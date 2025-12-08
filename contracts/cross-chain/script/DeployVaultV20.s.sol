// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import {Script, console2} from "forge-std/Script.sol";
import {CrossChainVault} from "../src/CrossChainVault.sol";
import {BridgeManager} from "../src/BridgeManager.sol";
import {AxelarAdapter} from "../src/adapters/AxelarAdapter.sol";
import {CCIPAdapter} from "../src/adapters/CCIPAdapter.sol";

/**
 * @title DeployVaultV20
 * @notice Deploys CrossChainVault V20 with safety features:
 *         - MIN_GAS_AMOUNT enforcement (0.01 ETH)
 *         - Manual sync function for recovery
 *         - Balance reconciliation helper
 *         - Enhanced gas validation
 *
 * @dev V20 Improvements over V19:
 *      - Prevents permanent out-of-sync state with minimum gas enforcement
 *      - Provides recovery mechanisms for failed cross-chain messages
 *      - Better user experience with clear gas fee requirements
 *
 * @dev Run on Sepolia:
 *      DEPLOYER_PRIVATE_KEY=<key> forge script script/DeployVaultV20.s.sol:DeployVaultV20 \
 *        --rpc-url https://sepolia.infura.io/v3/YOUR_KEY \
 *        --broadcast --verify
 *
 * @dev Run on Polygon Amoy:
 *      DEPLOYER_PRIVATE_KEY=<key> forge script script/DeployVaultV20.s.sol:DeployVaultV20 \
 *        --rpc-url https://polygon-amoy.infura.io/v3/YOUR_KEY \
 *        --broadcast --verify
 */
contract DeployVaultV20 is Script {
    // Axelar addresses (same for all testnets)
    address constant AXELAR_GATEWAY_SEPOLIA = 0xe432150cce91c13a887f7D836923d5597adD8E31;
    address constant AXELAR_GATEWAY_AMOY = 0xe432150cce91c13a887f7D836923d5597adD8E31;
    address constant AXELAR_GAS_SERVICE_SEPOLIA = 0xbE406F0189A0B4cf3A05C286473D23791Dd44Cc6;
    address constant AXELAR_GAS_SERVICE_AMOY = 0xbE406F0189A0B4cf3A05C286473D23791Dd44Cc6;

    // CCIP addresses (optional, not used in V20 since we're using Axelar only)
    address constant CCIP_ROUTER_SEPOLIA = 0x0BF3dE8c5D3e8A2B34D2BEeB17ABfCeBaf363A59;
    address constant CCIP_ROUTER_AMOY = 0x9C32fCB86BF0f4a1A8921a9Fe46de3198bb884B2;

    function run() external {
        uint256 deployerKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        vm.startBroadcast(deployerKey);

        // Determine current chain
        uint256 chainId = block.chainid;
        console2.log("Deploying V20 on chain:", chainId);

        address axelarGateway;
        address axelarGasService;
        address ccipRouter;

        if (chainId == 11155111) {
            // Sepolia
            axelarGateway = AXELAR_GATEWAY_SEPOLIA;
            axelarGasService = AXELAR_GAS_SERVICE_SEPOLIA;
            ccipRouter = CCIP_ROUTER_SEPOLIA;
            console2.log("Network: Ethereum Sepolia");
        } else if (chainId == 80002) {
            // Polygon Amoy
            axelarGateway = AXELAR_GATEWAY_AMOY;
            axelarGasService = AXELAR_GAS_SERVICE_AMOY;
            ccipRouter = CCIP_ROUTER_AMOY;
            console2.log("Network: Polygon Amoy");
        } else {
            revert("Unsupported chain");
        }

        // Create deterministic salt for CREATE2 deployment
        // V20: Safety features (MIN_GAS_AMOUNT, manualSync, reconcileBalance)
        bytes32 salt = keccak256("CrossChainVault-V20-SafetyFeatures");

        // Step 1: Deploy BridgeManager
        console2.log("\nStep 1: Deploying BridgeManager...");
        BridgeManager bridgeManager = new BridgeManager{salt: salt}();
        console2.log("BridgeManager deployed at:", address(bridgeManager));

        // Step 2: Deploy Axelar Adapter
        console2.log("\nStep 2: Deploying AxelarAdapter...");
        string[] memory axelarChains = new string[](2);
        axelarChains[0] = "ethereum";
        axelarChains[1] = "polygon";

        AxelarAdapter axelarAdapter = new AxelarAdapter{salt: salt}(
            axelarGateway,
            axelarGasService,
            axelarChains
        );
        console2.log("AxelarAdapter deployed at:", address(axelarAdapter));

        // Step 3: Deploy CCIP Adapter (for future use)
        console2.log("\nStep 3: Deploying CCIPAdapter...");
        uint64[] memory ccipSelectors = new uint64[](2);
        string[] memory ccipChains = new string[](2);
        ccipSelectors[0] = 16015286601757825753; // Sepolia
        ccipSelectors[1] = 16281711391670634445; // Polygon Amoy
        ccipChains[0] = "ethereum";
        ccipChains[1] = "polygon";

        CCIPAdapter ccipAdapter = new CCIPAdapter{salt: salt}(
            ccipRouter,
            ccipSelectors,
            ccipChains
        );
        console2.log("CCIPAdapter deployed at:", address(ccipAdapter));

        // Step 4: Register Axelar as preferred protocol for all chains
        console2.log("\nStep 4: Registering Axelar as default protocol...");
        bridgeManager.registerAdapter(axelarAdapter);
        bridgeManager.setPreferredProtocol("ethereum", "axelar");
        bridgeManager.setPreferredProtocol("polygon", "axelar");

        // Step 5: Deploy CrossChainVault
        console2.log("\nStep 5: Deploying CrossChainVault...");
        string[] memory supportedChains = new string[](2);
        supportedChains[0] = "ethereum";
        supportedChains[1] = "polygon";

        CrossChainVault vault = new CrossChainVault{salt: salt}(
            address(bridgeManager),
            axelarGateway,
            ccipRouter,
            supportedChains
        );
        console2.log("CrossChainVault deployed at:", address(vault));

        // Display deployment summary
        console2.log("\n================================================");
        console2.log("V20 Deployment Complete");
        console2.log("================================================");
        console2.log("Chain ID:", chainId);
        console2.log("BridgeManager:", address(bridgeManager));
        console2.log("AxelarAdapter:", address(axelarAdapter));
        console2.log("CCIPAdapter:", address(ccipAdapter));
        console2.log("CrossChainVault:", address(vault));
        console2.log("================================================");
        console2.log("\nV20 Safety Features:");
        console2.log("- MIN_GAS_AMOUNT: 0.01 ETH enforcement");
        console2.log("- manualSync() for recovery");
        console2.log("- reconcileBalance() for fixing inconsistencies");
        console2.log("\nNext steps:");
        console2.log("1. Deploy on the other chain");
        console2.log("2. Run ConfigureV20 script to set trustedVaults");
        console2.log("3. Update frontend with new addresses");

        vm.stopBroadcast();
    }
}
