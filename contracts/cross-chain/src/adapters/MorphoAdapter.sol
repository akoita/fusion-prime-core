// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import "../interfaces/ILiquiditySource.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/**
 * @title IMorpho
 * @notice Minimal interface for Morpho Blue
 */
interface IMorpho {
    struct MarketParams {
        address loanToken;
        address collateralToken;
        address oracle;
        address irm; // Interest Rate Model
        uint256 lltv; // Liquidation LTV
    }

    struct Market {
        uint128 totalSupplyAssets;
        uint128 totalSupplyShares;
        uint128 totalBorrowAssets;
        uint128 totalBorrowShares;
        uint128 lastUpdate;
        uint128 fee;
    }

    struct Position {
        uint256 supplyShares;
        uint128 borrowShares;
        uint128 collateral;
    }

    function supply(
        MarketParams memory marketParams,
        uint256 assets,
        uint256 shares,
        address onBehalf,
        bytes memory data
    ) external returns (uint256 assetsSupplied, uint256 sharesSupplied);

    function borrow(
        MarketParams memory marketParams,
        uint256 assets,
        uint256 shares,
        address onBehalf,
        address receiver
    ) external returns (uint256 assetsBorrowed, uint256 sharesBorrowed);

    function repay(
        MarketParams memory marketParams,
        uint256 assets,
        uint256 shares,
        address onBehalf,
        bytes memory data
    ) external returns (uint256 assetsRepaid, uint256 sharesRepaid);

    function withdraw(
        MarketParams memory marketParams,
        uint256 assets,
        uint256 shares,
        address onBehalf,
        address receiver
    ) external returns (uint256 assetsWithdrawn, uint256 sharesWithdrawn);

    function supplyCollateral(
        MarketParams memory marketParams,
        uint256 assets,
        address onBehalf,
        bytes memory data
    ) external;

    function withdrawCollateral(
        MarketParams memory marketParams,
        uint256 assets,
        address onBehalf,
        address receiver
    ) external;

    function market(bytes32 id) external view returns (Market memory);

    function position(
        bytes32 id,
        address user
    ) external view returns (Position memory);

    function idToMarketParams(
        bytes32 id
    ) external view returns (MarketParams memory);
}

/**
 * @title IMorphoIrm
 * @notice Interface for Morpho Interest Rate Model
 */
interface IMorphoIrm {
    function borrowRate(
        IMorpho.MarketParams memory marketParams,
        IMorpho.Market memory market
    ) external view returns (uint256);

    function borrowRateView(
        IMorpho.MarketParams memory marketParams,
        IMorpho.Market memory market
    ) external view returns (uint256);
}

/**
 * @title MorphoAdapter
 * @notice Liquidity source adapter for Morpho Blue protocol
 * @dev Allows borrowing from Morpho with optimized rates through P2P matching
 *
 * Key Features:
 * - Access to Morpho's optimized rates (often better than Aave/Compound)
 * - Multiple isolated markets
 * - Efficient capital utilization
 */
contract MorphoAdapter is ILiquiditySource, Ownable {
    using SafeERC20 for IERC20;

    // ============ Constants ============

    address public constant NATIVE_ETH = address(0);
    uint256 public constant SECONDS_PER_YEAR = 365 days;
    uint256 public constant BPS_DENOMINATOR = 10000;
    uint256 public constant WAD = 1e18;

    // ============ State ============

    /// @notice Morpho Blue contract
    IMorpho public immutable morpho;

    /// @notice WETH address for ETH operations
    address public immutable weth;

    /// @notice Registered market IDs by loan token
    mapping(address => bytes32) public preferredMarkets;

    /// @notice All registered market IDs
    bytes32[] public marketIds;

    /// @notice Market params cache
    mapping(bytes32 => IMorpho.MarketParams) public marketParamsCache;

    /// @notice Borrowed amounts per user per token
    mapping(address => mapping(address => uint256)) public userBorrows;

    /// @notice Total borrowed per token
    mapping(address => uint256) public totalBorrowedByToken;

    // ============ Events ============

    event MarketAdded(
        bytes32 indexed marketId,
        address indexed loanToken,
        address indexed collateralToken
    );
    event BorrowedFromMorpho(
        address indexed user,
        address indexed token,
        uint256 amount,
        uint256 rateAPY
    );
    event RepaidToMorpho(
        address indexed user,
        address indexed token,
        uint256 amount
    );

    // ============ Constructor ============

    constructor(address _morpho, address _weth) Ownable(msg.sender) {
        require(_morpho != address(0), "Invalid Morpho");
        require(_weth != address(0), "Invalid WETH");

        morpho = IMorpho(_morpho);
        weth = _weth;
    }

    // ============ Admin Functions ============

    /**
     * @notice Register a Morpho market
     * @param marketId Morpho market ID
     * @param setAsPreferred Set as preferred market for this loan token
     */
    function addMarket(
        bytes32 marketId,
        bool setAsPreferred
    ) external onlyOwner {
        IMorpho.MarketParams memory params = morpho.idToMarketParams(marketId);
        require(params.loanToken != address(0), "Invalid market");

        marketParamsCache[marketId] = params;
        marketIds.push(marketId);

        if (setAsPreferred) {
            preferredMarkets[params.loanToken] = marketId;
        }

        emit MarketAdded(marketId, params.loanToken, params.collateralToken);
    }

    /**
     * @notice Set preferred market for a loan token
     * @param loanToken Loan token address
     * @param marketId Market ID to prefer
     */
    function setPreferredMarket(
        address loanToken,
        bytes32 marketId
    ) external onlyOwner {
        preferredMarkets[loanToken] = marketId;
    }

    // ============ ILiquiditySource Implementation ============

    /**
     * @notice Get available liquidity in Morpho for a token
     * @param token Token to check
     * @return available Available amount to borrow
     */
    function getAvailableLiquidity(
        address token
    ) external view override returns (uint256 available) {
        address actualToken = token == NATIVE_ETH ? weth : token;
        bytes32 marketId = preferredMarkets[actualToken];

        if (marketId == bytes32(0)) {
            return 0;
        }

        IMorpho.Market memory market = morpho.market(marketId);

        // Available = total supply - total borrow
        if (market.totalSupplyAssets > market.totalBorrowAssets) {
            available = market.totalSupplyAssets - market.totalBorrowAssets;
            // Leave 5% buffer
            available = (available * 95) / 100;
        }
    }

    /**
     * @notice Get a quote for borrowing from Morpho
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
            sourceType: SourceType.EXTERNAL_MORPHO,
            sourceAddress: address(this),
            chainId: block.chainid,
            token: token,
            availableAmount: available < amount ? available : amount,
            feeBps: 0, // No upfront fee
            estimatedTime: 0, // Instant
            rateAPY: rateAPY,
            metadata: abi.encode(preferredMarkets[actualToken]) // Include market ID
        });
    }

    /**
     * @notice Execute a borrow from Morpho
     * @param token Token to borrow
     * @param amount Amount to borrow
     * @param recipient Address to receive funds
     * @param data Optional market ID to use
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

        // Get market ID from data or use preferred
        bytes32 marketId;
        if (data.length >= 32) {
            marketId = abi.decode(data, (bytes32));
        } else {
            marketId = preferredMarkets[actualToken];
        }

        require(marketId != bytes32(0), "No market for token");

        IMorpho.MarketParams memory params = marketParamsCache[marketId];
        require(params.loanToken == actualToken, "Market mismatch");

        // Check available liquidity
        uint256 available = this.getAvailableLiquidity(token);
        require(amount <= available, "Insufficient Morpho liquidity");

        // Get current rate for event
        uint256 rateAPY = _getBorrowRate(actualToken);

        // Borrow from Morpho
        // Note: This requires collateral to be deposited first
        (uint256 borrowed, ) = morpho.borrow(
            params,
            amount,
            0, // shares (0 = use assets)
            address(this),
            recipient
        );

        // Track borrowed amount
        userBorrows[recipient][token] += borrowed;
        totalBorrowedByToken[token] += borrowed;

        emit BorrowedFromMorpho(recipient, token, borrowed, rateAPY);

        success = true;
        requestId = bytes32(0);
    }

    /**
     * @notice Repay borrowed amount to Morpho
     * @param token Token to repay
     * @param amount Amount to repay
     * @param onBehalfOf User to repay for
     */
    function repay(address token, uint256 amount, address onBehalfOf) external {
        address actualToken = token == NATIVE_ETH ? weth : token;
        bytes32 marketId = preferredMarkets[actualToken];

        require(marketId != bytes32(0), "No market for token");

        IMorpho.MarketParams memory params = marketParamsCache[marketId];

        // Transfer tokens from caller
        IERC20(actualToken).safeTransferFrom(msg.sender, address(this), amount);

        // Approve Morpho
        IERC20(actualToken).approve(address(morpho), amount);

        // Repay to Morpho
        (uint256 repaid, ) = morpho.repay(
            params,
            amount,
            0, // shares (0 = use assets)
            address(this),
            ""
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

        emit RepaidToMorpho(onBehalfOf, token, repaid);
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
        return preferredMarkets[actualToken] != bytes32(0);
    }

    /**
     * @notice Get source type (EXTERNAL_MORPHO)
     */
    function getSourceType() external pure override returns (SourceType) {
        return SourceType.EXTERNAL_MORPHO;
    }

    /**
     * @notice Check if async (no, Morpho is instant)
     */
    function isAsync() external pure override returns (bool) {
        return false;
    }

    // ============ View Functions ============

    /**
     * @notice Get current borrow rate from Morpho
     * @param token Token to check
     * @return rateBps Rate in basis points (100 = 1% APY)
     */
    function _getBorrowRate(
        address token
    ) internal view returns (uint256 rateBps) {
        bytes32 marketId = preferredMarkets[token];
        if (marketId == bytes32(0)) {
            return 0;
        }

        IMorpho.MarketParams memory params = marketParamsCache[marketId];
        IMorpho.Market memory market = morpho.market(marketId);

        // Get rate from IRM
        if (params.irm != address(0)) {
            try IMorphoIrm(params.irm).borrowRateView(params, market) returns (
                uint256 ratePerSecond
            ) {
                // Convert to APY in BPS
                uint256 rateAPY = ratePerSecond * SECONDS_PER_YEAR;
                rateBps = (rateAPY * BPS_DENOMINATOR) / WAD;
            } catch {
                // Fallback estimate
                rateBps = 300; // 3% default
            }
        }
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
     * @notice Get all registered market IDs
     * @return ids Array of market IDs
     */
    function getAllMarkets() external view returns (bytes32[] memory) {
        return marketIds;
    }

    /**
     * @notice Get market params for a market ID
     * @param marketId Market ID
     * @return params Market parameters
     */
    function getMarketParams(
        bytes32 marketId
    ) external view returns (IMorpho.MarketParams memory) {
        return marketParamsCache[marketId];
    }

    // ============ Receive ETH ============

    receive() external payable {}
}
