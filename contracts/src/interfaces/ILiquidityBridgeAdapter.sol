// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import "./IBridgeAdapter.sol";

/**
 * @title ILiquidityBridgeAdapter
 * @notice Extended interface for bridge adapters used in liquidity routing
 * @dev Extends IBridgeAdapter with liquidity-specific functionality (fee estimation, transfer tracking)
 */
interface ILiquidityBridgeAdapter is IBridgeAdapter {
    /// @notice Status of a liquidity bridge transfer
    enum LiquidityTransferStatus {
        PENDING, // Transfer initiated, waiting for bridge
        COMPLETED, // Funds received on destination
        FAILED, // Transfer failed
        EXPIRED // Transfer timed out
    }

    /// @notice Details of a liquidity bridge request
    struct LiquidityTransferRequest {
        bytes32 requestId; // Unique identifier
        address user; // User who initiated
        uint256 sourceChainId; // Origin chain
        uint256 destChainId; // Destination chain
        address token; // Token being bridged
        uint256 amount; // Amount requested
        uint256 fee; // Bridge fee paid
        uint256 timestamp; // When request was created
        LiquidityTransferStatus status; // Current status
    }

    /**
     * @notice Get estimated bridge fee for liquidity transfer
     * @param sourceChainId Origin chain ID
     * @param destChainId Destination chain ID
     * @param token Token to bridge (address(0) for native ETH)
     * @param amount Amount to bridge
     * @return fee Estimated fee in native token
     * @return feeBps Fee as basis points of amount
     */
    function estimateLiquidityBridgeFee(
        uint256 sourceChainId,
        uint256 destChainId,
        address token,
        uint256 amount
    ) external view returns (uint256 fee, uint256 feeBps);

    /**
     * @notice Get estimated bridge time
     * @param sourceChainId Origin chain ID
     * @param destChainId Destination chain ID
     * @return estimatedSeconds Expected time for transfer to complete
     */
    function estimateBridgeTime(
        uint256 sourceChainId,
        uint256 destChainId
    ) external view returns (uint256 estimatedSeconds);

    /**
     * @notice Initiate a liquidity bridge transfer from another chain
     * @param sourceChainId Chain to pull liquidity from
     * @param token Token to bridge
     * @param amount Amount to bridge
     * @param recipient Address to receive funds on this chain
     * @return requestId Unique identifier to track this request
     */
    function initiateLiquidityTransfer(
        uint256 sourceChainId,
        address token,
        uint256 amount,
        address recipient
    ) external payable returns (bytes32 requestId);

    /**
     * @notice Check status of a liquidity transfer request
     * @param requestId The request to check
     * @return request Full request details including status
     */
    function getLiquidityTransferRequest(
        bytes32 requestId
    ) external view returns (LiquidityTransferRequest memory request);

    /**
     * @notice Get all pending liquidity requests for a user
     * @param user User address
     * @return requestIds Array of pending request IDs
     */
    function getPendingLiquidityRequests(
        address user
    ) external view returns (bytes32[] memory requestIds);

    /**
     * @notice Callback when liquidity transfer completes
     * @param requestId The completed request
     * @param success Whether the transfer succeeded
     */
    function onLiquidityTransferComplete(
        bytes32 requestId,
        bool success
    ) external;

    /**
     * @notice Check if a chain ID is supported for liquidity transfers
     * @param chainId Chain ID to check
     * @return supported Whether the chain is supported
     */
    function supportsChainId(
        uint256 chainId
    ) external view returns (bool supported);

    /**
     * @notice Get available liquidity on a remote chain
     * @param remoteChainId Remote chain to query
     * @param token Token to check
     * @return available Amount available on that chain
     */
    function getRemoteLiquidity(
        uint256 remoteChainId,
        address token
    ) external view returns (uint256 available);
}
