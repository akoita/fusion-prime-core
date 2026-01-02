// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.30;

import {IBridgeAdapter} from "interfaces/IBridgeAdapter.sol";
import {StringAddressUtils} from "interfaces/IAxelarInterfaces.sol";

/// @notice MessageBridge interface
interface IMessageBridge {
    function sendMessage(
        uint64 destChainId,
        address recipient,
        bytes calldata payload
    ) external returns (bytes32 messageId);
}

/// @title MessageBridgeAdapter
/// @notice Bridge adapter for custom MessageBridge system
/// @dev Implements IBridgeAdapter for our relayer-based bridge
contract MessageBridgeAdapter is IBridgeAdapter {
    using StringAddressUtils for string;

    /// @notice MessageBridge contract
    IMessageBridge public immutable messageBridge;

    /// @notice Mapping from chain names to chain IDs
    mapping(string => uint64) public chainNameToId;

    /// @notice Mapping from chain ID to chain names
    mapping(uint64 => string) public chainIdToName;

    /// @notice Supported chains
    string[] public supportedChains;

    event MessageSent(string destinationChain, uint64 destinationChainId, address destinationAddress, bytes32 messageId);

    /// @notice Constructor
    /// @param _messageBridge MessageBridge contract address
    /// @param _chainNames Array of chain names
    /// @param _chainIds Array of chain IDs corresponding to names
    constructor(
        address _messageBridge,
        string[] memory _chainNames,
        uint64[] memory _chainIds
    ) {
        require(_chainNames.length == _chainIds.length, "Mismatched arrays");
        require(_messageBridge != address(0), "Invalid MessageBridge address");

        messageBridge = IMessageBridge(_messageBridge);

        for (uint256 i = 0; i < _chainNames.length; i++) {
            chainNameToId[_chainNames[i]] = _chainIds[i];
            chainIdToName[_chainIds[i]] = _chainNames[i];
            supportedChains.push(_chainNames[i]);
        }
    }

    /// @inheritdoc IBridgeAdapter
    function sendMessage(
        string memory destinationChain,
        string memory destinationAddress,
        bytes memory payload,
        address /* gasToken - MessageBridge doesn't use gas tokens */
    ) external payable returns (bytes32 messageId) {
        require(isChainSupported(destinationChain), "Unsupported destination chain");

        uint64 destChainId = chainNameToId[destinationChain];
        address destination = destinationAddress.toAddress();

        // Send via MessageBridge
        messageId = messageBridge.sendMessage(destChainId, destination, payload);

        emit MessageSent(destinationChain, destChainId, destination, messageId);
        return messageId;
    }

    /// @inheritdoc IBridgeAdapter
    function estimateGas(
        string memory destinationChain,
        bytes memory /* payload */
    ) external view returns (uint256 estimatedGas) {
        require(isChainSupported(destinationChain), "Unsupported destination chain");

        // MessageBridge is essentially free - relayer pays for destination execution
        // Only cost is source chain transaction gas, which is negligible
        // Return a small nominal amount for compatibility
        return 100000; // ~0.0001 ETH at 1 gwei
    }

    /// @inheritdoc IBridgeAdapter
    function getProtocolName() external pure returns (string memory) {
        return "messagebridge";
    }

    /// @inheritdoc IBridgeAdapter
    function isChainSupported(string memory chainName) public view returns (bool) {
        return chainNameToId[chainName] != 0;
    }

    /// @inheritdoc IBridgeAdapter
    function getSupportedChains() external view returns (string[] memory) {
        return supportedChains;
    }

    /// @notice Get chain ID for a chain name
    /// @param chainName Chain name
    /// @return chainId Chain ID
    function getChainId(string memory chainName) external view returns (uint64) {
        return chainNameToId[chainName];
    }

    /// @notice Get chain name for a chain ID
    /// @param chainId Chain ID
    /// @return chainName Chain name
    function getChainName(uint64 chainId) external view returns (string memory) {
        return chainIdToName[chainId];
    }
}
