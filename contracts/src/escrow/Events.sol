// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.30;

/// @notice Global events for the Fusion Prime protocol
/// @dev Events declared at file level for better organization and reusability

// Escrow Factory Events
event EscrowDeployed(
    address indexed escrow,
    address indexed payer,
    address indexed payee,
    address arbiter,
    uint256 amount,
    uint256 releaseDelay,
    uint8 approvalsRequired
);

// Escrow Events
event EscrowCreated(
    address indexed payer,
    address indexed payee,
    address indexed arbiter,
    uint256 amount,
    uint256 releaseTime,
    uint8 approvalsRequired
);

event EscrowReleased(address indexed payee, uint256 amount, uint256 timestamp);

event EscrowRefunded(address indexed payer, uint256 amount, uint256 timestamp);

event ApprovalAdded(address indexed escrow, address indexed approver, uint8 currentApprovals, uint8 requiredApprovals);

event ApprovalRevoked(
    address indexed escrow, address indexed approver, uint8 currentApprovals, uint8 requiredApprovals
);

// Additional Escrow Events
event Approved(address indexed approver);

event ArbiterChanged(address indexed oldArbiter, address indexed newArbiter);
