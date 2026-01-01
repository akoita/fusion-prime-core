// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/IdentityFactory.sol";
import "../src/ClaimIssuerRegistry.sol";
import "../src/Identity.sol";

contract IdentityFactoryTest is Test {
    IdentityFactory public factory;
    ClaimIssuerRegistry public registry;

    address public user1 = address(0x1);
    address public user2 = address(0x2);

    function setUp() public {
        registry = new ClaimIssuerRegistry();
        factory = new IdentityFactory(address(registry));
    }

    function testCreateIdentity() public {
        vm.prank(user1);
        address identityAddress = factory.createIdentity();

        assertTrue(identityAddress != address(0));
        assertEq(factory.getIdentity(user1), identityAddress);
        assertTrue(factory.hasIdentity(user1));
    }

    function testCreateIdentityFor() public {
        address identityAddress = factory.createIdentityFor(user1);

        assertTrue(identityAddress != address(0));
        assertEq(factory.getIdentity(user1), identityAddress);
    }

    function testCannotCreateDuplicateIdentity() public {
        vm.startPrank(user1);
        factory.createIdentity();

        vm.expectRevert("IdentityFactory: identity already exists");
        factory.createIdentity();
        vm.stopPrank();
    }

    function testGetIdentityCount() public {
        assertEq(factory.getIdentityCount(), 0);

        factory.createIdentityFor(user1);
        assertEq(factory.getIdentityCount(), 1);

        factory.createIdentityFor(user2);
        assertEq(factory.getIdentityCount(), 2);
    }

    function testGetIdentities() public {
        factory.createIdentityFor(user1);
        factory.createIdentityFor(user2);

        (address[] memory identities, uint256 total) = factory.getIdentities(0, 10);

        assertEq(total, 2);
        assertEq(identities.length, 2);
    }

    function testGetIdentitiesPagination() public {
        // Create 5 identities
        for (uint160 i = 1; i <= 5; i++) {
            factory.createIdentityFor(address(i));
        }

        // Get first 3
        (address[] memory page1, uint256 total1) = factory.getIdentities(0, 3);
        assertEq(total1, 5);
        assertEq(page1.length, 3);

        // Get next 2
        (address[] memory page2, uint256 total2) = factory.getIdentities(3, 3);
        assertEq(total2, 5);
        assertEq(page2.length, 2);
    }

    function testIdentityHasManagementKey() public {
        vm.prank(user1);
        address identityAddress = factory.createIdentity();

        Identity identity = Identity(payable(identityAddress));
        bytes32 userKey = keccak256(abi.encodePacked(user1));

        assertTrue(identity.keyHasPurpose(userKey, 1));
    }
}
