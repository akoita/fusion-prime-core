// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import "../interfaces/ILiquiditySource.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/**
 * @title IComet
 * @notice Minimal interface for Compound V3 (Comet)
 */
interface IComet {
    function supply(address asset, uint256 amount) external;

    function supplyTo(address dst, address asset, uint256 amount) external;

    function withdraw(address asset, uint256 amount) external;

    function withdrawTo(address to, address asset, uint256 amount) external;

    function borrowBalanceOf(address account) external view returns (uint256);

    function balanceOf(address account) external view returns (uint256);

    function totalSupply() external view returns (uint256);

    function totalBorrow() external view returns (uint256);

    function baseToken() external view returns (address);

    function baseTokenPriceFeed() external view returns (address);

    function getSupplyRate(uint256 utilization) external view returns (uint64);

    function getBorrowRate(uint256 utilization) external view returns (uint64);

    function getUtilization() external view returns (uint256);

    function baseBorrowMin() external view returns (uint256);

    function isAllowed(
        address owner,
        address manager
    ) external view returns (bool);

    function allow(address manager, bool isAllowed_) external;

    function collateralBalanceOf(
        address account,
        address asset
    ) external view returns (uint128);

    function getAssetInfo(
        uint8 i
    )
        external
        view
        returns (
            uint8 offset,
            address asset,
            address priceFeed,
            uint64 scale,
            uint64 borrowCollateralFactor,
            uint64 liquidateCollateralFactor,
            uint64 liquidationFactor,
            uint128 supplyCap
        );

    function numAssets() external view returns (uint8);
}

/**
 * @title CompoundV3Adapter
 * @notice Liquidity source adapter for Compound V3 (Comet) protocol
 * @dev Allows borrowing from Compound using cross-chain collateral as backing
 *
 * Key Features:
 * - Direct base token borrowing
 * - Real-time utilization-based rates
 * - Simple borrow/repay interface
 */
contract CompoundV3Adapter is ILiquiditySource, Ownable {
    using SafeERC20 for IERC20;

    // ============ Constants ============

    address public constant NATIVE_ETH = address(0);
    uint256 public constant SECONDS_PER_YEAR = 365 days;
    uint256 public constant BPS_DENOMINATOR = 10000;
    uint256 public constant FACTOR_SCALE = 1e18;

    // ============ State ============

    /// @notice Comet instances by base token
    mapping(address => address) public comets;

    /// @notice WETH address for ETH operations
    address public immutable weth;

    /// @notice Supported base tokens
    address[] public supportedBaseTokens;

    /// @notice Borrowed amounts per user per token
    mapping(address => mapping(address => uint256)) public userBorrows;

    /// @notice Total borrowed per token
    mapping(address => uint256) public totalBorrowedByToken;

    // ============ Events ============

    event CometAdded(address indexed baseToken, address indexed comet);
    event BorrowedFromCompound(
        address indexed user,
        address indexed token,
        uint256 amount,
        uint256 rateAPY
    );
    event RepaidToCompound(
        address indexed user,
        address indexed token,
        uint256 amount
    );

    // ============ Constructor ============

    constructor(address _weth) Ownable(msg.sender) {
        require(_weth != address(0), "Invalid WETH");
        weth = _weth;
    }

    // ============ Admin Functions ============

    /**
     * @notice Register a Comet market
     * @param comet Comet contract address
     */
    function addComet(address comet) external onlyOwner {
        require(comet != address(0), "Invalid comet");

        address baseToken = IComet(comet).baseToken();
        comets[baseToken] = comet;
        supportedBaseTokens.push(baseToken);

        emit CometAdded(baseToken, comet);
    }

    /**
     * @notice Remove a Comet market
     * @param baseToken Base token of the market to remove
     */
    function removeComet(address baseToken) external onlyOwner {
        delete comets[baseToken];

        // Remove from array
        for (uint256 i = 0; i < supportedBaseTokens.length; i++) {
            if (supportedBaseTokens[i] == baseToken) {
                supportedBaseTokens[i] = supportedBaseTokens[
                    supportedBaseTokens.length - 1
                ];
                supportedBaseTokens.pop();
                break;
            }
        }
    }

    // ============ ILiquiditySource Implementation ============

    /**
     * @notice Get available liquidity in Compound for a token
     * @param token Token to check
     * @return available Available amount to borrow
     */
    function getAvailableLiquidity(
        address token
    ) external view override returns (uint256 available) {
        address actualToken = token == NATIVE_ETH ? weth : token;
        address comet = comets[actualToken];

        if (comet == address(0)) {
            return 0;
        }

        IComet cometContract = IComet(comet);

        // Available = total supply - total borrow
        uint256 totalSupply = cometContract.totalSupply();
        uint256 totalBorrow = cometContract.totalBorrow();

        if (totalSupply > totalBorrow) {
            available = totalSupply - totalBorrow;
            // Leave 5% buffer
            available = (available * 95) / 100;
        }
    }

    /**
     * @notice Get a quote for borrowing from Compound
     * @param token Token to borrow
     * @param amount Amount to borrow
     * @return quote Full quote with APY
     */
    function getQuote(
        address token,
        uint256 amount
    ) external view override returns (LiquidityQuote memory quote) {
        address actualToken = token == NATIVE_ETH ? weth : token;

        uint256 available = this.getAvailableLiquidity(token);
        uint256 rateAPY = _getBorrowRate(actualToken);

        quote = LiquidityQuote({
            sourceType: SourceType.EXTERNAL_COMPOUND,
            sourceAddress: address(this),
            chainId: block.chainid,
            token: token,
            availableAmount: available < amount ? available : amount,
            feeBps: 0, // No upfront fee
            estimatedTime: 0, // Instant
            rateAPY: rateAPY,
            metadata: ""
        });
    }

    /**
     * @notice Execute a borrow from Compound
     * @param token Token to borrow
     * @param amount Amount to borrow
     * @param recipient Address to receive funds
     * @param data Additional data (unused)
     * @return success Whether borrow succeeded
     * @return requestId Empty (instant operation)
     */
    function borrow(
        address token,
        uint256 amount,
        address recipient,
        bytes calldata data
    ) external override returns (bool success, bytes32 requestId) {
        address actualToken = token == NATIVE_ETH ? weth : token;
        address comet = comets[actualToken];

        require(comet != address(0), "Token not supported");
        require(amount > 0, "Amount must be > 0");

        // Check available liquidity
        uint256 available = this.getAvailableLiquidity(token);
        require(amount <= available, "Insufficient Compound liquidity");

        // Get current rate for event
        uint256 rateAPY = _getBorrowRate(actualToken);

        // In Compound V3, borrowing is done by withdrawing more than your collateral
        // This requires collateral to be deposited first
        // For now, we withdraw from our position
        IComet(comet).withdrawTo(recipient, actualToken, amount);

        // Track borrowed amount
        userBorrows[recipient][token] += amount;
        totalBorrowedByToken[token] += amount;

        emit BorrowedFromCompound(recipient, token, amount, rateAPY);

        success = true;
        requestId = bytes32(0);
    }

    /**
     * @notice Repay borrowed amount to Compound
     * @param token Token to repay
     * @param amount Amount to repay
     * @param onBehalfOf User to repay for
     */
    function repay(address token, uint256 amount, address onBehalfOf) external {
        address actualToken = token == NATIVE_ETH ? weth : token;
        address comet = comets[actualToken];

        require(comet != address(0), "Token not supported");

        // Transfer tokens from caller
        IERC20(actualToken).safeTransferFrom(msg.sender, address(this), amount);

        // Approve Comet
        IERC20(actualToken).approve(comet, amount);

        // Supply to repay (in V3, supplying reduces borrow balance)
        IComet(comet).supply(actualToken, amount);

        // Update tracking
        if (userBorrows[onBehalfOf][token] >= amount) {
            userBorrows[onBehalfOf][token] -= amount;
        } else {
            userBorrows[onBehalfOf][token] = 0;
        }

        if (totalBorrowedByToken[token] >= amount) {
            totalBorrowedByToken[token] -= amount;
        } else {
            totalBorrowedByToken[token] = 0;
        }

        emit RepaidToCompound(onBehalfOf, token, amount);
    }

    /**
     * @notice Check if token is supported
     * @param token Token to check
     * @return supported Whether token is supported
     */
    function supportsToken(
        address token
    ) external view override returns (bool) {
        address actualToken = token == NATIVE_ETH ? weth : token;
        return comets[actualToken] != address(0);
    }

    /**
     * @notice Get source type (EXTERNAL_COMPOUND)
     */
    function getSourceType() external pure override returns (SourceType) {
        return SourceType.EXTERNAL_COMPOUND;
    }

    /**
     * @notice Check if async (no, Compound is instant)
     */
    function isAsync() external pure override returns (bool) {
        return false;
    }

    // ============ View Functions ============

    /**
     * @notice Get current borrow rate from Compound
     * @param token Token to check
     * @return rateBps Rate in basis points (100 = 1% APY)
     */
    function _getBorrowRate(
        address token
    ) internal view returns (uint256 rateBps) {
        address comet = comets[token];
        if (comet == address(0)) {
            return 0;
        }

        IComet cometContract = IComet(comet);

        // Get current utilization
        uint256 utilization = cometContract.getUtilization();

        // Get borrow rate per second
        uint64 ratePerSecond = cometContract.getBorrowRate(utilization);

        // Convert to APY in BPS
        // Rate per second * seconds per year / FACTOR_SCALE * BPS_DENOMINATOR
        uint256 rateAPY = uint256(ratePerSecond) * SECONDS_PER_YEAR;
        rateBps = (rateAPY * BPS_DENOMINATOR) / FACTOR_SCALE;
    }

    /**
     * @notice Get user's borrowed amount
     * @param user User address
     * @param token Token
     * @return borrowed Amount currently borrowed
     */
    function getUserBorrowed(
        address user,
        address token
    ) external view returns (uint256) {
        return userBorrows[user][token];
    }

    /**
     * @notice Get current APY for a token (in basis points)
     * @param token Token to check
     * @return apyBps APY in basis points (100 = 1%)
     */
    function getCurrentAPY(
        address token
    ) external view returns (uint256 apyBps) {
        address actualToken = token == NATIVE_ETH ? weth : token;
        return _getBorrowRate(actualToken);
    }

    /**
     * @notice Get all supported base tokens
     * @return tokens Array of supported tokens
     */
    function getSupportedTokens() external view returns (address[] memory) {
        return supportedBaseTokens;
    }

    // ============ Receive ETH ============

    receive() external payable {}
}
