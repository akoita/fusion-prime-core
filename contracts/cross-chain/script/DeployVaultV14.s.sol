// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import {Script} from "forge-std/Script.sol";
import {console2} from "forge-std/console2.sol";
import {CrossChainVault} from "../src/CrossChainVault.sol";
import {BridgeManager} from "../src/BridgeManager.sol";
import {CCIPAdapter} from "../src/adapters/CCIPAdapter.sol";
import {VaultFactory} from "../src/VaultFactory.sol";

/**
 * @title DeployVaultV14
 * @notice Deploy V14 with fixed CCIP adapter (200k gas limit)
 * @dev Deploys complete new setup: BridgeManager + CCIPAdapter + CrossChainVault
 */
contract DeployVaultV14 is Script {
    // CCIP Router addresses (testnet)
    address constant SEPOLIA_CCIP_ROUTER = 0x0BF3dE8c5D3e8A2B34D2BEeB17ABfCeBaf363A59;
    address constant AMOY_CCIP_ROUTER = 0x9C32fCB86BF0f4a1A8921a9Fe46de3198bb884B2;

    // CCIP Chain Selectors
    uint64 constant SEPOLIA_SELECTOR = 16015286601757825753;
    uint64 constant AMOY_SELECTOR = 16281711391670634445;

    function run() external {
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        vm.startBroadcast(deployerPrivateKey);

        console2.log("====================================");
        console2.log("Deploying V14 with Fixed CCIP Gas Limit");
        console2.log("====================================");
        console2.log("Chain ID:", block.chainid);

        address ccipRouter;
        uint64 destinationChainSelector;
        string memory destinationChainName;

        if (block.chainid == 11155111) {
            // Sepolia
            ccipRouter = SEPOLIA_CCIP_ROUTER;
            destinationChainSelector = AMOY_SELECTOR;
            destinationChainName = "polygon";
            console2.log("Deploying on Sepolia");
        } else if (block.chainid == 80002) {
            // Polygon Amoy
            ccipRouter = AMOY_CCIP_ROUTER;
            destinationChainSelector = SEPOLIA_SELECTOR;
            destinationChainName = "ethereum";
            console2.log("Deploying on Polygon Amoy");
        } else {
            revert("Unsupported chain");
        }

        // 1. Deploy BridgeManager
        console2.log("\n--- Step 1: Deploy BridgeManager ---");
        BridgeManager bridgeManager = new BridgeManager();
        console2.log("BridgeManager deployed:", address(bridgeManager));

        // 2. Deploy CCIPAdapter with fixed gas limit (200k)
        console2.log("\n--- Step 2: Deploy Fixed CCIPAdapter ---");
        uint64[] memory chainSelectors = new uint64[](1);
        string[] memory chainNames = new string[](1);
        chainSelectors[0] = destinationChainSelector;
        chainNames[0] = destinationChainName;

        CCIPAdapter ccipAdapter = new CCIPAdapter(ccipRouter, chainSelectors, chainNames);
        console2.log("CCIPAdapter deployed:", address(ccipAdapter));
        console2.log("Gas limit: 200,000 (fixed in adapter code)");

        // 3. Register CCIPAdapter with BridgeManager
        console2.log("\n--- Step 3: Register Adapter ---");
        bridgeManager.registerAdapter(ccipAdapter);
        console2.log("CCIPAdapter registered with BridgeManager");

        // 4. Deploy CrossChainVault via VaultFactory for deterministic address
        console2.log("\n--- Step 4: Deploy CrossChainVault ---");

        // Create supported chains array
        string[] memory supportedChains = new string[](1);
        supportedChains[0] = destinationChainName;

        // Deploy VaultFactory
        VaultFactory factory = new VaultFactory();
        console2.log("VaultFactory deployed:", address(factory));

        // Calculate vault address using V14 salt
        bytes32 salt = keccak256("CrossChainVault-V14");
        address predictedVault = factory.computeVaultAddress(
            address(bridgeManager),
            address(0), // No Axelar, using CCIP only
            ccipRouter,
            supportedChains,
            salt
        );
        console2.log("Predicted vault address:", predictedVault);

        // Deploy vault via factory
        address vault = factory.deployVault(
            address(bridgeManager),
            address(0), // No Axelar, using CCIP only
            ccipRouter,
            supportedChains,
            salt
        );
        console2.log("CrossChainVault deployed:", vault);
        require(vault == predictedVault, "Vault address mismatch");

        vm.stopBroadcast();

        console2.log("\n====================================");
        console2.log("V14 Deployment Complete!");
        console2.log("====================================");
        console2.log("BridgeManager:", address(bridgeManager));
        console2.log("CCIPAdapter:", address(ccipAdapter));
        console2.log("CrossChainVault:", vault);
        console2.log("");
        console2.log("Next steps:");
        console2.log("1. Deploy on the other chain");
        console2.log("2. Configure trustedVaults mapping on both chains");
        console2.log("3. Update frontend configuration");
    }
}
