// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.30;

import "forge-std/Script.sol";
import "../src/CrossChainVaultV23.sol";

contract DeployVaultV23 is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);

        console2.log("Deploying CrossChainVaultV23 from:", deployer);
        console2.log("Chain ID:", block.chainid);

        // Get MessageBridge address based on chain
        address messageBridge;
        if (block.chainid == 11155111) {
            messageBridge = vm.envAddress("SEPOLIA_MESSAGE_BRIDGE");
            console2.log("Sepolia MessageBridge:", messageBridge);
        } else if (block.chainid == 80002) {
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

        CrossChainVaultV23 vault = new CrossChainVaultV23(
            messageBridge,
            supportedChains,
            chainIds
        );

        console2.log("========================================");
        console2.log("CrossChainVaultV23 deployed at:", address(vault));
        console2.log("========================================");

        vm.stopBroadcast();
    }
}
