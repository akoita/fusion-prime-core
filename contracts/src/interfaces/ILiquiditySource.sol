// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

/**
 * @title ILiquiditySource
 * @notice Interface for liquidity source adapters (local vault, bridges, external protocols)
 * @dev Each adapter implements this interface to provide unified access to different liquidity sources
 */
interface ILiquiditySource {
    /// @notice Types of liquidity sources
    enum SourceType {
        LOCAL_VAULT, // Local chain vault (instant, no fees)
        CROSS_CHAIN_BRIDGE, // Bridge from another chain (async, bridge fees)
        EXTERNAL_AAVE, // Aave V3 protocol
        EXTERNAL_COMPOUND, // Compound V3 protocol
        EXTERNAL_MORPHO // Morpho optimized lending
    }

    /// @notice Quote for borrowing from this source
    struct LiquidityQuote {
        SourceType sourceType; // Type of this source
        address sourceAddress; // Contract address of source
        uint256 chainId; // Chain ID (for cross-chain sources)
        address token; // Token to borrow
        uint256 availableAmount; // Max borrowable from this source
        uint256 feeBps; // Fee in basis points (100 = 1%)
        uint256 estimatedTime; // Seconds until funds available (0 = instant)
        uint256 rateAPY; // Annual interest rate (for external protocols, in bps)
        bytes metadata; // Additional source-specific data
    }

    /**
     * @notice Get available liquidity for a token
     * @param token Token address (address(0) for native ETH)
     * @return available Amount available to borrow
     */
    function getAvailableLiquidity(
        address token
    ) external view returns (uint256 available);

    /**
     * @notice Get a quote for borrowing
     * @param token Token to borrow
     * @param amount Amount to borrow
     * @return quote Full quote details
     */
    function getQuote(
        address token,
        uint256 amount
    ) external view returns (LiquidityQuote memory quote);

    /**
     * @notice Execute a borrow from this source
     * @param token Token to borrow
     * @param amount Amount to borrow
     * @param recipient Address to receive funds
     * @param data Additional data for the source
     * @return success Whether the borrow was initiated successfully
     * @return requestId For async sources, ID to track the request
     */
    function borrow(
        address token,
        uint256 amount,
        address recipient,
        bytes calldata data
    ) external returns (bool success, bytes32 requestId);

    /**
     * @notice Check if this source supports a token
     * @param token Token address
     * @return supported Whether the token is supported
     */
    function supportsToken(
        address token
    ) external view returns (bool supported);

    /**
     * @notice Get the source type
     * @return sourceType The type of this liquidity source
     */
    function getSourceType() external view returns (SourceType sourceType);

    /**
     * @notice Check if borrows from this source are instant or async
     * @return isAsync True if borrows require waiting (e.g., bridge transfers)
     */
    function isAsync() external view returns (bool isAsync);
}
