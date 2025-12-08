// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.30;

import {
    EscrowCreated,
    EscrowReleased,
    EscrowRefunded,
    ApprovalAdded,
    ApprovalRevoked,
    Approved,
    ArbiterChanged
} from "./Events.sol";
import {
    Unauthorized,
    AlreadyApproved,
    EscrowAlreadyReleased,
    EscrowAlreadyRefunded,
    TimelockNotExpired,
    InsufficientApprovals,
    TransferFailed,
    InvalidConfiguration
} from "./Errors.sol";

/// @title Escrow
/// @notice Enhanced escrow contract with timelocks, multi-sig approvals, and emergency refunds.
/// @dev Supports programmable release conditions for institutional settlement workflows.
contract Escrow {
    // Participants
    address public payer;
    address public payee;
    address public arbiter; // Optional third-party arbiter

    // Escrow state
    uint256 public amount;
    uint256 public createdAt;
    uint256 public releaseTime; // Timelock: funds can't be released before this
    bool public released;
    bool public refunded;

    // Approval tracking
    mapping(address => bool) public approvals;
    uint8 public approvalsRequired; // Number of approvals needed (1-3)
    uint8 public approvalsCount;

    // Events and Errors are now imported from separate files

    /// @notice Create an escrow with configurable release conditions
    /// @param _payer Address of the payer (funds sender)
    /// @param _payee Recipient of the escrowed funds
    /// @param _releaseDelay Seconds to wait before funds can be released (timelock)
    /// @param _approvalsRequired Number of approvals needed (1=payer only, 2=payer+payee, 3=includes arbiter)
    /// @param _arbiter Optional arbiter address (use address(0) if not needed)
    constructor(address _payer, address _payee, uint256 _releaseDelay, uint8 _approvalsRequired, address _arbiter)
        payable {
        if (msg.value == 0) revert InvalidConfiguration();
        if (_payer == address(0)) revert InvalidConfiguration();
        if (_payee == address(0)) revert InvalidConfiguration();
        if (_approvalsRequired < 1 || _approvalsRequired > 3) revert InvalidConfiguration();
        if (_approvalsRequired == 3 && _arbiter == address(0)) revert InvalidConfiguration();

        payer = _payer;
        payee = _payee;
        arbiter = _arbiter;
        amount = msg.value;
        createdAt = block.timestamp;
        releaseTime = block.timestamp + _releaseDelay;
        approvalsRequired = _approvalsRequired;

        emit EscrowCreated(payer, payee, amount, releaseTime, approvalsRequired);
    }

    /// @notice Approve the escrow release
    /// @dev Can be called by payer, payee, or arbiter depending on configuration
    function approve() external {
        if (released) revert EscrowAlreadyReleased();
        if (refunded) revert EscrowAlreadyRefunded();
        if (approvals[msg.sender]) revert AlreadyApproved();
        if (msg.sender != payer && msg.sender != payee && (arbiter == address(0) || msg.sender != arbiter)) {
            revert Unauthorized();
        }

        approvals[msg.sender] = true;
        approvalsCount++;

        emit Approved(msg.sender);

        // Auto-release if conditions met
        if (approvalsCount >= approvalsRequired && block.timestamp >= releaseTime) {
            _release();
        }
    }

    /// @notice Manually trigger release after conditions are met
    function release() external {
        if (released) revert EscrowAlreadyReleased();
        if (refunded) revert EscrowAlreadyRefunded();
        if (block.timestamp < releaseTime) revert TimelockNotExpired();
        if (approvalsCount < approvalsRequired) revert InsufficientApprovals();

        _release();
    }

    /// @notice Refund payer if release conditions not met and timelock expired by 30 days
    /// @dev Emergency escape hatch if payee never approves
    function refund() external {
        if (released) revert EscrowAlreadyReleased();
        if (refunded) revert EscrowAlreadyRefunded();
        if (msg.sender != payer) revert Unauthorized();
        if (block.timestamp < releaseTime + 30 days) revert TimelockNotExpired();

        refunded = true;
        emit EscrowRefunded(payer, amount, block.timestamp);

        (bool ok,) = payer.call{value: amount}("");
        if (!ok) revert TransferFailed();
    }

    /// @notice Change arbiter (can only be called by current arbiter or payer if no arbiter set)
    function changeArbiter(address newArbiter) external {
        if (released) revert EscrowAlreadyReleased();
        if (refunded) revert EscrowAlreadyRefunded();
        if (arbiter != address(0) && msg.sender != arbiter) revert Unauthorized();
        if (arbiter == address(0) && msg.sender != payer) revert Unauthorized();

        address oldArbiter = arbiter;
        arbiter = newArbiter;
        emit ArbiterChanged(oldArbiter, newArbiter);
    }

    /// @notice Internal release logic
    function _release() internal {
        released = true;
        emit EscrowReleased(payee, amount, block.timestamp);

        (bool ok,) = payee.call{value: amount}("");
        if (!ok) revert TransferFailed();
    }

    /// @notice Check if escrow is ready to be released
    function canRelease() external view returns (bool) {
        return !released && !refunded && approvalsCount >= approvalsRequired && block.timestamp >= releaseTime;
    }

    /// @notice Get escrow status summary
    function getStatus()
        external
        view
        returns (
            bool _released,
            bool _refunded,
            uint8 _approvalsCount,
            uint8 _approvalsRequired,
            uint256 _releaseTime,
            bool _canRelease
        )
    {
        return (
            released,
            refunded,
            approvalsCount,
            approvalsRequired,
            releaseTime,
            !released && !refunded && approvalsCount >= approvalsRequired && block.timestamp >= releaseTime
        );
    }
}
// Test comment
