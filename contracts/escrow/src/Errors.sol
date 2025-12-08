// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.30;

/// @notice Global errors for the Fusion Prime protocol
/// @dev Errors declared for better organization and reusability

// Escrow Factory Errors
error DeploymentFailed();
error InvalidParameters();
error EscrowAlreadyExists();
error UnauthorizedAccess();

// Escrow Errors
error InsufficientFunds();
error InvalidAmount();
error InvalidAddress();
error InvalidApproval();
error AlreadyApproved();
error NotApproved();
error InvalidReleaseTime();
error EscrowNotActive();
error EscrowAlreadyReleased();
error EscrowAlreadyRefunded();

// General Errors
error Unauthorized();
error InvalidInput();
error ContractPaused();
error ContractNotInitialized();

// Additional Escrow Errors
error TimelockNotExpired();
error InsufficientApprovals();
error TransferFailed();
error InvalidConfiguration();
