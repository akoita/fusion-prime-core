// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.30;

import {IAxelarGasService} from "../../src/interfaces/IAxelarInterfaces.sol";

/// @title MockAxelarGasService
/// @notice Mock implementation of IAxelarGasService for testing
contract MockAxelarGasService is IAxelarGasService {
    mapping(bytes32 => uint256) public gasPaid;

    function payNativeGasForContractCall(
        address sender,
        string calldata destinationChain,
        string calldata destinationAddress,
        bytes calldata payload,
        address refundAddress
    ) external payable {
        bytes32 messageId = keccak256(
            abi.encodePacked(sender, destinationChain, destinationAddress, payload)
        );
        gasPaid[messageId] = msg.value;
        emit NativeGasPaidForContractCall(sender, destinationChain, destinationAddress, payload, msg.value, refundAddress);
    }

    function payNativeGasForContractCallWithToken(
        address sender,
        string calldata destinationChain,
        string calldata destinationAddress,
        bytes calldata payload,
        string calldata symbol,
        uint256 amount,
        address refundAddress
    ) external payable {
        bytes32 messageId = keccak256(
            abi.encodePacked(sender, destinationChain, destinationAddress, payload, symbol, amount)
        );
        gasPaid[messageId] = msg.value;
        emit NativeGasPaidForContractCallWithToken(
            sender,
            destinationChain,
            destinationAddress,
            payload,
            symbol,
            amount,
            msg.value,
            refundAddress
        );
    }

    function payGasForContractCall(
        address sender,
        string calldata destinationChain,
        string calldata destinationAddress,
        bytes calldata payload,
        address gasToken,
        uint256 gasFeeAmount,
        address refundAddress
    ) external {
        bytes32 messageId = keccak256(
            abi.encodePacked(sender, destinationChain, destinationAddress, payload)
        );
        gasPaid[messageId] = gasFeeAmount;
        emit GasPaidForContractCall(
            sender,
            destinationChain,
            destinationAddress,
            payload,
            gasToken,
            gasFeeAmount,
            refundAddress
        );
    }

    function payGasForContractCallWithToken(
        address sender,
        string calldata destinationChain,
        string calldata destinationAddress,
        bytes calldata payload,
        string calldata symbol,
        uint256 amount,
        address gasToken,
        uint256 gasFeeAmount,
        address refundAddress
    ) external {
        bytes32 messageId = keccak256(
            abi.encodePacked(sender, destinationChain, destinationAddress, payload, symbol, amount)
        );
        gasPaid[messageId] = gasFeeAmount;
        emit GasPaidForContractCallWithToken(
            sender,
            destinationChain,
            destinationAddress,
            payload,
            symbol,
            amount,
            gasToken,
            gasFeeAmount,
            refundAddress
        );
    }

    function addNativeGas(
        bytes32 txHash,
        uint256 logIndex,
        address refundAddress
    ) external payable {
        emit NativeGasAdded(txHash, logIndex, msg.value, refundAddress);
    }

    function addGas(
        bytes32 txHash,
        uint256 logIndex,
        address gasToken,
        uint256 gasFeeAmount,
        address refundAddress
    ) external {
        emit GasAdded(txHash, logIndex, gasToken, gasFeeAmount, refundAddress);
    }

    event NativeGasPaidForContractCall(
        address indexed sender,
        string destinationChain,
        string destinationAddress,
        bytes payload,
        uint256 gasFeeAmount,
        address refundAddress
    );

    event NativeGasPaidForContractCallWithToken(
        address indexed sender,
        string destinationChain,
        string destinationAddress,
        bytes payload,
        string symbol,
        uint256 amount,
        uint256 gasFeeAmount,
        address refundAddress
    );

    event GasPaidForContractCall(
        address indexed sender,
        string destinationChain,
        string destinationAddress,
        bytes payload,
        address gasToken,
        uint256 gasFeeAmount,
        address refundAddress
    );

    event GasPaidForContractCallWithToken(
        address indexed sender,
        string destinationChain,
        string destinationAddress,
        bytes payload,
        string symbol,
        uint256 amount,
        address gasToken,
        uint256 gasFeeAmount,
        address refundAddress
    );

    event NativeGasAdded(bytes32 indexed txHash, uint256 indexed logIndex, uint256 gasFeeAmount, address refundAddress);
    event GasAdded(
        bytes32 indexed txHash,
        uint256 indexed logIndex,
        address gasToken,
        uint256 gasFeeAmount,
        address refundAddress
    );
}
