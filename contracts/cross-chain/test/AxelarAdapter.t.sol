// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.30;

import {Test, console2} from "forge-std/Test.sol";
import {AxelarAdapter} from "../src/adapters/AxelarAdapter.sol";
import {MockAxelarGateway} from "./mocks/MockAxelarGateway.sol";
import {MockAxelarGasService} from "./mocks/MockAxelarGasService.sol";

contract AxelarAdapterTest is Test {
    AxelarAdapter public adapter;
    MockAxelarGateway public mockGateway;
    MockAxelarGasService public mockGasService;
    string[] public supportedChains;

    function setUp() public {
        mockGateway = new MockAxelarGateway();
        mockGasService = new MockAxelarGasService();

        supportedChains = new string[](3);
        supportedChains[0] = "ethereum";
        supportedChains[1] = "polygon";
        supportedChains[2] = "arbitrum";

        adapter = new AxelarAdapter(
            address(mockGateway),
            address(mockGasService),
            supportedChains
        );
    }

    function testGetProtocolName() public view {
        string memory name = adapter.getProtocolName();
        assertEq(name, "axelar");
    }

    function testIsChainSupported() public view {
        assertTrue(adapter.isChainSupported("ethereum"));
        assertTrue(adapter.isChainSupported("polygon"));
        assertFalse(adapter.isChainSupported("unsupported"));
    }

    function testGetSupportedChains() public view {
        string[] memory chains = adapter.getSupportedChains();
        assertEq(chains.length, 3);
        assertEq(chains[0], "ethereum");
        assertEq(chains[1], "polygon");
        assertEq(chains[2], "arbitrum");
    }

    function testSendMessage() public payable {
        bytes memory payload = abi.encode("test", "data");
        bytes32 messageId = adapter.sendMessage{value: 0.001 ether}(
            "polygon",
            "0x1234567890123456789012345678901234567890",
            payload,
            address(0)
        );

        assertTrue(messageId != bytes32(0));
    }

    function testEstimateGas() public view {
        bytes memory payload = abi.encode("test", "data");
        uint256 estimatedGas = adapter.estimateGas("polygon", payload);

        assertGt(estimatedGas, 0);
    }

    function testFailsOnUnsupportedChain() public {
        bytes memory payload = abi.encode("test", "data");
        vm.expectRevert();
        adapter.sendMessage{value: 0.001 ether}(
            "unsupported",
            "0x1234567890123456789012345678901234567890",
            payload,
            address(0)
        );
    }
}
