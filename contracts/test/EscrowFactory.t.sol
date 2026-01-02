// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.30;

import {Test, console2} from "forge-std/Test.sol";
import {EscrowFactory} from "escrow/EscrowFactory.sol";
import {Escrow} from "escrow/Escrow.sol";
import {EscrowDeployed} from "escrow/Events.sol";
import {InvalidParameters} from "escrow/Errors.sol";

contract EscrowFactoryTest is Test {
    EscrowFactory public factory;
    address public payer = address(0x1);
    address public payee = address(0x2);
    address public arbiter = address(0x3);
    uint256 public constant AMOUNT = 1 ether;

    function setUp() public {
        factory = new EscrowFactory();
        vm.deal(payer, 100 ether);
    }

    function testCreateEscrow() public {
        vm.prank(payer);
        address escrowAddr = factory.createEscrow{value: AMOUNT}(
            payee,
            1 days,
            2,
            address(0)
        );

        assertTrue(
            escrowAddr != address(0),
            "Escrow address should not be zero"
        );
        assertTrue(factory.isEscrow(escrowAddr));
        assertEq(factory.getEscrowCount(), 1);

        Escrow escrow = Escrow(payable(escrowAddr));
        assertEq(escrow.payer(), payer);
        assertEq(escrow.payee(), payee);
        assertEq(escrow.amount(), AMOUNT);
    }

    function testCreateMultipleEscrows() public {
        vm.startPrank(payer);

        address escrow1 = factory.createEscrow{value: AMOUNT}(
            payee,
            1 days,
            2,
            address(0)
        );
        address escrow2 = factory.createEscrow{value: AMOUNT}(
            address(0x4),
            2 days,
            1,
            address(0)
        );

        vm.stopPrank();

        assertEq(factory.getEscrowCount(), 2);

        address[] memory userEscrows = factory.getUserEscrows(payer);
        assertEq(userEscrows.length, 2);
        assertEq(userEscrows[0], escrow1);
        assertEq(userEscrows[1], escrow2);
    }

    function testCreateEscrowDeterministic() public {
        bytes32 salt = keccak256("test_salt");

        // Compute expected address
        address predicted = factory.computeEscrowAddress(
            payer,
            payee,
            1 days,
            2,
            address(0),
            salt
        );

        // Deploy with CREATE2
        vm.prank(payer);
        address escrowAddr = factory.createEscrowDeterministic{value: AMOUNT}(
            payee,
            1 days,
            2,
            address(0),
            salt
        );

        // Addresses should match
        assertEq(escrowAddr, predicted);
        assertTrue(factory.isEscrow(escrowAddr));
    }

    function testCannotCreateWithZeroValue() public {
        vm.prank(payer);
        vm.expectRevert(InvalidParameters.selector);
        factory.createEscrow{value: 0}(payee, 1 days, 2, address(0));
    }

    function testCannotCreateWithZeroPayee() public {
        vm.prank(payer);
        vm.expectRevert(InvalidParameters.selector);
        factory.createEscrow{value: AMOUNT}(address(0), 1 days, 2, address(0));
    }

    function testGetEscrowsPagination() public {
        vm.startPrank(payer);

        // Create 5 escrows
        for (uint256 i = 0; i < 5; i++) {
            factory.createEscrow{value: AMOUNT}(payee, 1 days, 2, address(0));
        }

        vm.stopPrank();

        // Get first 3
        address[] memory page1 = factory.getEscrows(0, 3);
        assertEq(page1.length, 3);

        // Get next 2
        address[] memory page2 = factory.getEscrows(3, 3);
        assertEq(page2.length, 2);

        // Get beyond limit (should return empty)
        address[] memory page3 = factory.getEscrows(10, 3);
        assertEq(page3.length, 0);
    }

    function testFactoryTracksMultipleUsers() public {
        address payer2 = address(0x5);
        vm.deal(payer2, 100 ether);

        // Payer 1 creates 2 escrows
        vm.startPrank(payer);
        factory.createEscrow{value: AMOUNT}(payee, 1 days, 2, address(0));
        factory.createEscrow{value: AMOUNT}(payee, 1 days, 2, address(0));
        vm.stopPrank();

        // Payer 2 creates 1 escrow
        vm.prank(payer2);
        factory.createEscrow{value: AMOUNT}(payee, 1 days, 2, address(0));

        assertEq(factory.getUserEscrows(payer).length, 2);
        assertEq(factory.getUserEscrows(payer2).length, 1);
        assertEq(factory.getEscrowCount(), 3);
    }

    function testEscrowDeployedEvent() public {
        vm.prank(payer);
        // Check only indexed parameters (payer, payee) and non-indexed data
        vm.expectEmit(false, true, true, false);
        emit EscrowDeployed(
            address(0), // Address unknown before deployment
            payer,
            payee,
            address(0), // Arbiter
            AMOUNT,
            1 days,
            2
        );

        factory.createEscrow{value: AMOUNT}(payee, 1 days, 2, address(0));
    }

    function testDeterministicAddressComputation() public {
        bytes32 salt1 = keccak256("salt1");
        bytes32 salt2 = keccak256("salt2");

        address predicted1 = factory.computeEscrowAddress(
            payer,
            payee,
            1 days,
            2,
            address(0),
            salt1
        );

        address predicted2 = factory.computeEscrowAddress(
            payer,
            payee,
            1 days,
            2,
            address(0),
            salt2
        );

        // Different salts should produce different addresses
        assertTrue(predicted1 != predicted2);

        // Deploy with salt1
        vm.prank(payer);
        address deployed = factory.createEscrowDeterministic{value: AMOUNT}(
            payee,
            1 days,
            2,
            address(0),
            salt1
        );

        assertEq(deployed, predicted1);
    }
}
