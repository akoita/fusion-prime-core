// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.30;

import {IBridgeAdapter} from "cross-chain/interfaces/IBridgeAdapter.sol";

/// @title BridgeManager
/// @notice Manages multiple bridge adapters and selects the best one for each route
/// @dev Provides a unified interface for cross-chain messaging across different bridge protocols
contract BridgeManager {
    // Bridge adapters by protocol name
    mapping(string => IBridgeAdapter) public adapters;
    string[] public registeredProtocols;

    // Chain routing: chain => preferred protocol
    mapping(string => string) public preferredProtocol;

    // Events
    event AdapterRegistered(string protocolName, address adapter);
    event PreferredProtocolSet(string chain, string protocol);
    event MessageRouted(string protocol, string destinationChain, bytes32 messageId);

    error AdapterNotRegistered(string protocol);
    error UnsupportedChain(string chain);
    error NoAdapterForChain(string chain);

    /// @notice Register a bridge adapter
    /// @param adapter Address of the bridge adapter contract
    function registerAdapter(IBridgeAdapter adapter) external {
        string memory protocolName = adapter.getProtocolName();
        require(address(adapters[protocolName]) == address(0), "Adapter already registered");

        adapters[protocolName] = adapter;
        registeredProtocols.push(protocolName);

        emit AdapterRegistered(protocolName, address(adapter));
    }

    /// @notice Set preferred protocol for a chain
    /// @param chainName Chain name or identifier
    /// @param protocolName Protocol name (e.g., "axelar", "ccip")
    function setPreferredProtocol(string memory chainName, string memory protocolName) external {
        require(address(adapters[protocolName]) != address(0), "Adapter not registered");
        require(adapters[protocolName].isChainSupported(chainName), "Chain not supported by adapter");

        preferredProtocol[chainName] = protocolName;
        emit PreferredProtocolSet(chainName, protocolName);
    }

    /// @notice Send message using the preferred adapter for the destination chain
    /// @param destinationChain Destination chain identifier
    /// @param destinationAddress Destination contract address
    /// @param payload Message payload
    /// @param gasToken Token to pay gas with
    /// @return messageId Unique identifier for the message
    function sendMessage(
        string memory destinationChain,
        string memory destinationAddress,
        bytes memory payload,
        address gasToken
    ) external payable returns (bytes32 messageId) {
        string memory protocol = preferredProtocol[destinationChain];

        if (bytes(protocol).length == 0) {
            // No preference set, try to find any adapter that supports the chain
            protocol = _findSupportedAdapter(destinationChain);
            if (bytes(protocol).length == 0) {
                revert NoAdapterForChain(destinationChain);
            }
        }

        IBridgeAdapter adapter = adapters[protocol];
        if (address(adapter) == address(0)) {
            revert AdapterNotRegistered(protocol);
        }

        messageId = adapter.sendMessage{value: msg.value}(
            destinationChain,
            destinationAddress,
            payload,
            gasToken
        );

        emit MessageRouted(protocol, destinationChain, messageId);
        return messageId;
    }

    /// @notice Estimate gas cost for sending a message
    /// @param destinationChain Destination chain identifier
    /// @param payload Message payload
    /// @return estimatedGas Estimated gas cost
    /// @return protocol Protocol that will be used
    function estimateGas(
        string memory destinationChain,
        bytes memory payload
    ) external view returns (uint256 estimatedGas, string memory protocol) {
        protocol = preferredProtocol[destinationChain];

        if (bytes(protocol).length == 0) {
            protocol = _findSupportedAdapter(destinationChain);
        }

        if (bytes(protocol).length == 0) {
            revert NoAdapterForChain(destinationChain);
        }

        IBridgeAdapter adapter = adapters[protocol];
        estimatedGas = adapter.estimateGas(destinationChain, payload);
        return (estimatedGas, protocol);
    }

    /// @notice Find an adapter that supports the given chain
    /// @param chainName Chain name to check
    /// @return protocolName Protocol name that supports the chain, or empty string
    function _findSupportedAdapter(string memory chainName) internal view returns (string memory) {
        for (uint256 i = 0; i < registeredProtocols.length; i++) {
            string memory protocol = registeredProtocols[i];
            IBridgeAdapter adapter = adapters[protocol];
            if (address(adapter) != address(0) && adapter.isChainSupported(chainName)) {
                return protocol;
            }
        }
        return "";
    }

    /// @notice Get registered protocols
    /// @return protocols Array of registered protocol names
    function getRegisteredProtocols() external view returns (string[] memory) {
        return registeredProtocols;
    }

    /// @notice Check if a chain is supported by any registered adapter
    /// @param chainName Chain name to check
    /// @return isSupported True if chain is supported
    function isChainSupported(string memory chainName) external view returns (bool) {
        return bytes(_findSupportedAdapter(chainName)).length > 0;
    }
}
