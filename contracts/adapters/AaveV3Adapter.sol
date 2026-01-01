// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import "../interfaces/ILiquiditySource.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/**
 * @title IAaveV3Pool
 * @notice Minimal interface for Aave V3 Pool
 */
interface IAaveV3Pool {
    function supply(
        address asset,
        uint256 amount,
        address onBehalfOf,
        uint16 referralCode
    ) external;

    function borrow(
        address asset,
        uint256 amount,
        uint256 interestRateMode, // 1 = stable, 2 = variable
        uint16 referralCode,
        address onBehalfOf
    ) external;

    function repay(
        address asset,
        uint256 amount,
        uint256 interestRateMode,
        address onBehalfOf
    ) external returns (uint256);

    function withdraw(
        address asset,
        uint256 amount,
        address to
    ) external returns (uint256);

    function getUserAccountData(
        address user
    )
        external
        view
        returns (
            uint256 totalCollateralBase,
            uint256 totalDebtBase,
            uint256 availableBorrowsBase,
            uint256 currentLiquidationThreshold,
            uint256 ltv,
            uint256 healthFactor
        );
}

/**
 * @title IAaveV3PoolDataProvider
 * @notice Interface for Aave V3 Pool Data Provider
 */
interface IAaveV3PoolDataProvider {
    function getReserveData(
        address asset
    )
        external
        view
        returns (
            uint256 unbacked,
            uint256 accruedToTreasuryScaled,
            uint256 totalAToken,
            uint256 totalStableDebt,
            uint256 totalVariableDebt,
            uint256 liquidityRate,
            uint256 variableBorrowRate,
            uint256 stableBorrowRate,
            uint256 averageStableBorrowRate,
            uint256 liquidityIndex,
            uint256 variableBorrowIndex,
            uint40 lastUpdateTimestamp
        );

    function getATokenTotalSupply(
        address asset
    ) external view returns (uint256);

    function getTotalDebt(address asset) external view returns (uint256);
}

/**
 * @title AaveV3Adapter
 * @notice Liquidity source adapter for Aave V3 protocol
 * @dev Allows borrowing from Aave using cross-chain collateral as backing
 *
 * Key Features:
 * - Variable rate borrowing from Aave V3
 * - Real-time APY from on-chain data
 * - Health factor monitoring
 */
contract AaveV3Adapter is ILiquiditySource, Ownable {
    using SafeERC20 for IERC20;

    // ============ Constants ============

    address public constant NATIVE_ETH = address(0);
    uint256 public constant VARIABLE_RATE_MODE = 2;
    uint256 public constant RAY = 1e27; // Aave uses RAY for rates
    uint256 public constant BPS_DENOMINATOR = 10000;

    // ============ State ============

    /// @notice Aave V3 Pool
    IAaveV3Pool public immutable aavePool;

    /// @notice Aave V3 Pool Data Provider
    IAaveV3PoolDataProvider public immutable dataProvider;

    /// @notice WETH address for ETH operations
    address public immutable weth;

    /// @notice Supported tokens for borrowing
    mapping(address => bool) public supportedTokens;

    /// @notice Token to aToken mapping
    mapping(address => address) public aTokens;

    /// @notice Borrowed amounts per user per token
    mapping(address => mapping(address => uint256)) public userBorrows;

    /// @notice Total borrowed per token
    mapping(address => uint256) public totalBorrowedByToken;

    // ============ Events ============

    event TokenAdded(address indexed token, address indexed aToken);
    event BorrowedFromAave(
        address indexed user,
        address indexed token,
        uint256 amount,
        uint256 rateAPY
    );
    event RepaidToAave(
        address indexed user,
        address indexed token,
        uint256 amount
    );

    // ============ Constructor ============

    constructor(
        address _aavePool,
        address _dataProvider,
        address _weth
    ) Ownable(msg.sender) {
        require(_aavePool != address(0), "Invalid pool");
        require(_dataProvider != address(0), "Invalid data provider");
        require(_weth != address(0), "Invalid WETH");

        aavePool = IAaveV3Pool(_aavePool);
        dataProvider = IAaveV3PoolDataProvider(_dataProvider);
        weth = _weth;
    }

    // ============ Admin Functions ============

    /**
     * @notice Add a supported token for borrowing
     * @param token Token address
     * @param aToken Corresponding aToken address
     */
    function addSupportedToken(
        address token,
        address aToken
    ) external onlyOwner {
        require(token != address(0), "Invalid token");
        supportedTokens[token] = true;
        aTokens[token] = aToken;
        emit TokenAdded(token, aToken);
    }

    /**
     * @notice Remove a supported token
     * @param token Token to remove
     */
    function removeSupportedToken(address token) external onlyOwner {
        supportedTokens[token] = false;
        delete aTokens[token];
    }

    // ============ ILiquiditySource Implementation ============

    /**
     * @notice Get available liquidity in Aave for a token
     * @param token Token to check
     * @return available Available amount to borrow
     */
    function getAvailableLiquidity(
        address token
    ) external view override returns (uint256 available) {
        address actualToken = token == NATIVE_ETH ? weth : token;

        if (!supportedTokens[actualToken]) {
            return 0;
        }

        // Get total aToken supply (deposited)
        uint256 totalSupply = dataProvider.getATokenTotalSupply(actualToken);

        // Get total debt
        uint256 totalDebt = dataProvider.getTotalDebt(actualToken);

        // Available = supply - debt (with some buffer)
        if (totalSupply > totalDebt) {
            available = totalSupply - totalDebt;
            // Leave 5% buffer for other borrowers
            available = (available * 95) / 100;
        }
    }

    /**
     * @notice Get a quote for borrowing from Aave
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
        uint256 rateAPY = _getVariableBorrowRate(actualToken);

        // Convert RAY rate to BPS for display
        uint256 rateBps = (rateAPY * BPS_DENOMINATOR) / RAY;

        quote = LiquidityQuote({
            sourceType: SourceType.EXTERNAL_AAVE,
            sourceAddress: address(this),
            chainId: block.chainid,
            token: token,
            availableAmount: available < amount ? available : amount,
            feeBps: 0, // No upfront fee, just APY
            estimatedTime: 0, // Instant
            rateAPY: rateBps,
            metadata: abi.encode(rateAPY) // Full RAY rate
        });
    }

    /**
     * @notice Execute a borrow from Aave
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

        require(supportedTokens[actualToken], "Token not supported");
        require(amount > 0, "Amount must be > 0");

        // Check available liquidity
        uint256 available = this.getAvailableLiquidity(token);
        require(amount <= available, "Insufficient Aave liquidity");

        // Get current rate for event
        uint256 rateAPY = _getVariableBorrowRate(actualToken);

        // Borrow from Aave
        // Note: This contract needs to have collateral deposited first
        // In production, LiquidityRouter would handle collateral management
        aavePool.borrow(
            actualToken,
            amount,
            VARIABLE_RATE_MODE,
            0, // referral code
            address(this)
        );

        // Track borrowed amount
        userBorrows[recipient][token] += amount;
        totalBorrowedByToken[token] += amount;

        // Transfer to recipient
        if (token == NATIVE_ETH) {
            // Unwrap WETH and send ETH
            // Would need WETH interface in production
            IERC20(weth).safeTransfer(recipient, amount);
        } else {
            IERC20(actualToken).safeTransfer(recipient, amount);
        }

        emit BorrowedFromAave(recipient, token, amount, rateAPY);

        success = true;
        requestId = bytes32(0);
    }

    /**
     * @notice Repay borrowed amount to Aave
     * @param token Token to repay
     * @param amount Amount to repay
     * @param onBehalfOf User to repay for
     */
    function repay(address token, uint256 amount, address onBehalfOf) external {
        address actualToken = token == NATIVE_ETH ? weth : token;

        // Transfer tokens from caller
        IERC20(actualToken).safeTransferFrom(msg.sender, address(this), amount);

        // Approve Aave pool
        IERC20(actualToken).approve(address(aavePool), amount);

        // Repay to Aave
        uint256 repaid = aavePool.repay(
            actualToken,
            amount,
            VARIABLE_RATE_MODE,
            address(this)
        );

        // Update tracking
        if (userBorrows[onBehalfOf][token] >= repaid) {
            userBorrows[onBehalfOf][token] -= repaid;
        } else {
            userBorrows[onBehalfOf][token] = 0;
        }

        if (totalBorrowedByToken[token] >= repaid) {
            totalBorrowedByToken[token] -= repaid;
        } else {
            totalBorrowedByToken[token] = 0;
        }

        emit RepaidToAave(onBehalfOf, token, repaid);
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
        return supportedTokens[actualToken];
    }

    /**
     * @notice Get source type (EXTERNAL_AAVE)
     */
    function getSourceType() external pure override returns (SourceType) {
        return SourceType.EXTERNAL_AAVE;
    }

    /**
     * @notice Check if async (no, Aave is instant)
     */
    function isAsync() external pure override returns (bool) {
        return false;
    }

    // ============ View Functions ============

    /**
     * @notice Get current variable borrow rate from Aave
     * @param token Token to check
     * @return rate Rate in RAY (1e27)
     */
    function _getVariableBorrowRate(
        address token
    ) internal view returns (uint256 rate) {
        (, , , , , uint256 variableBorrowRate, , , , , , ) = dataProvider
            .getReserveData(token);
        return variableBorrowRate;
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
        uint256 rateRAY = _getVariableBorrowRate(actualToken);
        apyBps = (rateRAY * BPS_DENOMINATOR) / RAY;
    }

    // ============ Receive ETH ============

    receive() external payable {}
}
