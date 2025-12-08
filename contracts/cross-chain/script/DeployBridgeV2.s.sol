// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import {Script} from "forge-std/Script.sol";
import {console2} from "forge-std/console2.sol";
import {BridgeManager} from "../src/BridgeManager.sol";
import {AxelarAdapter} from "../src/adapters/AxelarAdapter.sol";
import {CCIPAdapter} from "../src/adapters/CCIPAdapter.sol";

/**
 * @title DeployBridgeV2
 * @notice Deploy corrected bridge infrastructure with proper chain names and selectors
 * @dev Deploys fresh BridgeManager + Adapters with all issues fixed
 *
 * FIXES:
 * 1. Axelar: Use correct testnet chain names ("ethereum-sepolia", "polygon-sepolia")
 * 2. CCIP: Use correct chain selectors from Chainlink docs
 * 3. Fresh BridgeManager allows proper configuration
 *
 * Usage on Sepolia:
 *   DEPLOYER_PRIVATE_KEY=0x... forge script script/DeployBridgeV2.s.sol:DeployBridgeV2 \
 *     --rpc-url https://ethereum-sepolia-rpc.publicnode.com \
 *     --broadcast -vvvv
 *
 * Usage on Amoy:
 *   DEPLOYER_PRIVATE_KEY=0x... forge script script/DeployBridgeV2.s.sol:DeployBridgeV2 \
 *     --rpc-url https://rpc-amoy.polygon.technology \
 *     --broadcast -vvvv
 */
contract DeployBridgeV2 is Script {
    // Protocol Infrastructure
    // Sepolia
    address constant AXELAR_GATEWAY_SEPOLIA = 0xe432150cce91c13a887f7D836923d5597adD8E31;
    address constant AXELAR_GAS_SERVICE_SEPOLIA = 0xbE406F0189A0B4cf3A05C286473D23791Dd44Cc6;
    address constant CCIP_ROUTER_SEPOLIA = 0x0BF3dE8c5D3e8A2B34D2BEeB17ABfCeBaf363A59;

    // Amoy (polygon-sepolia in Axelar testnet config)
    address constant AXELAR_GATEWAY_AMOY = 0xe432150cce91c13a887f7D836923d5597adD8E31; // CORRECT
    address constant AXELAR_GAS_SERVICE_AMOY = 0xbE406F0189A0B4cf3A05C286473D23791Dd44Cc6;
    address constant CCIP_ROUTER_AMOY = 0x9C32fCB86BF0f4a1A8921a9Fe46de3198bb884B2;

    // CCIP Chain Selectors (CORRECT VALUES from Chainlink docs)
    // Source: https://docs.chain.link/ccip/directory/testnet
    uint64 constant CCIP_SELECTOR_SEPOLIA = 16015286601757825753;
    uint64 constant CCIP_SELECTOR_AMOY = 16281711391670634445;
    uint64 constant CCIP_SELECTOR_ARBITRUM = 3478487238524512106;

    struct DeploymentResult {
        address bridgeManager;
        address axelarAdapter;
        address ccipAdapter;
        uint256 chainId;
        string chainName;
    }

    function run() external returns (DeploymentResult memory) {
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);
        uint256 chainId = block.chainid;

        console2.log("====================================");
        console2.log("Bridge V2 Deployment (CORRECTED)");
        console2.log("====================================");
        console2.log("Deployer:", deployer);
        console2.log("Chain ID:", chainId);
        console2.log("");

        DeploymentResult memory result;
        result.chainId = chainId;

        vm.startBroadcast(deployerPrivateKey);

        if (chainId == 11155111) {
            // Sepolia
            console2.log("Network: Ethereum Sepolia");
            result.chainName = "ethereum-sepolia";
            result = deploySepolia(result);
        } else if (chainId == 80002) {
            // Amoy
            console2.log("Network: Polygon Amoy");
            result.chainName = "polygon-sepolia";
            result = deployAmoy(result);
        } else {
            revert("Unsupported chain");
        }

        vm.stopBroadcast();

        logDeployment(result);
        return result;
    }

    function deploySepolia(DeploymentResult memory result) internal returns (DeploymentResult memory) {
        console2.log("");
        console2.log(">>> Deploying BridgeManager...");
        BridgeManager bridgeManager = new BridgeManager();
        result.bridgeManager = address(bridgeManager);
        console2.log("Deployed BridgeManager at:", result.bridgeManager);

        // Deploy Axelar Adapter with CORRECT chain names
        console2.log("");
        console2.log(">>> Deploying AxelarAdapter with correct testnet chain names...");
        string[] memory axelarChains = new string[](3);
        axelarChains[0] = "ethereum-sepolia"; // CORRECT
        axelarChains[1] = "polygon-sepolia"; // CORRECT
        axelarChains[2] = "arbitrum-sepolia"; // CORRECT

        AxelarAdapter axelarAdapter =
            new AxelarAdapter(AXELAR_GATEWAY_SEPOLIA, AXELAR_GAS_SERVICE_SEPOLIA, axelarChains);
        result.axelarAdapter = address(axelarAdapter);
        console2.log("Deployed AxelarAdapter at:", result.axelarAdapter);
        console2.log("  Supported chains:", axelarChains[0], axelarChains[1], axelarChains[2]);

        // Deploy CCIP Adapter with CORRECT selectors
        console2.log("");
        console2.log(">>> Deploying CCIPAdapter with correct chain selectors...");
        uint64[] memory ccipSelectors = new uint64[](3);
        ccipSelectors[0] = CCIP_SELECTOR_SEPOLIA; // 16015286601757825753
        ccipSelectors[1] = CCIP_SELECTOR_AMOY; // 16281711391670634445 CORRECT
        ccipSelectors[2] = CCIP_SELECTOR_ARBITRUM; // 3478487238524512106 CORRECT

        string[] memory ccipChains = new string[](3);
        ccipChains[0] = "ethereum";
        ccipChains[1] = "polygon";
        ccipChains[2] = "arbitrum";

        CCIPAdapter ccipAdapter = new CCIPAdapter(CCIP_ROUTER_SEPOLIA, ccipSelectors, ccipChains);
        result.ccipAdapter = address(ccipAdapter);
        console2.log("Deployed CCIPAdapter at:", result.ccipAdapter);
        console2.log("  Polygon Amoy selector:", CCIP_SELECTOR_AMOY);

        // Register adapters
        console2.log("");
        console2.log(">>> Registering adapters with BridgeManager...");
        bridgeManager.registerAdapter(axelarAdapter);
        console2.log("Registered AxelarAdapter");
        bridgeManager.registerAdapter(ccipAdapter);
        console2.log("Registered CCIPAdapter");

        // Set preferred protocols (using testnet chain names)
        console2.log("");
        console2.log(">>> Setting protocol preferences...");
        bridgeManager.setPreferredProtocol("polygon-sepolia", "axelar");
        console2.log("Set: polygon-sepolia -> axelar");
        bridgeManager.setPreferredProtocol("ethereum-sepolia", "axelar");
        console2.log("Set: ethereum-sepolia -> axelar");
        bridgeManager.setPreferredProtocol("arbitrum-sepolia", "axelar");
        console2.log("Set: arbitrum-sepolia -> axelar");

        return result;
    }

    function deployAmoy(DeploymentResult memory result) internal returns (DeploymentResult memory) {
        console2.log("");
        console2.log(">>> Deploying BridgeManager...");
        BridgeManager bridgeManager = new BridgeManager();
        result.bridgeManager = address(bridgeManager);
        console2.log("Deployed BridgeManager at:", result.bridgeManager);

        // Deploy Axelar Adapter with CORRECT chain names
        console2.log("");
        console2.log(">>> Deploying AxelarAdapter with correct testnet chain names...");
        string[] memory axelarChains = new string[](3);
        axelarChains[0] = "ethereum-sepolia"; // CORRECT
        axelarChains[1] = "polygon-sepolia"; // CORRECT
        axelarChains[2] = "arbitrum-sepolia"; // CORRECT

        AxelarAdapter axelarAdapter = new AxelarAdapter(AXELAR_GATEWAY_AMOY, AXELAR_GAS_SERVICE_AMOY, axelarChains);
        result.axelarAdapter = address(axelarAdapter);
        console2.log("Deployed AxelarAdapter at:", result.axelarAdapter);
        console2.log("  Supported chains:", axelarChains[0], axelarChains[1], axelarChains[2]);

        // Deploy CCIP Adapter with CORRECT selectors
        console2.log("");
        console2.log(">>> Deploying CCIPAdapter with correct chain selectors...");
        uint64[] memory ccipSelectors = new uint64[](3);
        ccipSelectors[0] = CCIP_SELECTOR_SEPOLIA; // 16015286601757825753 CORRECT
        ccipSelectors[1] = CCIP_SELECTOR_AMOY; // 16281711391670634445
        ccipSelectors[2] = CCIP_SELECTOR_ARBITRUM; // 3478487238524512106 CORRECT

        string[] memory ccipChains = new string[](3);
        ccipChains[0] = "ethereum";
        ccipChains[1] = "polygon";
        ccipChains[2] = "arbitrum";

        CCIPAdapter ccipAdapter = new CCIPAdapter(CCIP_ROUTER_AMOY, ccipSelectors, ccipChains);
        result.ccipAdapter = address(ccipAdapter);
        console2.log("Deployed CCIPAdapter at:", result.ccipAdapter);
        console2.log("  Ethereum Sepolia selector:", CCIP_SELECTOR_SEPOLIA);

        // Register adapters
        console2.log("");
        console2.log(">>> Registering adapters with BridgeManager...");
        bridgeManager.registerAdapter(axelarAdapter);
        console2.log("Registered AxelarAdapter");
        bridgeManager.registerAdapter(ccipAdapter);
        console2.log("Registered CCIPAdapter");

        // Set preferred protocols (using testnet chain names)
        console2.log("");
        console2.log(">>> Setting protocol preferences...");
        bridgeManager.setPreferredProtocol("ethereum-sepolia", "axelar");
        console2.log("Set: ethereum-sepolia -> axelar");
        bridgeManager.setPreferredProtocol("polygon-sepolia", "axelar");
        console2.log("Set: polygon-sepolia -> axelar");
        bridgeManager.setPreferredProtocol("arbitrum-sepolia", "axelar");
        console2.log("Set: arbitrum-sepolia -> axelar");

        return result;
    }

    function logDeployment(DeploymentResult memory result) internal pure {
        console2.log("");
        console2.log("====================================");
        console2.log("Deployment Summary");
        console2.log("====================================");
        console2.log("Chain:", result.chainName);
        console2.log("Chain ID:", result.chainId);
        console2.log("");
        console2.log("BridgeManager:", result.bridgeManager);
        console2.log("AxelarAdapter:", result.axelarAdapter);
        console2.log("CCIPAdapter:", result.ccipAdapter);
        console2.log("");
        console2.log("All contracts deployed and configured!");
        console2.log("");
        console2.log("NEXT STEPS:");
        console2.log("1. Update frontend contract addresses");
        console2.log("2. Test transfers in both directions");
        console2.log("3. Monitor cross-chain message delivery");
        console2.log("");
    }
}
