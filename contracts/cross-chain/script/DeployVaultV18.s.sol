// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import {Script} from "forge-std/Script.sol";
import {console2} from "forge-std/console2.sol";
import {CrossChainVault} from "../src/CrossChainVault.sol";
import {BridgeManager} from "../src/BridgeManager.sol";
import {AxelarAdapter} from "../src/adapters/AxelarAdapter.sol";
import {VaultFactory} from "../src/VaultFactory.sol";

/**
 * @title DeployVaultV18
 * @notice Deploy V18 using Axelar instead of CCIP
 * @dev Switching from CCIP to Axelar due to persistent InvalidEVMAddress errors in CCIP Router
 *      Axelar uses simpler string-based addressing which should be more reliable
 */
contract DeployVaultV18 is Script {
    // Axelar Gateway addresses (same for both testnet chains)
    address constant AXELAR_GATEWAY_SEPOLIA = 0xe432150cce91c13a887f7D836923d5597adD8E31;
    address constant AXELAR_GATEWAY_AMOY = 0xe432150cce91c13a887f7D836923d5597adD8E31;

    // Axelar Gas Service addresses (same for both testnet chains)
    address constant AXELAR_GAS_SERVICE_SEPOLIA = 0xbE406F0189A0B4cf3A05C286473D23791Dd44Cc6;
    address constant AXELAR_GAS_SERVICE_AMOY = 0xbE406F0189A0B4cf3A05C286473D23791Dd44Cc6;

    function run() external {
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        vm.startBroadcast(deployerPrivateKey);

        console2.log("====================================");
        console2.log("Deploying V18 - Axelar Protocol");
        console2.log("====================================");
        console2.log("Chain ID:", block.chainid);

        address axelarGateway;
        address axelarGasService;
        string memory destinationChainName;

        if (block.chainid == 11155111) {
            // Sepolia
            axelarGateway = AXELAR_GATEWAY_SEPOLIA;
            axelarGasService = AXELAR_GAS_SERVICE_SEPOLIA;
            destinationChainName = "polygon";
            console2.log("Deploying on Sepolia");
        } else if (block.chainid == 80002) {
            // Polygon Amoy
            axelarGateway = AXELAR_GATEWAY_AMOY;
            axelarGasService = AXELAR_GAS_SERVICE_AMOY;
            destinationChainName = "ethereum";
            console2.log("Deploying on Polygon Amoy");
        } else {
            revert("Unsupported chain");
        }

        // 1. Deploy BridgeManager
        console2.log("\n--- Step 1: Deploy BridgeManager ---");
        BridgeManager bridgeManager = new BridgeManager();
        console2.log("BridgeManager deployed:", address(bridgeManager));

        // 2. Deploy AxelarAdapter
        console2.log("\n--- Step 2: Deploy AxelarAdapter ---");
        string[] memory axelarChains = new string[](1);
        axelarChains[0] = destinationChainName;

        AxelarAdapter axelarAdapter = new AxelarAdapter(
            axelarGateway,
            axelarGasService,
            axelarChains
        );
        console2.log("AxelarAdapter deployed:", address(axelarAdapter));
        console2.log("  - Gateway:", axelarGateway);
        console2.log("  - Gas Service:", axelarGasService);

        // 3. Register AxelarAdapter with BridgeManager
        console2.log("\n--- Step 3: Register Adapter ---");
        bridgeManager.registerAdapter(axelarAdapter);
        console2.log("AxelarAdapter registered");

        // 3b. Set Axelar as preferred protocol
        console2.log("\n--- Step 3b: Set Preferred Protocol ---");
        bridgeManager.setPreferredProtocol(destinationChainName, "axelar");
        console2.log("Preferred protocol set: axelar for", destinationChainName);

        // 4. Deploy CrossChainVault
        console2.log("\n--- Step 4: Deploy CrossChainVault ---");

        string[] memory supportedChains = new string[](1);
        supportedChains[0] = destinationChainName;

        VaultFactory factory = new VaultFactory();
        console2.log("VaultFactory deployed:", address(factory));

        bytes32 salt = keccak256("CrossChainVault-V18-Axelar");
        address predictedVault = factory.computeVaultAddress(
            address(bridgeManager),
            axelarGateway,
            address(0), // No CCIP
            supportedChains,
            salt
        );
        console2.log("Predicted vault:", predictedVault);

        address vault = factory.deployVault(
            address(bridgeManager),
            axelarGateway,
            address(0), // No CCIP
            supportedChains,
            salt
        );
        console2.log("CrossChainVault deployed:", vault);
        require(vault == predictedVault, "Vault address mismatch");

        vm.stopBroadcast();

        console2.log("\n====================================");
        console2.log("V18 Deployment Complete!");
        console2.log("====================================");
        console2.log("BridgeManager:", address(bridgeManager));
        console2.log("AxelarAdapter:", address(axelarAdapter));
        console2.log("CrossChainVault:", vault);
        console2.log("");
        console2.log("PROTOCOL: Axelar (instead of CCIP)");
        console2.log("  - String-based addressing");
        console2.log("  - Preferred protocol: axelar");
        console2.log("  - Destination chain:", destinationChainName);
    }
}
