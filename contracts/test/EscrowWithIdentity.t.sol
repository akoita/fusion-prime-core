// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "escrow/EscrowWithIdentity.sol";
import "identity/IdentityFactory.sol";
import "identity/ClaimIssuerRegistry.sol";
import "identity/Identity.sol";

contract EscrowWithIdentityTest is Test {
    IdentityFactory public factory;
    ClaimIssuerRegistry public registry;

    address public payer = address(0x1);
    address public payee = address(0x2);
    address public arbiter = address(0x3);
    address public issuer = address(0x4);

    function setUp() public {
        // Deploy identity system
        registry = new ClaimIssuerRegistry();
        factory = new IdentityFactory(address(registry));

        // Create identities for payer and payee
        vm.prank(payer);
        factory.createIdentity();

        vm.prank(payee);
        factory.createIdentity();

        // Fund payer
        vm.deal(payer, 10 ether);
    }

    function testCreateEscrowWithIdentity() public {
        uint256[] memory requiredClaims = new uint256[](0);

        vm.prank(payer);
        EscrowWithIdentity escrow = new EscrowWithIdentity{value: 1 ether}(
            payer,
            payee,
            0,
            1,
            address(0),
            address(factory),
            requiredClaims
        );

        assertEq(escrow.amount(), 1 ether);
        assertEq(escrow.payer(), payer);
        assertEq(escrow.payee(), payee);
    }

    function testCannotCreateEscrowWithoutIdentity() public {
        address noIdentity = address(0x99);
        uint256[] memory requiredClaims = new uint256[](0);

        vm.deal(noIdentity, 10 ether);
        vm.prank(noIdentity);
        vm.expectRevert(
            EscrowWithIdentity.IdentityVerificationRequired.selector
        );
        new EscrowWithIdentity{value: 1 ether}(
            noIdentity,
            payee,
            0,
            1,
            address(0),
            address(factory),
            requiredClaims
        );
    }

    function testEscrowWithKYCRequirement() public {
        // Setup: Add KYC issuer
        registry.addIssuer(issuer, "KYC Provider", new uint256[](0));

        // Issue KYC claims
        address payerIdentity = factory.getIdentity(payer);
        address payeeIdentity = factory.getIdentity(payee);

        // Trust the issuer in both identities
        vm.prank(payer);
        Identity(payable(payerIdentity)).addTrustedIssuer(issuer);
        vm.prank(payee);
        Identity(payable(payeeIdentity)).addTrustedIssuer(issuer);

        vm.prank(issuer);
        registry.issueClaim(
            payerIdentity,
            1,
            0,
            abi.encodePacked("KYC approved"),
            ""
        );

        vm.prank(issuer);
        registry.issueClaim(
            payeeIdentity,
            1,
            0,
            abi.encodePacked("KYC approved"),
            ""
        );

        // Create escrow with KYC requirement
        uint256[] memory requiredClaims = new uint256[](1);
        requiredClaims[0] = 1; // KYC_VERIFIED

        vm.prank(payer);
        EscrowWithIdentity escrow = new EscrowWithIdentity{value: 1 ether}(
            payer,
            payee,
            0,
            1,
            address(0),
            address(factory),
            requiredClaims
        );

        assertTrue(address(escrow) != address(0));
    }

    function testCannotCreateEscrowWithoutRequiredClaims() public {
        uint256[] memory requiredClaims = new uint256[](1);
        requiredClaims[0] = 1; // KYC_VERIFIED (but not issued)

        vm.prank(payer);
        vm.expectRevert(EscrowWithIdentity.ClaimVerificationFailed.selector);
        new EscrowWithIdentity{value: 1 ether}(
            payer,
            payee,
            0,
            1,
            address(0),
            address(factory),
            requiredClaims
        );
    }

    function testApproveAndRelease() public {
        uint256[] memory requiredClaims = new uint256[](0);

        vm.prank(payer);
        EscrowWithIdentity escrow = new EscrowWithIdentity{value: 1 ether}(
            payer,
            payee,
            0,
            1,
            address(0),
            address(factory),
            requiredClaims
        );

        uint256 payeeBalanceBefore = payee.balance;

        vm.prank(payer);
        escrow.approve();

        assertEq(payee.balance, payeeBalanceBefore + 1 ether);
        assertTrue(escrow.released());
    }

    function testCanReleaseChecksIdentity() public {
        uint256[] memory requiredClaims = new uint256[](0);

        vm.prank(payer);
        EscrowWithIdentity escrow = new EscrowWithIdentity{value: 1 ether}(
            payer,
            payee,
            0,
            1,
            address(0),
            address(factory),
            requiredClaims
        );

        assertTrue(escrow.canRelease() == false); // Not approved yet

        vm.prank(payer);
        escrow.approve();

        assertTrue(escrow.released());
    }

    function testIdentityBypass() public {
        uint256[] memory requiredClaims = new uint256[](0);

        vm.prank(payer);
        EscrowWithIdentity escrow = new EscrowWithIdentity{value: 1 ether}(
            payer,
            payee,
            0,
            2,
            arbiter,
            address(factory),
            requiredClaims
        );

        assertFalse(escrow.identityBypassEnabled());

        // Only arbiter can toggle
        vm.prank(arbiter);
        escrow.toggleIdentityBypass();

        assertTrue(escrow.identityBypassEnabled());
    }
}
