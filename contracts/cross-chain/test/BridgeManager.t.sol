// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.30;

import {Test, console2} from "forge-std/Test.sol";
import {BridgeManager} from "../src/BridgeManager.sol";
import {IBridgeAdapter} from "../src/interfaces/IBridgeAdapter.sol";
import {AxelarAdapter} from "../src/adapters/AxelarAdapter.sol";
import {CCIPAdapter} from "../src/adapters/CCIPAdapter.sol";
import {MockAxelarGateway} from "./mocks/MockAxelarGateway.sol";
import {MockAxelarGasService} from "./mocks/MockAxelarGasService.sol";
import {MockCCIPRouter} from "./mocks/MockCCIPRouter.sol";

contract BridgeManagerTest is Test {
    BridgeManager public bridgeManager;
    MockAxelarGateway public mockGateway;
    MockAxelarGasService public mockGasService;
    MockCCIPRouter public mockCCIPRouter;
    AxelarAdapter public axelarAdapter;
    CCIPAdapter public ccipAdapter;

    string[] public axelarChains;
    uint64[] public ccipSelectors;
    string[] public ccipChainNames;

    function setUp() public {
        // Deploy mocks
        mockGateway = new MockAxelarGateway();
        mockGasService = new MockAxelarGasService();
        mockCCIPRouter = new MockCCIPRouter();

        // Setup Axelar chains
        axelarChains = new string[](3);
        axelarChains[0] = "ethereum";
        axelarChains[1] = "polygon";
        axelarChains[2] = "arbitrum";

        // Setup CCIP chains
        ccipSelectors = new uint64[](3);
        ccipChainNames = new string[](3);
        ccipSelectors[0] = 16015286601757825753; // Ethereum Sepolia
        ccipSelectors[1] = 12532609583862916517; // Polygon Mumbai
        ccipSelectors[2] = 3478487238524512106; // Arbitrum Sepolia
        ccipChainNames[0] = "ethereum";
        ccipChainNames[1] = "polygon";
        ccipChainNames[2] = "arbitrum";

        // Deploy adapters
        axelarAdapter = new AxelarAdapter(
            address(mockGateway),
            address(mockGasService),
            axelarChains
        );

        ccipAdapter = new CCIPAdapter(
            address(mockCCIPRouter),
            ccipSelectors,
            ccipChainNames
        );

        // Deploy BridgeManager
        bridgeManager = new BridgeManager();
    }

    function testRegisterAdapter() public {
        bridgeManager.registerAdapter(axelarAdapter);

        string[] memory protocols = bridgeManager.getRegisteredProtocols();
        assertEq(protocols.length, 1);
        assertEq(protocols[0], "axelar");
    }

    function testRegisterMultipleAdapters() public {
        bridgeManager.registerAdapter(axelarAdapter);
        bridgeManager.registerAdapter(ccipAdapter);

        string[] memory protocols = bridgeManager.getRegisteredProtocols();
        assertEq(protocols.length, 2);
    }

    function testSetPreferredProtocol() public {
        bridgeManager.registerAdapter(axelarAdapter);
        bridgeManager.setPreferredProtocol("polygon", "axelar");

        // Should not revert
        assertTrue(true);
    }

    function testSendMessageWithPreferredProtocol() public {
        bridgeManager.registerAdapter(axelarAdapter);
        bridgeManager.setPreferredProtocol("polygon", "axelar");

        bytes memory payload = abi.encode("test", "data");
        bytes32 messageId = bridgeManager.sendMessage{value: 0.001 ether}(
            "polygon",
            "0x1234567890123456789012345678901234567890",
            payload,
            address(0)
        );

        assertTrue(messageId != bytes32(0));
    }

    function testSendMessageAutoSelectAdapter() public {
        bridgeManager.registerAdapter(axelarAdapter);
        // No preferred protocol set, should auto-select

        bytes memory payload = abi.encode("test", "data");
        bytes32 messageId = bridgeManager.sendMessage{value: 0.001 ether}(
            "ethereum",
            "0x1234567890123456789012345678901234567890",
            payload,
            address(0)
        );

        assertTrue(messageId != bytes32(0));
    }

    function testEstimateGas() public {
        bridgeManager.registerAdapter(axelarAdapter);

        bytes memory payload = abi.encode("test", "data");
        (uint256 estimatedGas, string memory protocol) = bridgeManager.estimateGas(
            "polygon",
            payload
        );

        assertGt(estimatedGas, 0);
        assertEq(protocol, "");
    }

    function testIsChainSupported() public {
        bridgeManager.registerAdapter(axelarAdapter);

        assertTrue(bridgeManager.isChainSupported("ethereum"));
        assertTrue(bridgeManager.isChainSupported("polygon"));
        assertFalse(bridgeManager.isChainSupported("unsupported"));
    }

    function testFailsWhenNoAdapterForChain() public {
        bridgeManager.registerAdapter(axelarAdapter);

        bytes memory payload = abi.encode("test", "data");
        vm.expectRevert();
        bridgeManager.sendMessage{value: 0.001 ether}(
            "unsupported-chain",
            "0x1234567890123456789012345678901234567890",
            payload,
            address(0)
        );
    }

    function testPreferCCIPOverAxelar() public {
        bridgeManager.registerAdapter(axelarAdapter);
        bridgeManager.registerAdapter(ccipAdapter);
        bridgeManager.setPreferredProtocol("polygon", "ccip");

        bytes memory payload = abi.encode("test", "data");
        bytes32 messageId = bridgeManager.sendMessage{value: 0.001 ether}(
            "polygon",
            "0x1234567890123456789012345678901234567890",
            payload,
            address(0)
        );

        assertTrue(messageId != bytes32(0));
    }
}
