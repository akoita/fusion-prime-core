// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import {Script} from "forge-std/Script.sol";
import {console2} from "forge-std/console2.sol";
import {MessageBridgeAdapter} from "../src/adapters/MessageBridgeAdapter.sol";

/**
 * @title DeployMessageBridgeAdapter
 * @notice Deploys MessageBridgeAdapter for cross-chain vault integration
 *
 * Usage:
 *   # Deploy on Sepolia
 *   forge script script/DeployMessageBridgeAdapter.s.sol:DeployMessageBridgeAdapter \
 *     --rpc-url $SEPOLIA_RPC_URL --broadcast -vvvv
 *
 *   # Deploy on Amoy
 *   forge script script/DeployMessageBridgeAdapter.s.sol:DeployMessageBridgeAdapter \
 *     --rpc-url $AMOY_RPC_URL --broadcast -vvvv
 *
 * Environment Variables:
 *   DEPLOYER_PRIVATE_KEY         - Deployer private key
 *   SEPOLIA_MESSAGE_BRIDGE       - MessageBridge address on Sepolia
 *   AMOY_MESSAGE_BRIDGE          - MessageBridge address on Amoy
 */
contract DeployMessageBridgeAdapter is Script {
    // Chain IDs
    uint64 constant SEPOLIA_CHAIN_ID = 11155111;
    uint64 constant AMOY_CHAIN_ID = 80002;

    // MessageBridge addresses (from DEPLOYMENT_ADDRESSES.md)
    address constant SEPOLIA_MESSAGE_BRIDGE = 0xd04ef4fb6f49850c9Bf3D48666ec5Af10b0EFa2C;
    address constant AMOY_MESSAGE_BRIDGE = 0x5e67D35a38E2BCBD76e56729A8AFC78Ef8A5bDB2;

    struct DeploymentResult {
        address adapter;
        address messageBridge;
        uint256 chainId;
        string chainName;
    }

    function run() external returns (DeploymentResult memory) {
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);

        console2.log("====================================");
        console2.log("MessageBridgeAdapter Deployment");
        console2.log("====================================");
        console2.log("Deployer:", deployer);
        console2.log("Chain ID:", block.chainid);
        console2.log("Balance:", deployer.balance);
        console2.log("");

        vm.startBroadcast(deployerPrivateKey);

        DeploymentResult memory result = deployAdapter();

        vm.stopBroadcast();

        logDeployment(result);

        return result;
    }

    function deployAdapter() internal returns (DeploymentResult memory result) {
        result.chainId = block.chainid;

        // Determine which MessageBridge to use
        address messageBridgeAddress;
        if (block.chainid == SEPOLIA_CHAIN_ID) {
            result.chainName = "sepolia";
            messageBridgeAddress = SEPOLIA_MESSAGE_BRIDGE;
        } else if (block.chainid == AMOY_CHAIN_ID) {
            result.chainName = "amoy";
            messageBridgeAddress = AMOY_MESSAGE_BRIDGE;
        } else {
            revert("Unsupported chain");
        }

        result.messageBridge = messageBridgeAddress;

        console2.log("Deploying MessageBridgeAdapter...");
        console2.log("MessageBridge:", messageBridgeAddress);

        // Configure supported chains
        string[] memory chainNames = new string[](2);
        chainNames[0] = "ethereum";  // Sepolia testnet
        chainNames[1] = "polygon";   // Amoy testnet

        uint64[] memory chainIds = new uint64[](2);
        chainIds[0] = SEPOLIA_CHAIN_ID;
        chainIds[1] = AMOY_CHAIN_ID;

        // Deploy adapter
        MessageBridgeAdapter adapter = new MessageBridgeAdapter(
            messageBridgeAddress,
            chainNames,
            chainIds
        );

        result.adapter = address(adapter);
        console2.log("MessageBridgeAdapter deployed at:", result.adapter);

        return result;
    }

    function logDeployment(DeploymentResult memory result) internal view {
        console2.log("\n====================================");
        console2.log("Deployment Summary");
        console2.log("====================================");
        console2.log("Chain:", result.chainName);
        console2.log("Chain ID:", result.chainId);
        console2.log("MessageBridge:", result.messageBridge);
        console2.log("MessageBridgeAdapter:", result.adapter);
        console2.log("====================================\n");

        console2.log("Add to .env:");
        if (result.chainId == SEPOLIA_CHAIN_ID) {
            console2.log("SEPOLIA_MESSAGE_BRIDGE_ADAPTER=", result.adapter);
        } else if (result.chainId == AMOY_CHAIN_ID) {
            console2.log("AMOY_MESSAGE_BRIDGE_ADAPTER=", result.adapter);
        }
    }
}
