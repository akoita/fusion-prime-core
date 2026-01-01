// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.30;

/// @notice CCIP Client library (matches CCIPAdapter.sol)
library Client {
    struct EVMTokenAmount {
        address token;
        uint256 amount;
    }

    struct EVM2AnyMessage {
        bytes receiver;
        bytes data;
        EVMTokenAmount[] tokenAmounts;
        address feeToken;
        bytes extraArgs;
    }
}

/// @title MockCCIPRouter
/// @notice Mock implementation of Chainlink CCIP Router for testing
contract MockCCIPRouter {
    mapping(bytes32 => bool) public sentMessages;

    /// @notice Send a message via CCIP (matches IRouterClient interface)
    function ccipSend(
        uint64 destinationChainSelector,
        Client.EVM2AnyMessage calldata message
    ) external payable returns (bytes32 messageId) {
        messageId = keccak256(
            abi.encodePacked(
                block.timestamp,
                block.number,
                destinationChainSelector,
                message.receiver,
                message.data
            )
        );
        sentMessages[messageId] = true;
        emit MessageSent(
            messageId,
            destinationChainSelector,
            msg.sender,
            message.data,
            msg.value
        );
        return messageId;
    }

    /// @notice Get fee for sending a message (matches IRouterClient interface)
    function getFee(
        uint64 /* destinationChainSelector */,
        Client.EVM2AnyMessage calldata message
    ) external pure returns (uint256 fee) {
        // Default fee based on payload size
        return 0.001 ether + (message.data.length * 100);
    }

    event MessageSent(
        bytes32 indexed messageId,
        uint64 destinationChainSelector,
        address indexed sender,
        bytes data,
        uint256 value
    );
}
