// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/Identity.sol";
import "../src/IdentityFactory.sol";
import "../src/ClaimIssuerRegistry.sol";

contract IdentityTest is Test {
    Identity public identity;
    IdentityFactory public factory;
    ClaimIssuerRegistry public registry;

    address public owner = address(0x1);
    address public user1 = address(0x2);
    address public user2 = address(0x3);
    address public issuer = address(0x4);

    function setUp() public {
        // Deploy registry
        registry = new ClaimIssuerRegistry();

        // Deploy factory
        factory = new IdentityFactory(address(registry));

        // Create identity for owner
        vm.prank(owner);
        address identityAddress = factory.createIdentity();
        identity = Identity(payable(identityAddress));
    }

    function testConstructor() public {
        // Check owner has management key
        bytes32 ownerKey = keccak256(abi.encodePacked(owner));
        assertTrue(identity.keyHasPurpose(ownerKey, 1));
    }

    function testAddKey() public {
        bytes32 newKey = keccak256(abi.encodePacked(user1));

        vm.prank(owner);
        bool success = identity.addKey(newKey, 2, 1);

        assertTrue(success);
        assertTrue(identity.keyHasPurpose(newKey, 2));
    }

    function testAddKeyUnauthorized() public {
        bytes32 newKey = keccak256(abi.encodePacked(user1));

        vm.prank(user1); // Not a management key
        vm.expectRevert("Identity: sender is not management key");
        identity.addKey(newKey, 2, 1);
    }

    function testRemoveKey() public {
        // First add a key
        bytes32 newKey = keccak256(abi.encodePacked(user1));
        vm.prank(owner);
        identity.addKey(newKey, 2, 1);

        // Then remove it
        vm.prank(owner);
        bool success = identity.removeKey(newKey, 2);

        assertTrue(success);
        assertFalse(identity.keyHasPurpose(newKey, 2));
    }

    function testCannotRemoveLastManagementKey() public {
        bytes32 ownerKey = keccak256(abi.encodePacked(owner));

        vm.prank(owner);
        vm.expectRevert("Identity: cannot remove last management key");
        identity.removeKey(ownerKey, 1);
    }

    function testAddClaim() public {
        // Add issuer as trusted
        vm.prank(owner);
        identity.addTrustedIssuer(issuer);

        // Create claim data
        uint256 topic = 1;
        bytes memory data = abi.encodePacked("KYC verified");
        bytes32 dataHash = keccak256(data);

        // Sign data (in real scenario, issuer would sign)
        bytes memory signature = new bytes(65);

        vm.prank(issuer);
        bytes32 claimId = identity.addClaim(topic, 1, issuer, signature, data, "ipfs://...");

        // Verify claim exists
        bytes32 expectedClaimId = keccak256(abi.encodePacked(issuer, topic));
        assertEq(claimId, expectedClaimId);

        (uint256 retTopic,,,,, ) = identity.getClaim(claimId);
        assertEq(retTopic, topic);
    }

    function testAddClaimUntrustedIssuer() public {
        uint256 topic = 1;
        bytes memory data = abi.encodePacked("KYC verified");
        bytes memory signature = new bytes(65);

        vm.prank(issuer); // Not trusted
        vm.expectRevert("Identity: issuer not trusted");
        identity.addClaim(topic, 1, issuer, signature, data, "");
    }

    function testRemoveClaim() public {
        // Add claim first
        vm.prank(owner);
        identity.addTrustedIssuer(issuer);

        uint256 topic = 1;
        bytes memory data = abi.encodePacked("KYC verified");
        bytes memory signature = new bytes(65);

        vm.prank(issuer);
        bytes32 claimId = identity.addClaim(topic, 1, issuer, signature, data, "");

        // Remove claim
        vm.prank(issuer);
        bool success = identity.removeClaim(claimId);

        assertTrue(success);

        // Verify claim removed
        (uint256 retTopic,,,,, ) = identity.getClaim(claimId);
        assertEq(retTopic, 0);
    }

    function testHasClaim() public {
        // Add trusted issuer and claim
        vm.prank(owner);
        identity.addTrustedIssuer(issuer);

        uint256 topic = 1;
        bytes memory data = abi.encodePacked("KYC verified");
        bytes memory signature = new bytes(65);

        vm.prank(issuer);
        identity.addClaim(topic, 1, issuer, signature, data, "");

        // Check hasClaim
        bool hasClaim = identity.hasClaim(topic);
        assertTrue(hasClaim);
    }

    function testGetClaimIdsByTopic() public {
        vm.prank(owner);
        identity.addTrustedIssuer(issuer);

        uint256 topic = 1;
        bytes memory data = abi.encodePacked("KYC verified");
        bytes memory signature = new bytes(65);

        vm.prank(issuer);
        identity.addClaim(topic, 1, issuer, signature, data, "");

        bytes32[] memory claimIds = identity.getClaimIdsByTopic(topic);
        assertEq(claimIds.length, 1);
    }
}
