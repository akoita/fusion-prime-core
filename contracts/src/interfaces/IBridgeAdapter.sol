// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.30;

/// @title IBridgeAdapter
/// @notice Unified interface for bridge adapters (Axelar, CCIP, etc.)
/// @dev Allows CrossChainVault to work with multiple bridge protocols
interface IBridgeAdapter {
    /// @notice Send a cross-chain message
    /// @param destinationChain Destination chain identifier (chain name or chain ID)
    /// @param destinationAddress Destination contract address (as string for Axelar, address for CCIP)
    /// @param payload Message payload to send
    /// @param gasToken Token to pay gas with (address(0) for native, token address for ERC20)
    /// @return messageId Unique identifier for the message
    function sendMessage(
        string memory destinationChain,
        string memory destinationAddress,
        bytes memory payload,
        address gasToken
    ) external payable returns (bytes32 messageId);

    /// @notice Estimate gas cost for sending a message
    /// @param destinationChain Destination chain identifier
    /// @param payload Message payload
    /// @return estimatedGas Estimated gas cost
    function estimateGas(
        string memory destinationChain,
        bytes memory payload
    ) external view returns (uint256 estimatedGas);

    /// @notice Get the bridge protocol name
    /// @return protocolName Name of the bridge protocol (e.g., "axelar", "ccip")
    function getProtocolName() external pure returns (string memory);

    /// @notice Check if a chain is supported by this bridge
    /// @param chainName Chain name or identifier
    /// @return isSupported True if chain is supported
    function isChainSupported(string memory chainName) external view returns (bool);

    /// @notice Get supported chains
    /// @return chains Array of supported chain identifiers
    function getSupportedChains() external view returns (string[] memory);
}
