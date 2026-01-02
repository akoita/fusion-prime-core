// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.30;

import {Test, console2} from "forge-std/Test.sol";
import {CCIPAdapter} from "adapters/CCIPAdapter.sol";
import {MockCCIPRouter} from "./mocks/MockCCIPRouter.sol";

contract CCIPAdapterTest is Test {
    CCIPAdapter public adapter;
    MockCCIPRouter public mockRouter;
    uint64[] public chainSelectors;
    string[] public chainNames;

    function setUp() public {
        mockRouter = new MockCCIPRouter();

        chainSelectors = new uint64[](3);
        chainNames = new string[](3);
        chainSelectors[0] = 16015286601757825753; // Ethereum Sepolia
        chainSelectors[1] = 12532609583862916517; // Polygon Mumbai
        chainSelectors[2] = 3478487238524512106; // Arbitrum Sepolia
        chainNames[0] = "ethereum";
        chainNames[1] = "polygon";
        chainNames[2] = "arbitrum";

        adapter = new CCIPAdapter(
            address(mockRouter),
            chainSelectors,
            chainNames
        );
    }

    function testGetProtocolName() public view {
        string memory name = adapter.getProtocolName();
        assertEq(name, "ccip");
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

    function test_RevertWhen_UnsupportedChain() public {
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
