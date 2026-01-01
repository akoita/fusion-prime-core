// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import "forge-std/Test.sol";
import "../src/CrossChainVault.sol";
import "../src/InterestRateModel.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

// Mock ERC20 Token
contract MockERC20 is ERC20 {
    constructor(string memory name, string memory symbol) ERC20(name, symbol) {}

    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }
}

// Mock Price Oracle
contract MockPriceOracle {
    mapping(address => uint256) public prices;

    function setPrice(address token, uint256 price) external {
        prices[token] = price;
    }

    function getTokenPrice(address token) external view returns (uint256) {
        return prices[token];
    }

    function convertTokenToUSD(
        address token,
        uint256 amount
    ) external view returns (uint256) {
        return (amount * prices[token]) / 1e18;
    }

    // For ETH collateral (uses address(0) price)
    function convertToUSD(uint256 amount) external view returns (uint256) {
        return (amount * prices[address(0)]) / 1e18;
    }

    // Convert USD to token amount
    function convertUSDToToken(
        address token,
        uint256 usdAmount
    ) external view returns (uint256) {
        if (prices[token] == 0) return 0;
        return (usdAmount * 1e18) / prices[token];
    }
}

// Mock Identity Contract (ERC-735)
contract MockIdentity {
    mapping(uint256 => bytes32[]) public claimIdsByTopic;
    mapping(bytes32 => ClaimData) public claims;

    struct ClaimData {
        uint256 topic;
        uint256 scheme;
        address issuer;
        bytes signature;
        bytes data;
        string uri;
    }

    function addClaim(
        uint256 topic,
        address issuer
    ) external returns (bytes32) {
        bytes32 claimId = keccak256(abi.encode(issuer, topic));
        claimIdsByTopic[topic].push(claimId);
        claims[claimId] = ClaimData({
            topic: topic,
            scheme: 1,
            issuer: issuer,
            signature: "",
            data: "",
            uri: ""
        });
        return claimId;
    }

    function getClaimIdsByTopic(
        uint256 topic
    ) external view returns (bytes32[] memory) {
        return claimIdsByTopic[topic];
    }

    function getClaim(
        bytes32 claimId
    )
        external
        view
        returns (
            uint256,
            uint256,
            address,
            bytes memory,
            bytes memory,
            string memory
        )
    {
        ClaimData storage c = claims[claimId];
        return (c.topic, c.scheme, c.issuer, c.signature, c.data, c.uri);
    }
}

contract CrossChainVaultTest is Test {
    CrossChainVault public vault;
    InterestRateModel public interestRateModel;
    MockPriceOracle public oracle;
    MockERC20 public usdc;
    MockIdentity public identity;

    address public owner = address(this);
    address public user1 = address(0x1);
    address public user2 = address(0x2);
    address public trustedIssuer = address(0x100);
    address public mockGateway = address(0xABC);
    address public mockGasService = address(0xDEF);

    uint256 constant INITIAL_BALANCE = 10_000 * 1e18;
    uint256 constant ETH_PRICE = 2000 * 1e18; // $2000 per ETH
    uint256 constant USDC_PRICE = 1 * 1e18; // $1 per USDC

    function setUp() public {
        // Deploy contracts
        oracle = new MockPriceOracle();
        interestRateModel = new InterestRateModel();
        usdc = new MockERC20("USD Coin", "USDC");
        identity = new MockIdentity();

        // Deploy vault (use mock addresses for gateway/gas service in tests)
        vault = new CrossChainVault(
            mockGateway,
            mockGasService,
            address(oracle),
            address(interestRateModel)
        );

        // Setup oracle prices
        oracle.setPrice(address(0), ETH_PRICE); // ETH
        oracle.setPrice(address(usdc), USDC_PRICE); // USDC

        // Setup vault token (V30/V31 uses addToken)
        vault.addToken(address(usdc), 8500); // 85% collateral factor

        // Add trusted issuer
        vault.addTrustedIssuer(trustedIssuer);

        // Setup users
        vm.deal(user1, 100 ether);
        vm.deal(user2, 100 ether);
        usdc.mint(user1, INITIAL_BALANCE);
        usdc.mint(user2, INITIAL_BALANCE);
        usdc.mint(address(vault), INITIAL_BALANCE * 10); // Liquidity

        // Setup identity for user1
        identity.addClaim(1, trustedIssuer); // KYC_VERIFIED claim

        vm.prank(user1);
        vault.registerIdentity(address(identity));
    }

    // ========== COMPLIANCE MODE TESTS ==========

    function testComplianceModeDefaultPermissionless() public view {
        assertEq(
            uint256(vault.complianceMode()),
            uint256(CrossChainVault.ComplianceMode.PERMISSIONLESS)
        );
    }

    function testPermissionlessModeAllowsAnyoneToDeposit() public {
        // user2 has no identity registered
        vm.prank(user2);
        vault.deposit{value: 1 ether}();

        (uint256 collateral, , , , , ) = vault.positions(user2);
        assertEq(collateral, 1 ether);
    }

    function testWhitelistModeRequiresKYC() public {
        // Enable whitelist mode
        vault.setComplianceMode(CrossChainVault.ComplianceMode.WHITELIST);

        // user2 has no identity, should fail
        vm.prank(user2);
        vm.expectRevert(CrossChainVault.KYCRequired.selector);
        vault.deposit{value: 1 ether}();

        // user1 has identity with KYC claim, should succeed
        vm.prank(user1);
        vault.deposit{value: 1 ether}();

        (uint256 collateral, , , , , ) = vault.positions(user1);
        assertEq(collateral, 1 ether);
    }

    // ========== IDENTITY REGISTRATION TESTS ==========

    function testRegisterIdentity() public {
        MockIdentity newIdentity = new MockIdentity();
        newIdentity.addClaim(1, trustedIssuer);

        vm.prank(user2);
        vault.registerIdentity(address(newIdentity));

        assertEq(vault.userIdentities(user2), address(newIdentity));
    }

    function testCannotRegisterInvalidIdentity() public {
        vm.prank(user2);
        vm.expectRevert(CrossChainVault.InvalidIdentityContract.selector);
        vault.registerIdentity(address(0));
    }

    function testCannotRegisterTwice() public {
        MockIdentity newIdentity = new MockIdentity();

        vm.prank(user2);
        vault.registerIdentity(address(newIdentity));

        vm.prank(user2);
        vm.expectRevert(CrossChainVault.AlreadyRegistered.selector);
        vault.registerIdentity(address(newIdentity));
    }

    function testUpdateIdentity() public {
        MockIdentity newIdentity = new MockIdentity();
        newIdentity.addClaim(1, trustedIssuer);

        vm.prank(user1);
        vault.updateIdentity(address(newIdentity));

        assertEq(vault.userIdentities(user1), address(newIdentity));
    }

    function testRemoveIdentity() public {
        vm.prank(user1);
        vault.removeIdentity();

        assertEq(vault.userIdentities(user1), address(0));
    }

    // ========== KYC VERIFICATION TESTS ==========

    function testIsKYCVerified() public {
        // Enable whitelist mode to test actual KYC verification
        vault.setComplianceMode(CrossChainVault.ComplianceMode.WHITELIST);

        // user1 has identity with KYC claim from trusted issuer
        assertTrue(vault.isKYCVerified(user1));

        // user2 has no identity - should be false in WHITELIST mode
        assertFalse(vault.isKYCVerified(user2));
    }

    function testKYCRequiresTrustedIssuer() public {
        // Enable whitelist mode to test actual KYC verification
        vault.setComplianceMode(CrossChainVault.ComplianceMode.WHITELIST);

        // Create identity with claim from untrusted issuer
        MockIdentity untrustedIdentity = new MockIdentity();
        address untrustedIssuer = address(0x999);
        untrustedIdentity.addClaim(1, untrustedIssuer);

        vm.prank(user2);
        vault.registerIdentity(address(untrustedIdentity));

        // Should not be verified (issuer not trusted)
        assertFalse(vault.isKYCVerified(user2));
    }

    function testGetKYCStatus() public view {
        // user1 has complete KYC
        (
            bool hasIdentity,
            bool isVerified,
            uint256[] memory missingClaims
        ) = vault.getKYCStatus(user1);
        assertTrue(hasIdentity);
        assertTrue(isVerified);
        assertEq(missingClaims.length, 0);

        // user2 has no identity
        (hasIdentity, isVerified, missingClaims) = vault.getKYCStatus(user2);
        assertFalse(hasIdentity);
        assertFalse(isVerified);
        assertEq(missingClaims.length, 1); // Missing KYC_VERIFIED
    }

    // ========== TRUSTED ISSUER TESTS ==========

    function testAddTrustedIssuer() public {
        address newIssuer = address(0x200);
        vault.addTrustedIssuer(newIssuer);
        assertTrue(vault.trustedIssuers(newIssuer));
    }

    function testRemoveTrustedIssuer() public {
        // Enable whitelist mode to test actual KYC verification
        vault.setComplianceMode(CrossChainVault.ComplianceMode.WHITELIST);

        vault.removeTrustedIssuer(trustedIssuer);
        assertFalse(vault.trustedIssuers(trustedIssuer));

        // user1's KYC should now be invalid (no trusted issuer)
        assertFalse(vault.isKYCVerified(user1));
    }

    function testGetTrustedIssuers() public view {
        address[] memory issuers = vault.getTrustedIssuers();
        assertEq(issuers.length, 1);
        assertEq(issuers[0], trustedIssuer);
    }

    // ========== REQUIRED CLAIMS TESTS ==========

    function testAddRequiredClaim() public {
        // Add AML_CLEARED requirement
        vault.addRequiredClaim(2);

        uint256[] memory required = vault.getRequiredClaims();
        assertEq(required.length, 2);
        assertEq(required[0], 1); // KYC_VERIFIED
        assertEq(required[1], 2); // AML_CLEARED
    }

    function testRemoveRequiredClaim() public {
        // First add another claim
        vault.addRequiredClaim(2);

        // Remove it
        vault.removeRequiredClaim(2);

        uint256[] memory required = vault.getRequiredClaims();
        assertEq(required.length, 1);
        assertEq(required[0], 1); // Only KYC_VERIFIED remains
    }

    function testUserFailsWithMissingRequiredClaim() public {
        // Enable whitelist mode
        vault.setComplianceMode(CrossChainVault.ComplianceMode.WHITELIST);

        // Add AML_CLEARED requirement
        vault.addRequiredClaim(2);

        // user1 only has KYC_VERIFIED, not AML_CLEARED
        vm.prank(user1);
        vm.expectRevert(CrossChainVault.KYCRequired.selector);
        vault.deposit{value: 1 ether}();
    }

    // ========== WITHDRAWAL ACCESS TESTS ==========

    function testCanWithdrawWithoutKYC() public {
        // First deposit in permissionless mode
        vm.prank(user2);
        vault.deposit{value: 1 ether}();

        // Enable whitelist mode
        vault.setComplianceMode(CrossChainVault.ComplianceMode.WHITELIST);

        // Should still be able to withdraw (exit positions)
        vm.prank(user2);
        vault.withdraw(0.5 ether);

        (uint256 collateral, , , , , ) = vault.positions(user2);
        assertEq(collateral, 0.5 ether);
    }

    function testCanRepayWithoutKYC() public {
        // First deposit liquidity to the vault by having a liquidity provider deposit
        address liquidityProvider = address(0x999);
        usdc.mint(liquidityProvider, 100_000 * 1e18);
        vm.startPrank(liquidityProvider);
        usdc.approve(address(vault), type(uint256).max);
        vault.depositToken(address(usdc), 100_000 * 1e18);
        vm.stopPrank();

        // user1 deposits ETH collateral and borrows USDC in permissionless mode
        vm.prank(user1);
        vault.deposit{value: 10 ether}();

        vm.prank(user1);
        usdc.approve(address(vault), type(uint256).max);

        // Borrow a small amount relative to collateral (10 ETH = $20000, borrow $1000)
        vm.prank(user1);
        vault.borrow(address(usdc), 1000 * 1e18);

        // Enable whitelist mode
        vault.setComplianceMode(CrossChainVault.ComplianceMode.WHITELIST);

        // Remove user1's identity to simulate expired KYC
        vm.prank(user1);
        vault.removeIdentity();

        // Should still be able to repay
        vm.prank(user1);
        vault.repay(address(usdc), 500 * 1e18);
    }

    // ========== ADMIN ONLY TESTS ==========

    function testOnlyOwnerCanSetComplianceMode() public {
        vm.prank(user1);
        vm.expectRevert();
        vault.setComplianceMode(CrossChainVault.ComplianceMode.WHITELIST);
    }

    function testOnlyOwnerCanAddTrustedIssuer() public {
        vm.prank(user1);
        vm.expectRevert();
        vault.addTrustedIssuer(address(0x999));
    }

    function testOnlyOwnerCanRemoveTrustedIssuer() public {
        vm.prank(user1);
        vm.expectRevert();
        vault.removeTrustedIssuer(trustedIssuer);
    }

    // Receive ETH
    receive() external payable {}
}
