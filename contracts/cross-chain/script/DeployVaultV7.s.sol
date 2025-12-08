// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import {Script} from "forge-std/Script.sol";
import {console2} from "forge-std/console2.sol";
import {CrossChainVault} from "../src/CrossChainVault.sol";
import {VaultFactory} from "../src/VaultFactory.sol";
import {BridgeManager} from "../src/BridgeManager.sol";

contract DeployVaultV7 is Script {
    // Existing contract addresses
    address constant SEPOLIA_BRIDGE_MANAGER = 0x05BB4ef5D0759ddf9D39C9b8e6392b11CA175279;
    address constant AMOY_BRIDGE_MANAGER = 0x05BB4ef5D0759ddf9D39C9b8e6392b11CA175279;

    // V11 factories with updated CrossChainVault bytecode
    address constant SEPOLIA_VAULT_FACTORY = 0x26221AE1777229c657D0D6B592AD0f4297Ae6B55;
    address constant AMOY_VAULT_FACTORY = 0xcCA6Be7D705C9376d111d75010782c792f45cA94;

    // CCIP Router addresses (testnet)
    // Note: These are the actual addresses that call ccipReceive, not just the sending routers
    address constant SEPOLIA_CCIP_ROUTER = 0x0BF3dE8c5D3e8A2B34D2BEeB17ABfCeBaf363A59;
    address constant AMOY_CCIP_ROUTER = 0x7Ad494C173f5845c6B4028a06cDcC6d3108bc960; // CCIP Router/OffRamp that delivers messages

    // Dummy Axelar (not used for CCIP)
    address constant DUMMY_AXELAR_GATEWAY = address(0);

    // V13 vault salt (improved error messages for debugging)
    bytes32 constant VAULT_V13_SALT = keccak256("FusionPrime.CrossChainVault.ccip.v13");

    function run() external {
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        vm.startBroadcast(deployerPrivateKey);

        console2.log("====================================");
        console2.log("CCIP Vault V13 - Improved Error Messages");
        console2.log("====================================");
        console2.log("Chain ID:", block.chainid);
        console2.log("");

        // Get addresses for this chain
        address bridgeManager;
        address vaultFactory;
        address ccipRouter;

        if (block.chainid == 11155111) { // Sepolia
            bridgeManager = SEPOLIA_BRIDGE_MANAGER;
            vaultFactory = SEPOLIA_VAULT_FACTORY;
            ccipRouter = SEPOLIA_CCIP_ROUTER;
        } else if (block.chainid == 80002) { // Amoy
            bridgeManager = AMOY_BRIDGE_MANAGER;
            vaultFactory = AMOY_VAULT_FACTORY;
            ccipRouter = AMOY_CCIP_ROUTER;
        } else {
            revert("Unsupported chain");
        }

        // Supported chains - pass ALL chains including this one
        string[] memory supportedChains = new string[](2);
        if (block.chainid == 11155111) {
            // Sepolia
            supportedChains[0] = "ethereum";
            supportedChains[1] = "polygon";
        } else {
            // Amoy
            supportedChains[0] = "polygon";
            supportedChains[1] = "ethereum";
        }

        console2.log(">>> Deploying CrossChainVault V13...");
        VaultFactory factory = VaultFactory(vaultFactory);
        address vault = factory.deployVault(
            bridgeManager,
            DUMMY_AXELAR_GATEWAY,
            ccipRouter,
            supportedChains,
            VAULT_V13_SALT
        );
        console2.log("CrossChainVault V13:", vault);

        vm.stopBroadcast();

        console2.log("");
        console2.log("====================================");
        console2.log("Deployment Complete!");
        console2.log("====================================");
        console2.log("Vault V13:", vault);
        console2.log("CCIP Router (for receiving):", ccipRouter);
        console2.log("");
        console2.log("IMPORTANT: Configure trustedVaults mapping!");
        console2.log("Run setTrustedVault on both chains to link the vaults.");
    }
}
