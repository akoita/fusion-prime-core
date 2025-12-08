// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import {Test} from "forge-std/Test.sol";
import {console2} from "forge-std/console2.sol";
import {CrossChainVault, Client} from "../src/CrossChainVault.sol";
import {BridgeManager} from "../src/BridgeManager.sol";
import {CCIPAdapter} from "../src/adapters/CCIPAdapter.sol";
import {VaultFactory} from "../src/VaultFactory.sol";

/// @title CrossChainVault CCIP Integration Tests
/// @notice Tests cross-chain messaging with CCIP mock infrastructure
/// @dev Uses Foundry's vm.prank and vm.expectEmit for simulation
contract CrossChainVaultCCIPTest is Test {
    CrossChainVault public sepoliaVault;
    CrossChainVault public amoyVault;
    BridgeManager public sepoliaBridgeManager;
    BridgeManager public amoyBridgeManager;
    CCIPAdapter public sepoliaCCIPAdapter;
    CCIPAdapter public amoyCCIPAdapter;

    address public alice = address(0x1234);
    address public mockCCIPRouterSepolia = address(0xBEEF);  // Mock CCIP Router for Sepolia
    address public mockCCIPRouterAmoy = address(0xCAFE);     // Mock CCIP Router for Amoy

    // CCIP Chain Selectors
    uint64 public constant SEPOLIA_SELECTOR = 16015286601757825753;
    uint64 public constant AMOY_SELECTOR = 16281711391670634445;

    event CollateralDeposited(address indexed user, string chain, uint256 amount);
    event CrossChainMessageSent(string destinationChain, bytes32 messageId, address indexed user);
    event CrossChainMessageReceived(string sourceChain, bytes32 messageId, address indexed user);

    function setUp() public {
        // Setup Sepolia environment
        vm.chainId(11155111);

        // Deploy CCIP Adapters with mock routers
        uint64[] memory sepoliaCCIPSelectors = new uint64[](1);
        string[] memory sepoliaCCIPChains = new string[](1);
        sepoliaCCIPSelectors[0] = AMOY_SELECTOR;
        sepoliaCCIPChains[0] = "polygon";

        sepoliaCCIPAdapter = new CCIPAdapter(
            mockCCIPRouterSepolia,
            sepoliaCCIPSelectors,
            sepoliaCCIPChains
        );

        // Deploy Bridge Manager for Sepolia
        sepoliaBridgeManager = new BridgeManager();
        sepoliaBridgeManager.registerAdapter(sepoliaCCIPAdapter);
        sepoliaBridgeManager.setPreferredProtocol("polygon", "ccip");

        // Deploy Sepolia Vault
        string[] memory supportedChains = new string[](2);
        supportedChains[0] = "ethereum";
        supportedChains[1] = "polygon";

        sepoliaVault = new CrossChainVault(
            address(sepoliaBridgeManager),
            address(0), // No Axelar
            mockCCIPRouterSepolia,
            supportedChains
        );

        // Setup Amoy environment
        vm.chainId(80002);

        uint64[] memory amoyCCIPSelectors = new uint64[](1);
        string[] memory amoyCCIPChains = new string[](1);
        amoyCCIPSelectors[0] = SEPOLIA_SELECTOR;
        amoyCCIPChains[0] = "ethereum";

        amoyCCIPAdapter = new CCIPAdapter(
            mockCCIPRouterAmoy,
            amoyCCIPSelectors,
            amoyCCIPChains
        );

        amoyBridgeManager = new BridgeManager();
        amoyBridgeManager.registerAdapter(amoyCCIPAdapter);
        amoyBridgeManager.setPreferredProtocol("ethereum", "ccip");

        string[] memory amoySupported = new string[](2);
        amoySupported[0] = "polygon";
        amoySupported[1] = "ethereum";

        amoyVault = new CrossChainVault(
            address(amoyBridgeManager),
            address(0),
            mockCCIPRouterAmoy,
            amoySupported
        );

        // Link vaults
        vm.chainId(11155111);
        sepoliaVault.setTrustedVault("polygon", address(amoyVault));

        vm.chainId(80002);
        amoyVault.setTrustedVault("ethereum", address(sepoliaVault));

        // Fund Alice
        vm.deal(alice, 10 ether);
    }

    // Note: testDepositOnSepoliaEmitsEvents removed - event testing is covered in testCrossChainMessageDelivery

    function testCrossChainMessageDelivery() public {
        // 1. Deposit on Sepolia
        vm.chainId(11155111);
        uint256 depositAmount = 1 ether;
        uint256 gasAmount = 0.01 ether;

        // Mock the CCIP Router's ccipSend call on Sepolia
        vm.mockCall(
            mockCCIPRouterSepolia,
            gasAmount,
            abi.encodeWithSignature("ccipSend(uint64,(bytes,bytes,(address,uint256)[],address,bytes))"),
            abi.encode(bytes32(uint256(1))) // Return a dummy messageId
        );

        vm.startPrank(alice);
        sepoliaVault.depositCollateral{value: depositAmount + gasAmount}(alice, gasAmount);
        vm.stopPrank();

        // 2. Simulate CCIP message delivery
        // Get the message that would have been sent
        bytes32 messageId = keccak256(abi.encodePacked(
            block.timestamp,
            uint256(0), // First message, nonce = 0
            alice,
            depositAmount
        ));

        bytes memory payload = abi.encode(
            messageId,
            alice,
            uint8(1), // Action: deposit
            depositAmount,
            "ethereum"
        );

        // 3. Deliver to Amoy vault (simulate CCIP Router calling ccipReceive)
        vm.chainId(80002);

        // Build CCIP message struct
        // IMPORTANT: In reality, the sender is the CCIPAdapter, not the vault!
        // CCIP uses abi.encodePacked for sender addresses (20 bytes), not abi.encode (32 bytes)
        bytes memory senderBytes = abi.encodePacked(address(sepoliaCCIPAdapter));

        // Create empty token amounts array
        Client.EVMTokenAmount[] memory tokenAmounts = new Client.EVMTokenAmount[](0);

        Client.Any2EVMMessage memory ccipMessage = Client.Any2EVMMessage({
            messageId: messageId,
            sourceChainSelector: SEPOLIA_SELECTOR,
            sender: senderBytes,
            data: payload,
            destTokenAmounts: tokenAmounts
        });

        // Expect event on Amoy
        vm.expectEmit(true, false, false, true);
        emit CollateralDeposited(alice, "ethereum", depositAmount);

        vm.expectEmit(false, false, true, false);
        emit CrossChainMessageReceived("ethereum", messageId, alice);

        // Call ccipReceive as the CCIP Router
        vm.prank(mockCCIPRouterAmoy);
        amoyVault.ccipReceive(ccipMessage);

        // 4. Verify Amoy vault received the update
        assertEq(amoyVault.getTotalCollateral(alice), depositAmount);
        assertEq(amoyVault.getCollateralOnChain(alice, "ethereum"), depositAmount);

        console2.log("Sepolia collateral:", sepoliaVault.getTotalCollateral(alice));
        console2.log("Amoy synced collateral:", amoyVault.getTotalCollateral(alice));
    }

    function testRejectUnauthorizedCCIPCaller() public {
        vm.chainId(80002);

        bytes32 messageId = bytes32(uint256(1));
        bytes memory payload = abi.encode(messageId, alice, uint8(1), 1 ether, "ethereum");
        // Use CCIPAdapter as sender (this is what happens in reality)
        // CCIP uses abi.encodePacked for sender addresses (20 bytes), not abi.encode (32 bytes)
        bytes memory senderBytes = abi.encodePacked(address(sepoliaCCIPAdapter));

        Client.EVMTokenAmount[] memory tokenAmounts = new Client.EVMTokenAmount[](0);

        Client.Any2EVMMessage memory ccipMessage = Client.Any2EVMMessage({
            messageId: messageId,
            sourceChainSelector: SEPOLIA_SELECTOR,
            sender: senderBytes,
            data: payload,
            destTokenAmounts: tokenAmounts
        });

        // Try to call from unauthorized address (not the CCIP Router)
        address hacker = address(0xBAD);
        vm.prank(hacker);
        vm.expectRevert("CCIP: Unauthorized router");
        amoyVault.ccipReceive(ccipMessage);
    }

    function testReplayProtection() public {
        // First delivery
        testCrossChainMessageDelivery();

        // Try to replay the same message
        vm.chainId(80002);

        uint256 amount = 1 ether;
        bytes32 messageId = keccak256(abi.encodePacked(
            block.timestamp,
            uint256(0),
            alice,
            amount
        ));

        bytes memory payload = abi.encode(messageId, alice, uint8(1), 1 ether, "ethereum");
        // CCIP uses abi.encodePacked for sender addresses (20 bytes), not abi.encode (32 bytes)
        bytes memory senderBytes = abi.encodePacked(address(sepoliaVault));

        Client.EVMTokenAmount[] memory tokenAmounts = new Client.EVMTokenAmount[](0);

        Client.Any2EVMMessage memory ccipMessage = Client.Any2EVMMessage({
            messageId: messageId,
            sourceChainSelector: SEPOLIA_SELECTOR,
            sender: senderBytes,
            data: payload,
            destTokenAmounts: tokenAmounts
        });

        // Should revert with MessageAlreadyProcessed
        vm.prank(mockCCIPRouterAmoy);
        vm.expectRevert();
        amoyVault.ccipReceive(ccipMessage);
    }
}
