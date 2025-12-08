// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.30;

import {Test, console2} from "forge-std/Test.sol";
import {Escrow} from "../src/Escrow.sol";
import {TimelockNotExpired, AlreadyApproved, EscrowAlreadyReleased, Unauthorized} from "../src/Errors.sol";

contract EscrowTest is Test {
    Escrow public escrow;
    address public payer = address(0x1);
    address public payee = address(0x2);
    address public arbiter = address(0x3);
    uint256 public constant AMOUNT = 1 ether;
    uint256 public constant RELEASE_DELAY = 1 days;

    function setUp() public {
        vm.deal(payer, 10 ether);
    }

    function testCreateEscrow() public {
        vm.prank(payer);
        escrow = new Escrow{value: AMOUNT}(payer, payee, RELEASE_DELAY, 2, address(0));

        assertEq(escrow.payer(), payer);
        assertEq(escrow.payee(), payee);
        assertEq(escrow.amount(), AMOUNT);
        assertEq(escrow.approvalsRequired(), 2);
        assertEq(escrow.releaseTime(), block.timestamp + RELEASE_DELAY);
    }

    function testApproveAndRelease() public {
        vm.prank(payer);
        escrow = new Escrow{value: AMOUNT}(payer, payee, 0, 2, address(0));

        // Payer approves
        vm.prank(payer);
        escrow.approve();
        assertEq(escrow.approvalsCount(), 1);

        // Payee approves - should auto-release since no timelock
        uint256 payeeBalanceBefore = payee.balance;
        vm.prank(payee);
        escrow.approve();

        assertEq(escrow.approvalsCount(), 2);
        assertTrue(escrow.released());
        assertEq(payee.balance, payeeBalanceBefore + AMOUNT);
    }

    function testTimelockPreventsEarlyRelease() public {
        vm.prank(payer);
        escrow = new Escrow{value: AMOUNT}(payer, payee, RELEASE_DELAY, 2, address(0));

        // Both approve
        vm.prank(payer);
        escrow.approve();
        vm.prank(payee);
        escrow.approve();

        // Should not auto-release due to timelock
        assertFalse(escrow.released());

        // Try manual release before timelock expires
        vm.expectRevert(TimelockNotExpired.selector);
        escrow.release();

        // Warp past timelock
        vm.warp(block.timestamp + RELEASE_DELAY + 1);

        // Now release should work
        uint256 payeeBalanceBefore = payee.balance;
        escrow.release();

        assertTrue(escrow.released());
        assertEq(payee.balance, payeeBalanceBefore + AMOUNT);
    }

    function testThreePartyApproval() public {
        vm.prank(payer);
        escrow = new Escrow{value: AMOUNT}(payer, payee, 0, 3, arbiter);

        // Only payer and payee approve
        vm.prank(payer);
        escrow.approve();
        vm.prank(payee);
        escrow.approve();

        // Should not release yet (need 3 approvals)
        assertFalse(escrow.released());

        // Arbiter approves
        uint256 payeeBalanceBefore = payee.balance;
        vm.prank(arbiter);
        escrow.approve();

        assertTrue(escrow.released());
        assertEq(payee.balance, payeeBalanceBefore + AMOUNT);
    }

    function testRefundAfterTimeout() public {
        vm.prank(payer);
        escrow = new Escrow{value: AMOUNT}(payer, payee, RELEASE_DELAY, 2, address(0));

        // Only payer approves
        vm.prank(payer);
        escrow.approve();

        // Try refund too early
        vm.prank(payer);
        vm.expectRevert(TimelockNotExpired.selector);
        escrow.refund();

        // Warp past release time + 30 days
        vm.warp(block.timestamp + RELEASE_DELAY + 30 days + 1);

        // Refund should work now
        uint256 payerBalanceBefore = payer.balance;
        vm.prank(payer);
        escrow.refund();

        assertTrue(escrow.refunded());
        assertEq(payer.balance, payerBalanceBefore + AMOUNT);
    }

    function testCannotApproveAfterRelease() public {
        vm.prank(payer);
        escrow = new Escrow{value: AMOUNT}(payer, payee, 0, 2, address(0));

        vm.prank(payer);
        escrow.approve();
        vm.prank(payee);
        escrow.approve();

        assertTrue(escrow.released());

        // Try to approve again
        vm.prank(arbiter);
        vm.expectRevert(EscrowAlreadyReleased.selector);
        escrow.approve();
    }

    function testCannotDoubleApprove() public {
        vm.prank(payer);
        escrow = new Escrow{value: AMOUNT}(payer, payee, RELEASE_DELAY, 2, address(0));

        vm.prank(payer);
        escrow.approve();

        // Try to approve again as payer
        vm.prank(payer);
        vm.expectRevert(AlreadyApproved.selector);
        escrow.approve();
    }

    function testUnauthorizedCannotApprove() public {
        vm.prank(payer);
        escrow = new Escrow{value: AMOUNT}(payer, payee, RELEASE_DELAY, 2, address(0));

        // Random address tries to approve
        vm.prank(address(0x999));
        vm.expectRevert(Unauthorized.selector);
        escrow.approve();
    }

    function testChangeArbiter() public {
        vm.prank(payer);
        escrow = new Escrow{value: AMOUNT}(payer, payee, RELEASE_DELAY, 3, arbiter);

        address newArbiter = address(0x4);

        // Current arbiter changes to new arbiter
        vm.prank(arbiter);
        escrow.changeArbiter(newArbiter);

        assertEq(escrow.arbiter(), newArbiter);
    }

    function testCanReleaseView() public {
        vm.prank(payer);
        escrow = new Escrow{value: AMOUNT}(payer, payee, RELEASE_DELAY, 2, address(0));

        assertFalse(escrow.canRelease());

        // Approve both
        vm.prank(payer);
        escrow.approve();
        vm.prank(payee);
        escrow.approve();

        // Still can't release due to timelock
        assertFalse(escrow.canRelease());

        // Warp past timelock
        vm.warp(block.timestamp + RELEASE_DELAY + 1);

        // Now can release
        assertTrue(escrow.canRelease());
    }

    function testGetStatus() public {
        vm.prank(payer);
        escrow = new Escrow{value: AMOUNT}(payer, payee, RELEASE_DELAY, 2, address(0));

        (
            bool _released,
            bool _refunded,
            uint8 _approvalsCount,
            uint8 _approvalsRequired,
            uint256 _releaseTime,
            bool _canRelease
        ) = escrow.getStatus();

        assertFalse(_released);
        assertFalse(_refunded);
        assertEq(_approvalsCount, 0);
        assertEq(_approvalsRequired, 2);
        assertEq(_releaseTime, block.timestamp + RELEASE_DELAY);
        assertFalse(_canRelease);
    }

    function testFuzzApprovals(uint8 approvalsRequired) public {
        // Limit to valid range
        vm.assume(approvalsRequired >= 1 && approvalsRequired <= 2);

        vm.prank(payer);
        escrow = new Escrow{value: AMOUNT}(payer, payee, 0, approvalsRequired, address(0));

        if (approvalsRequired == 1) {
            vm.prank(payer);
            escrow.approve();
            assertTrue(escrow.released());
        } else {
            vm.prank(payer);
            escrow.approve();
            assertFalse(escrow.released());

            vm.prank(payee);
            escrow.approve();
            assertTrue(escrow.released());
        }
    }
}
