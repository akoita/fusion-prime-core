// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "interfaces/ILiquiditySource.sol";
import "interfaces/ILiquidityBridgeAdapter.sol";

/**
 * @title LiquidityRouter
 * @notice Routes borrow requests to optimal liquidity sources based on user preferences
 * @dev Users can opt-in to cross-chain or external protocol liquidity with full cost transparency
 *
 * Key Principles:
 * 1. OPT-IN: Extended liquidity sources are disabled by default
 * 2. TRANSPARENT: All costs (fees, rates, timing) shown before execution
 * 3. USER CHOICE: User selects which sources to use and accepts terms
 */
contract LiquidityRouter is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    // ============ Constants ============
    address public constant NATIVE_ETH = address(0);
    uint256 public constant BPS_DENOMINATOR = 10000; // 100% = 10000 bps

    // ============ State ============

    /// @notice Local vault contract (always available, no fees)
    address public localVault;

    /// @notice Registered liquidity sources by type
    mapping(ILiquiditySource.SourceType => address) public liquiditySources;

    /// @notice Bridge adapters by chain ID
    mapping(uint256 => address) public bridgeAdapters;

    /// @notice Supported remote chain IDs for cross-chain liquidity
    uint256[] public supportedRemoteChains;

    /// @notice User preferences for extended liquidity
    mapping(address => UserPreferences) public userPreferences;

    // ============ Structs ============

    struct UserPreferences {
        bool enableCrossChain; // Allow cross-chain liquidity
        bool enableExternalProtocols; // Allow Aave/Compound/Morpho
        uint256 maxBridgeFeeBps; // Max acceptable bridge fee (e.g., 100 = 1%)
        uint256 maxWaitTimeSeconds; // Max acceptable wait time
        uint256 maxExternalAPYBps; // Max external protocol rate
        uint256 lastUpdated; // When preferences were set
    }

    struct BorrowRequest {
        address token; // Token to borrow
        uint256 amount; // Total amount needed
        ILiquiditySource.SourceType[] enabledSources; // User-enabled sources
        uint256 maxTotalFeeBps; // Max total fees willing to pay
    }

    struct BorrowPlan {
        BorrowStep[] steps; // Ordered steps to fulfill borrow
        uint256 totalFee; // Total fees across all steps
        uint256 maxWaitTime; // Longest wait time (0 if all instant)
        bool isValid; // Whether plan can be executed
    }

    struct BorrowStep {
        ILiquiditySource.SourceType sourceType;
        address sourceAddress;
        uint256 chainId; // For cross-chain sources
        uint256 amount;
        uint256 feeBps;
        uint256 feeAbsolute; // Fee in token/ETH terms
        uint256 estimatedTime; // 0 = instant
        uint256 rateAPY; // For external protocols
    }

    // ============ Events ============

    event LiquiditySourceRegistered(
        ILiquiditySource.SourceType sourceType,
        address source
    );
    event BridgeAdapterRegistered(uint256 chainId, address adapter);
    event UserPreferencesUpdated(
        address indexed user,
        bool crossChain,
        bool external_
    );
    event BorrowExecuted(
        address indexed user,
        address token,
        uint256 totalAmount,
        uint256 totalFee,
        uint256 sourcesUsed
    );
    event CrossChainBorrowInitiated(
        address indexed user,
        bytes32 requestId,
        uint256 sourceChainId,
        uint256 amount
    );

    // ============ Constructor ============

    constructor(address _localVault) Ownable(msg.sender) {
        require(_localVault != address(0), "Invalid vault address");
        localVault = _localVault;
    }

    // ============ User Preference Management ============

    /**
     * @notice Update user preferences for extended liquidity
     * @param enableCrossChain Allow cross-chain liquidity bridging
     * @param enableExternalProtocols Allow external protocol borrowing
     * @param maxBridgeFeeBps Maximum acceptable bridge fee in basis points
     * @param maxWaitTimeSeconds Maximum acceptable wait time for bridged funds
     * @param maxExternalAPYBps Maximum acceptable external protocol APY
     */
    function updatePreferences(
        bool enableCrossChain,
        bool enableExternalProtocols,
        uint256 maxBridgeFeeBps,
        uint256 maxWaitTimeSeconds,
        uint256 maxExternalAPYBps
    ) external {
        userPreferences[msg.sender] = UserPreferences({
            enableCrossChain: enableCrossChain,
            enableExternalProtocols: enableExternalProtocols,
            maxBridgeFeeBps: maxBridgeFeeBps,
            maxWaitTimeSeconds: maxWaitTimeSeconds,
            maxExternalAPYBps: maxExternalAPYBps,
            lastUpdated: block.timestamp
        });

        emit UserPreferencesUpdated(
            msg.sender,
            enableCrossChain,
            enableExternalProtocols
        );
    }

    /**
     * @notice Get user preferences (returns defaults if not set)
     * @param user User address
     * @return prefs User preferences
     */
    function getPreferences(
        address user
    ) external view returns (UserPreferences memory prefs) {
        prefs = userPreferences[user];
        if (prefs.lastUpdated == 0) {
            // Default: everything disabled, conservative limits
            prefs.enableCrossChain = false;
            prefs.enableExternalProtocols = false;
            prefs.maxBridgeFeeBps = 50; // 0.5% default max
            prefs.maxWaitTimeSeconds = 900; // 15 min default max
            prefs.maxExternalAPYBps = 500; // 5% default max
        }
    }

    // ============ Quote Generation ============

    /**
     * @notice Get quotes from all available liquidity sources
     * @param token Token to borrow
     * @param amount Amount to borrow
     * @return quotes Array of quotes from each source
     */
    function getQuotes(
        address token,
        uint256 amount
    ) external view returns (ILiquiditySource.LiquidityQuote[] memory quotes) {
        // Count all registered sources regardless of user preferences
        // This allows the UI to show "Enable" buttons for opt-in sources
        uint256 sourceCount = 1; // Local vault always available
        sourceCount += supportedRemoteChains.length;
        sourceCount += 3; // Aave, Compound, Morpho (placeholders if not registered)

        quotes = new ILiquiditySource.LiquidityQuote[](sourceCount);
        uint256 idx = 0;

        // 1. Local vault quote (always first)
        quotes[idx++] = _getLocalVaultQuote(token, amount);

        // 2. Cross-chain quotes
        for (uint256 i = 0; i < supportedRemoteChains.length; i++) {
            quotes[idx++] = _getCrossChainQuote(
                supportedRemoteChains[i],
                token,
                amount
            );
        }

        // 3. External protocol quotes
        quotes[idx++] = _getExternalQuote(
            ILiquiditySource.SourceType.EXTERNAL_AAVE,
            token,
            amount
        );
        quotes[idx++] = _getExternalQuote(
            ILiquiditySource.SourceType.EXTERNAL_COMPOUND,
            token,
            amount
        );
        quotes[idx++] = _getExternalQuote(
            ILiquiditySource.SourceType.EXTERNAL_MORPHO,
            token,
            amount
        );
    }

    /**
     * @notice Generate a borrow plan from selected sources
     * @param request User's borrow request with enabled sources
     * @return plan Detailed plan showing each step, fees, and timing
     */
    function generateBorrowPlan(
        BorrowRequest calldata request
    ) external view returns (BorrowPlan memory plan) {
        uint256 remaining = request.amount;
        uint256 stepCount = 0;
        BorrowStep[] memory tempSteps = new BorrowStep[](
            request.enabledSources.length
        );

        // Try each enabled source in order
        for (
            uint256 i = 0;
            i < request.enabledSources.length && remaining > 0;
            i++
        ) {
            ILiquiditySource.SourceType sourceType = request.enabledSources[i];
            ILiquiditySource.LiquidityQuote memory quote;

            if (sourceType == ILiquiditySource.SourceType.LOCAL_VAULT) {
                quote = _getLocalVaultQuote(request.token, remaining);
            } else if (
                sourceType == ILiquiditySource.SourceType.CROSS_CHAIN_BRIDGE
            ) {
                // Use first available cross-chain source with liquidity
                quote = _getBestCrossChainQuote(request.token, remaining);
            } else {
                quote = _getExternalQuote(sourceType, request.token, remaining);
            }

            if (quote.availableAmount > 0) {
                uint256 borrowAmount = quote.availableAmount < remaining
                    ? quote.availableAmount
                    : remaining;

                uint256 feeAbsolute = (borrowAmount * quote.feeBps) /
                    BPS_DENOMINATOR;

                tempSteps[stepCount++] = BorrowStep({
                    sourceType: sourceType,
                    sourceAddress: quote.sourceAddress,
                    chainId: quote.chainId,
                    amount: borrowAmount,
                    feeBps: quote.feeBps,
                    feeAbsolute: feeAbsolute,
                    estimatedTime: quote.estimatedTime,
                    rateAPY: quote.rateAPY
                });

                remaining -= borrowAmount;
                plan.totalFee += feeAbsolute;
                if (quote.estimatedTime > plan.maxWaitTime) {
                    plan.maxWaitTime = quote.estimatedTime;
                }
            }
        }

        // Copy to correctly sized array
        plan.steps = new BorrowStep[](stepCount);
        for (uint256 i = 0; i < stepCount; i++) {
            plan.steps[i] = tempSteps[i];
        }

        // Check if plan is valid
        plan.isValid =
            remaining == 0 &&
            ((plan.totalFee * BPS_DENOMINATOR) / request.amount) <=
            request.maxTotalFeeBps;
    }

    // ============ Borrow Execution ============

    /**
     * @notice Execute a borrow using user-approved plan
     * @param request Original borrow request
     * @param plan Pre-generated plan (user has reviewed and approved)
     */
    function executeBorrow(
        BorrowRequest calldata request,
        BorrowPlan calldata plan
    ) external payable nonReentrant {
        require(plan.isValid, "Invalid borrow plan");
        require(plan.steps.length > 0, "Empty borrow plan");

        uint256 totalBorrowed = 0;
        uint256 asyncCount = 0;

        for (uint256 i = 0; i < plan.steps.length; i++) {
            BorrowStep memory step = plan.steps[i];

            if (step.sourceType == ILiquiditySource.SourceType.LOCAL_VAULT) {
                // Instant local borrow
                _executeLocalBorrow(request.token, step.amount, msg.sender);
                totalBorrowed += step.amount;
            } else if (
                step.sourceType ==
                ILiquiditySource.SourceType.CROSS_CHAIN_BRIDGE
            ) {
                // Async cross-chain borrow
                bytes32 requestId = _initiateCrossChainBorrow(
                    step.chainId,
                    request.token,
                    step.amount,
                    msg.sender
                );
                emit CrossChainBorrowInitiated(
                    msg.sender,
                    requestId,
                    step.chainId,
                    step.amount
                );
                asyncCount++;
            } else {
                // External protocol borrow
                _executeExternalBorrow(
                    step.sourceType,
                    request.token,
                    step.amount,
                    msg.sender
                );
                totalBorrowed += step.amount;
            }
        }

        emit BorrowExecuted(
            msg.sender,
            request.token,
            request.amount,
            plan.totalFee,
            plan.steps.length
        );
    }

    // ============ Admin Functions ============

    /**
     * @notice Register a liquidity source adapter
     * @param sourceType Type of source
     * @param source Adapter contract address
     */
    function registerLiquiditySource(
        ILiquiditySource.SourceType sourceType,
        address source
    ) external onlyOwner {
        require(source != address(0), "Invalid source address");
        liquiditySources[sourceType] = source;
        emit LiquiditySourceRegistered(sourceType, source);
    }

    /**
     * @notice Register a bridge adapter for a chain
     * @param chainId Remote chain ID
     * @param adapter Bridge adapter address
     */
    function registerBridgeAdapter(
        uint256 chainId,
        address adapter
    ) external onlyOwner {
        require(adapter != address(0), "Invalid adapter address");
        bridgeAdapters[chainId] = adapter;

        // Add to supported chains if not already present
        bool exists = false;
        for (uint256 i = 0; i < supportedRemoteChains.length; i++) {
            if (supportedRemoteChains[i] == chainId) {
                exists = true;
                break;
            }
        }
        if (!exists) {
            supportedRemoteChains.push(chainId);
        }

        emit BridgeAdapterRegistered(chainId, adapter);
    }

    /**
     * @notice Update local vault address
     * @param _localVault New vault address
     */
    function setLocalVault(address _localVault) external onlyOwner {
        require(_localVault != address(0), "Invalid vault address");
        localVault = _localVault;
    }

    // ============ Internal Functions ============

    function _getLocalVaultQuote(
        address token,
        uint256 amount
    ) internal view returns (ILiquiditySource.LiquidityQuote memory quote) {
        address adapter = liquiditySources[
            ILiquiditySource.SourceType.LOCAL_VAULT
        ];
        if (adapter != address(0)) {
            return ILiquiditySource(adapter).getQuote(token, amount);
        }

        // Fallback to direct vault balance check if no adapter registered
        uint256 available;
        if (token == NATIVE_ETH) {
            available = localVault.balance;
        } else {
            available = IERC20(token).balanceOf(localVault);
        }

        quote = ILiquiditySource.LiquidityQuote({
            sourceType: ILiquiditySource.SourceType.LOCAL_VAULT,
            sourceAddress: localVault,
            chainId: block.chainid,
            token: token,
            availableAmount: available < amount ? available : amount,
            feeBps: 0,
            estimatedTime: 0,
            rateAPY: 0,
            metadata: ""
        });
    }

    function _getCrossChainQuote(
        uint256 remoteChainId,
        address token,
        uint256 amount
    ) internal view returns (ILiquiditySource.LiquidityQuote memory quote) {
        quote.sourceType = ILiquiditySource.SourceType.CROSS_CHAIN_BRIDGE;
        quote.chainId = remoteChainId;
        quote.token = token;

        address adapter = bridgeAdapters[remoteChainId];
        if (adapter == address(0)) {
            return quote; // Partial quote for unavailable chain
        }

        ILiquidityBridgeAdapter bridge = ILiquidityBridgeAdapter(adapter);

        // Get remote liquidity
        uint256 available = bridge.getRemoteLiquidity(remoteChainId, token);

        // Get fee estimate
        (uint256 fee, uint256 feeBps) = bridge.estimateLiquidityBridgeFee(
            remoteChainId,
            block.chainid,
            token,
            amount < available ? amount : available
        );

        // Get time estimate
        uint256 estimatedTime = bridge.estimateBridgeTime(
            remoteChainId,
            block.chainid
        );

        quote = ILiquiditySource.LiquidityQuote({
            sourceType: ILiquiditySource.SourceType.CROSS_CHAIN_BRIDGE,
            sourceAddress: adapter,
            chainId: remoteChainId,
            token: token,
            availableAmount: available < amount ? available : amount,
            feeBps: feeBps,
            estimatedTime: estimatedTime,
            rateAPY: 0,
            metadata: abi.encode(fee) // Include absolute fee
        });
    }

    function _getBestCrossChainQuote(
        address token,
        uint256 amount
    ) internal view returns (ILiquiditySource.LiquidityQuote memory bestQuote) {
        uint256 bestFee = type(uint256).max;

        for (uint256 i = 0; i < supportedRemoteChains.length; i++) {
            ILiquiditySource.LiquidityQuote memory quote = _getCrossChainQuote(
                supportedRemoteChains[i],
                token,
                amount
            );

            if (quote.availableAmount > 0 && quote.feeBps < bestFee) {
                bestQuote = quote;
                bestFee = quote.feeBps;
            }
        }
    }

    function _getExternalQuote(
        ILiquiditySource.SourceType sourceType,
        address token,
        uint256 amount
    ) internal view returns (ILiquiditySource.LiquidityQuote memory quote) {
        quote.sourceType = sourceType;
        quote.token = token;

        address source = liquiditySources[sourceType];
        if (source == address(0)) {
            return quote; // Partial quote for unavailable source
        }

        ILiquiditySource adapter = ILiquiditySource(source);
        quote = adapter.getQuote(token, amount);
    }

    function _executeLocalBorrow(
        address token,
        uint256 amount,
        address recipient
    ) internal {
        address source = liquiditySources[
            ILiquiditySource.SourceType.LOCAL_VAULT
        ];
        require(source != address(0), "Local vault source not registered");

        ILiquiditySource adapter = ILiquiditySource(source);
        (bool success, ) = adapter.borrow(token, amount, recipient, "");
        require(success, "Local borrow failed");
    }

    function _initiateCrossChainBorrow(
        uint256 sourceChainId,
        address token,
        uint256 amount,
        address recipient
    ) internal returns (bytes32 requestId) {
        address adapter = bridgeAdapters[sourceChainId];
        require(adapter != address(0), "No bridge for chain");

        ILiquidityBridgeAdapter bridge = ILiquidityBridgeAdapter(adapter);

        // Get required fee
        (uint256 fee, ) = bridge.estimateLiquidityBridgeFee(
            sourceChainId,
            block.chainid,
            token,
            amount
        );

        // Initiate transfer
        requestId = bridge.initiateLiquidityTransfer{value: fee}(
            sourceChainId,
            token,
            amount,
            recipient
        );
    }

    function _executeExternalBorrow(
        ILiquiditySource.SourceType sourceType,
        address token,
        uint256 amount,
        address recipient
    ) internal {
        address source = liquiditySources[sourceType];
        require(source != address(0), "Source not registered");

        ILiquiditySource adapter = ILiquiditySource(source);
        (bool success, ) = adapter.borrow(token, amount, recipient, "");
        require(success, "External borrow failed");
    }

    // ============ View Functions ============

    /**
     * @notice Get all supported remote chains
     * @return chains Array of chain IDs
     */
    function getSupportedRemoteChains()
        external
        view
        returns (uint256[] memory)
    {
        return supportedRemoteChains;
    }

    /**
     * @notice Check if a source type is available
     * @param sourceType Source type to check
     * @return available Whether the source is registered and available
     */
    function isSourceAvailable(
        ILiquiditySource.SourceType sourceType
    ) external view returns (bool) {
        if (sourceType == ILiquiditySource.SourceType.LOCAL_VAULT) {
            return localVault != address(0);
        }
        return liquiditySources[sourceType] != address(0);
    }

    // ============ Receive ============

    receive() external payable {}
}
