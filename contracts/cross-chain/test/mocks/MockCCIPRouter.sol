// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.30;

/// @title MockCCIPRouter
/// @notice Mock implementation of Chainlink CCIP Router for testing
contract MockCCIPRouter {
    mapping(uint64 => mapping(bytes => uint256)) public fees;
    mapping(bytes32 => bool) public sentMessages;

    /// @notice Send a message via CCIP
    /// @param destinationChainSelector Destination chain selector
    /// @param receiverAndCalldata Encoded receiver address + calldata
    /// @return messageId Unique message identifier
    function send(
        uint64 destinationChainSelector,
        bytes memory receiverAndCalldata
    ) external payable returns (bytes32 messageId) {
        messageId = keccak256(abi.encodePacked(block.timestamp, block.number, destinationChainSelector, receiverAndCalldata));
        sentMessages[messageId] = true;
        emit MessageSent(messageId, destinationChainSelector, msg.sender, receiverAndCalldata, msg.value);
        return messageId;
    }

    /// @notice Get fee for sending a message
    /// @param destinationChainSelector Destination chain selector
    /// @param receiverAndCalldata Encoded receiver address + calldata
    /// @return fee Estimated fee in native token
    function getFee(
        uint64 destinationChainSelector,
        bytes memory receiverAndCalldata
    ) external view returns (uint256 fee) {
        // Return stored fee or default
        if (fees[destinationChainSelector][receiverAndCalldata] > 0) {
            return fees[destinationChainSelector][receiverAndCalldata];
        }
        // Default fee based on payload size
        return 0.001 ether + (receiverAndCalldata.length * 100);
    }

    /// @notice Set a custom fee for testing
    /// @param destinationChainSelector Chain selector
    /// @param receiverAndCalldata Encoded data
    /// @param fee Fee amount
    function setFee(
        uint64 destinationChainSelector,
        bytes memory receiverAndCalldata,
        uint256 fee
    ) external {
        fees[destinationChainSelector][receiverAndCalldata] = fee;
    }

    event MessageSent(
        bytes32 indexed messageId,
        uint64 destinationChainSelector,
        address indexed sender,
        bytes receiverAndCalldata,
        uint256 value
    );
}
