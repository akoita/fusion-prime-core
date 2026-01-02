// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.30;

import {IAxelarGateway} from "interfaces/IAxelarInterfaces.sol";

/// @title MockAxelarGateway
/// @notice Mock implementation of IAxelarGateway for testing
contract MockAxelarGateway is IAxelarGateway {
    mapping(string => address) public tokenAddresses;
    mapping(bytes32 => bool) public validatedCommands;

    function sendToken(
        string calldata destinationChain,
        string calldata destinationAddress,
        string calldata symbol,
        uint256 amount
    ) external {}

    function callContract(
        string calldata destinationChain,
        string calldata destinationAddress,
        bytes calldata payload
    ) external {
        // Emit event to simulate message sending
        emit ContractCall(msg.sender, destinationChain, destinationAddress, keccak256(payload));
    }

    function callContractWithToken(
        string calldata destinationChain,
        string calldata destinationAddress,
        bytes calldata payload,
        string calldata symbol,
        uint256 amount
    ) external {}

    function isContractCallApproved(
        bytes32 commandId,
        string calldata sourceChain,
        string calldata sourceAddress,
        address contractAddress,
        bytes32 payloadHash
    ) external view returns (bool) {
        return validatedCommands[commandId];
    }

    function isContractCallAndMintApproved(
        bytes32 commandId,
        string calldata sourceChain,
        string calldata sourceAddress,
        address contractAddress,
        bytes32 payloadHash,
        string calldata symbol,
        uint256 amount
    ) external view returns (bool) {
        return validatedCommands[commandId];
    }

    function validateContractCall(
        bytes32 commandId,
        string calldata sourceChain,
        string calldata sourceAddress,
        bytes32 payloadHash
    ) external returns (bool) {
        validatedCommands[commandId] = true;
        return true;
    }

    function validateContractCallAndMint(
        bytes32 commandId,
        string calldata sourceChain,
        string calldata sourceAddress,
        bytes32 payloadHash,
        string calldata symbol,
        uint256 amount
    ) external returns (bool) {
        validatedCommands[commandId] = true;
        return true;
    }

    event ContractCall(
        address indexed sender,
        string destinationChain,
        string destinationAddress,
        bytes32 payloadHash
    );
}
