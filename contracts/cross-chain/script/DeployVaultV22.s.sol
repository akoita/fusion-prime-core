// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.30;

import {Script} from "forge-std/Script.sol";
import {console2} from "forge-std/console2.sol";
import {CrossChainVaultV22} from "../src/CrossChainVaultV22.sol";

contract DeployVaultV22 is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);

        console2.log("Deployer:", deployer);
        console2.log("Chain ID:", block.chainid);

        // Get MessageBridge address from environment
        address messageBridge;
        if (block.chainid == 11155111) {
            // Sepolia
            messageBridge = vm.envAddress("SEPOLIA_MESSAGE_BRIDGE");
            console2.log("Sepolia MessageBridge:", messageBridge);
        } else if (block.chainid == 80002) {
            // Amoy
            messageBridge = vm.envAddress("AMOY_MESSAGE_BRIDGE");
            console2.log("Amoy MessageBridge:", messageBridge);
        } else {
            revert("Unsupported chain");
        }

        // Supported chains configuration
        string[] memory supportedChains = new string[](2);
        supportedChains[0] = "ethereum";
        supportedChains[1] = "polygon";

        uint64[] memory chainIds = new uint64[](2);
        chainIds[0] = 11155111; // Sepolia
        chainIds[1] = 80002;     // Amoy

        vm.startBroadcast(deployerPrivateKey);

        console2.log("Deploying CrossChainVaultV22...");
        CrossChainVaultV22 vault = new CrossChainVaultV22(
            messageBridge,
            supportedChains,
            chainIds
        );

        console2.log("CrossChainVaultV22 deployed at:", address(vault));
        console2.log("This chain name:", vault.thisChainName());
        console2.log("This chain ID:", vault.thisChainId());

        vm.stopBroadcast();
    }
}
