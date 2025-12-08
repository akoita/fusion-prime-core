// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import {Script} from "forge-std/Script.sol";
import {console2} from "forge-std/console2.sol";
import {CCIPAdapter} from "../src/adapters/CCIPAdapter.sol";
import {BridgeManager} from "../src/BridgeManager.sol";

contract DeployFixedCCIPAdapter is Script {
    // Existing contract addresses
    address constant SEPOLIA_BRIDGE_MANAGER = 0x05BB4ef5D0759ddf9D39C9b8e6392b11CA175279;
    address constant AMOY_BRIDGE_MANAGER = 0x05BB4ef5D0759ddf9D39C9b8e6392b11CA175279;

    // CCIP Router addresses
    address constant SEPOLIA_CCIP_ROUTER = 0x0BF3dE8c5D3e8A2B34D2BEeB17ABfCeBaf363A59;
    address constant AMOY_CCIP_ROUTER = 0x9C32fCB86BF0f4a1A8921a9Fe46de3198bb884B2;

    function run() external {
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        vm.startBroadcast(deployerPrivateKey);

        console2.log("====================================");
        console2.log("Deploying Fixed CCIPAdapter with Gas Limit");
        console2.log("====================================");
        console2.log("Chain ID:", block.chainid);

        address ccipRouter;
        address bridgeManager;

        if (block.chainid == 11155111) {
            ccipRouter = SEPOLIA_CCIP_ROUTER;
            bridgeManager = SEPOLIA_BRIDGE_MANAGER;
        } else if (block.chainid == 80002) {
            ccipRouter = AMOY_CCIP_ROUTER;
            bridgeManager = AMOY_BRIDGE_MANAGER;
        } else {
            revert("Unsupported chain");
        }

        // Deploy new CCIPAdapter with gas limit fix
        uint64[] memory chainSelectors = new uint64[](1);
        string[] memory chainNames = new string[](1);

        if (block.chainid == 11155111) {
            // Sepolia -> Amoy
            chainSelectors[0] = 16281711391670634445;
            chainNames[0] = "polygon";
        } else {
            // Amoy -> Sepolia
            chainSelectors[0] = 16015286601757825753;
            chainNames[0] = "ethereum";
        }

        CCIPAdapter newAdapter = new CCIPAdapter(ccipRouter, chainSelectors, chainNames);
        console2.log("New CCIPAdapter:", address(newAdapter));

        console2.log("");
        console2.log("NOTE: BridgeManager already has CCIP adapter registered.");
        console2.log("To use this new adapter, you need to:");
        console2.log("1. Unregister old adapter, OR");
        console2.log("2. Call vault.sendMessage() with this adapter directly");

        vm.stopBroadcast();

        console2.log("");
        console2.log("====================================");
        console2.log("Deployment Complete!");
        console2.log("====================================");
        console2.log("Fixed CCIPAdapter:", address(newAdapter));
        console2.log("Gas Limit: 200,000 (was using default ~100k)");
    }
}
