// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import {IAxelarGateway} from "interfaces/IAxelarInterfaces.sol";

/**
 * @title AxelarExecutable
 * @notice Base contract for contracts that want to receive cross-chain messages via Axelar
 * @dev Inherit from this contract and override _execute() to process incoming messages
 *
 * Based on: https://github.com/axelarnetwork/axelar-gmp-sdk-solidity/blob/main/contracts/executable/AxelarExecutable.sol
 */
abstract contract AxelarExecutable {
    IAxelarGateway public immutable gateway;

    error NotApprovedByGateway();
    error InvalidAddress();

    constructor(address gateway_) {
        if (gateway_ == address(0)) revert InvalidAddress();
        gateway = IAxelarGateway(gateway_);
    }

    /**
     * @notice External function called by Axelar relayers to execute cross-chain messages
     * @param commandId Unique identifier for this cross-chain call
     * @param sourceChain The chain from which the call originated (Axelar format, e.g., "ethereum-sepolia")
     * @param sourceAddress The address that initiated the call on the source chain
     * @param payload The payload data to be processed
     * @dev This function validates the call with the Axelar Gateway, then calls _execute()
     */
    function execute(
        bytes32 commandId,
        string calldata sourceChain,
        string calldata sourceAddress,
        bytes calldata payload
    ) external {
        // Validate that this call was approved by the Axelar Gateway
        bytes32 payloadHash = keccak256(payload);

        if (!gateway.validateContractCall(commandId, sourceChain, sourceAddress, payloadHash)) {
            revert NotApprovedByGateway();
        }

        // Call the internal implementation
        _execute(commandId, sourceChain, sourceAddress, payload);
    }

    /**
     * @notice Internal function to be overridden by child contracts
     * @param commandId Unique identifier for this cross-chain call
     * @param sourceChain The chain from which the call originated
     * @param sourceAddress The address that initiated the call on the source chain
     * @param payload The payload data to be processed
     * @dev Override this function to implement your custom message processing logic
     */
    function _execute(
        bytes32 commandId,
        string calldata sourceChain,
        string calldata sourceAddress,
        bytes calldata payload
    ) internal virtual;
}
