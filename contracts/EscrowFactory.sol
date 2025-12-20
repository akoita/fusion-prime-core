// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.30;

import {Escrow} from "escrow/Escrow.sol";
import {EscrowDeployed} from "escrow/Events.sol";
import {InvalidParameters, DeploymentFailed} from "escrow/Errors.sol";

/// @title EscrowFactory
/// @notice Factory contract for deploying user-specific escrow instances
/// @dev Uses CREATE2 for deterministic addresses and event indexing for discovery
contract EscrowFactory {
    // Tracking
    mapping(address => address[]) public userEscrows; // payer => escrow addresses
    address[] public allEscrows;
    mapping(address => bool) public isEscrow;

    // Events and Errors are now imported from separate files

    /// @notice Deploy a new escrow contract
    /// @param payee Recipient of the escrowed funds
    /// @param releaseDelay Seconds to wait before funds can be released
    /// @param approvalsRequired Number of approvals needed (1-3)
    /// @param arbiter Optional arbiter address (use address(0) if not needed)
    /// @return escrow Address of the deployed escrow contract
    function createEscrow(address payee, uint256 releaseDelay, uint8 approvalsRequired, address arbiter)
        external
        payable
        returns (address escrow)
    {
        if (msg.value == 0) revert InvalidParameters();
        if (payee == address(0)) revert InvalidParameters();

        // Deploy escrow contract with msg.value, passing original sender as payer
        escrow = address(
            new Escrow{value: msg.value}(
                msg.sender, // payer
                payee,
                releaseDelay,
                approvalsRequired,
                arbiter
            )
        );

        if (escrow == address(0)) revert DeploymentFailed();

        // Track deployment
        userEscrows[msg.sender].push(escrow);
        allEscrows.push(escrow);
        isEscrow[escrow] = true;

        emit EscrowDeployed(escrow, msg.sender, payee, arbiter, msg.value, releaseDelay, approvalsRequired);
    }

    /// @notice Deploy escrow with deterministic address using CREATE2
    /// @param payee Recipient of the escrowed funds
    /// @param releaseDelay Seconds to wait before funds can be released
    /// @param approvalsRequired Number of approvals needed (1-3)
    /// @param arbiter Optional arbiter address
    /// @param salt Unique salt for deterministic address generation
    /// @return escrow Address of the deployed escrow contract
    function createEscrowDeterministic(
        address payee,
        uint256 releaseDelay,
        uint8 approvalsRequired,
        address arbiter,
        bytes32 salt
    ) external payable returns (address escrow) {
        if (msg.value == 0) revert InvalidParameters();
        if (payee == address(0)) revert InvalidParameters();

        // Deploy with CREATE2 for deterministic address
        escrow = address(
            new Escrow{value: msg.value, salt: salt}(
                msg.sender, // payer
                payee,
                releaseDelay,
                approvalsRequired,
                arbiter
            )
        );

        if (escrow == address(0)) revert DeploymentFailed();

        // Track deployment
        userEscrows[msg.sender].push(escrow);
        allEscrows.push(escrow);
        isEscrow[escrow] = true;

        emit EscrowDeployed(escrow, msg.sender, payee, arbiter, msg.value, releaseDelay, approvalsRequired);
    }

    /// @notice Compute the address of an escrow deployed with CREATE2
    /// @param payer Address that will create the escrow
    /// @param payee Recipient address
    /// @param releaseDelay Timelock duration
    /// @param approvalsRequired Number of approvals needed
    /// @param arbiter Arbiter address
    /// @param salt Unique salt
    /// @return predicted Predicted escrow address
    function computeEscrowAddress(
        address payer,
        address payee,
        uint256 releaseDelay,
        uint8 approvalsRequired,
        address arbiter,
        bytes32 salt
    ) external view returns (address predicted) {
        bytes memory bytecode = abi.encodePacked(
            type(Escrow).creationCode, abi.encode(payer, payee, releaseDelay, approvalsRequired, arbiter)
        );

        bytes32 hash = keccak256(abi.encodePacked(bytes1(0xff), address(this), salt, keccak256(bytecode)));

        predicted = address(uint160(uint256(hash)));
    }

    /// @notice Get all escrows created by a user
    /// @param user Address of the payer
    /// @return Array of escrow addresses
    function getUserEscrows(address user) external view returns (address[] memory) {
        return userEscrows[user];
    }

    /// @notice Get total number of escrows created
    function getEscrowCount() external view returns (uint256) {
        return allEscrows.length;
    }

    /// @notice Get paginated list of all escrows
    /// @param offset Starting index
    /// @param limit Number of escrows to return
    function getEscrows(uint256 offset, uint256 limit) external view returns (address[] memory) {
        uint256 total = allEscrows.length;
        if (offset >= total) {
            return new address[](0);
        }

        uint256 end = offset + limit;
        if (end > total) {
            end = total;
        }

        address[] memory result = new address[](end - offset);
        for (uint256 i = offset; i < end; i++) {
            result[i - offset] = allEscrows[i];
        }

        return result;
    }
}
