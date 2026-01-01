// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.30;

import {Test, console2} from "forge-std/Test.sol";
import {Escrow} from "../src/Escrow.sol";
import {
    TimelockNotExpired,
    AlreadyApproved,
    EscrowAlreadyReleased,
    EscrowAlreadyRefunded,
    Unauthorized
} from "../src/Errors.sol";

contract EscrowLifecycleExtendedTest is Test {
    Escrow public escrow;
    address public payer = address(0x1);
    address public payee = address(0x2);
    address public arbiter = address(0x3);
    address public secondArbiter = address(0x4);
    uint256 public constant AMOUNT = 1 ether;
    uint256 public constant RELEASE_DELAY = 1 days;

    event ArbiterChanged(
        address indexed oldArbiter,
        address indexed newArbiter
    );
    event EscrowReleased(
        address indexed payee,
        uint256 amount,
        uint256 timestamp
    );

    function setUp() public {
        vm.deal(payer, 10 ether);
        vm.prank(payer);
        // Create a 2/3 multi-sig with arbiter
        escrow = new Escrow{value: AMOUNT}(
            payer,
            payee,
            RELEASE_DELAY,
            2,
            arbiter
        );
    }

    function testArbiterUpdateFlow() public {
        // Only current arbiter can change arbiter
        vm.prank(payer);
        vm.expectRevert(Unauthorized.selector);
        escrow.changeArbiter(secondArbiter);

        // Success flow
        vm.prank(arbiter);
        vm.expectEmit(true, true, false, true);
        emit ArbiterChanged(arbiter, secondArbiter);
        escrow.changeArbiter(secondArbiter);

        assertEq(escrow.arbiter(), secondArbiter);

        // Verify new arbiter can approve
        vm.prank(payer);
        escrow.approve();

        vm.prank(secondArbiter);
        escrow.approve();

        assertEq(escrow.approvalsCount(), 2);
    }

    function testArbiterReleaseCompetitive() public {
        // Setup: Payer approves
        vm.prank(payer);
        escrow.approve();

        // Still can't release (needs 2 approvals)
        assertFalse(escrow.canRelease());

        // Arbiter approves
        vm.prank(arbiter);
        escrow.approve();

        // 2/3 met, but timelock still active (1 day delay)
        assertFalse(escrow.released());
        assertFalse(escrow.canRelease());

        // Fast forward 1 day
        uint256 currentTime = block.timestamp + 1 days + 1;
        vm.warp(currentTime);
        assertTrue(escrow.canRelease());

        // Arbiter releases
        vm.prank(arbiter);
        vm.expectEmit(true, false, false, true);
        emit EscrowReleased(payee, AMOUNT, currentTime);
        escrow.release();

        assertTrue(escrow.released());
    }

    function testCannotReleaseTwice() public {
        vm.prank(payer);
        escrow.approve();
        vm.prank(arbiter);
        escrow.approve();

        vm.warp(block.timestamp + 1 days + 1);

        // First release
        escrow.release();
        assertTrue(escrow.released());

        // Second release should fail
        vm.expectRevert(EscrowAlreadyReleased.selector);
        escrow.release();
    }

    function testAutoReleaseIfTimelockAlreadyExpired() public {
        // Setup: Payer approves early
        vm.prank(payer);
        escrow.approve();

        // Warp past timelock BEFORE final approval
        vm.warp(block.timestamp + 1 days + 1);

        // Final approval should auto-trigger release
        vm.prank(arbiter);
        escrow.approve();

        assertTrue(escrow.released());
        assertEq(payee.balance, AMOUNT);
    }

    function testRefundBlocksRelease() public {
        // Warp past 30 days timeout
        vm.warp(block.timestamp + 32 days);

        // Payer refunds
        vm.prank(payer);
        escrow.refund();
        assertTrue(escrow.refunded());

        // Now even if approved, should not be able to release
        vm.prank(arbiter);
        vm.expectRevert(EscrowAlreadyRefunded.selector);
        escrow.approve();
    }
}
