// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import {Script} from "forge-std/Script.sol";
import {console2} from "forge-std/console2.sol";
import {BridgeManager} from "../cross-chain/src/BridgeManager.sol";
import {AxelarAdapter} from "../cross-chain/src/adapters/AxelarAdapter.sol";
import {CCIPAdapter} from "../cross-chain/src/adapters/CCIPAdapter.sol";
import {CrossChainVault} from "../cross-chain/src/CrossChainVault.sol";

/**
 * @title DeployCrossChain
 * @notice Foundry script for deploying cross-chain contracts (BridgeManager, Adapters, CrossChainVault)
 * @dev Deploys the full cross-chain infrastructure on each chain
 *
 * Usage:
 *   # Deploy to Sepolia
 *   forge script script/DeployCrossChain.s.sol:DeployCrossChain \
 *     --rpc-url $ETH_RPC_URL \
 *     --broadcast --verify -vvvv
 *
 *   # Deploy to Amoy
 *   forge script script/DeployCrossChain.s.sol:DeployCrossChain \
 *     --rpc-url $POLYGON_RPC_URL \
 *     --broadcast --verify -vvvv
 *
 * Environment Variables:
 *   PRIVATE_KEY              - Deployer private key
 *   ETH_RPC_URL              - Ethereum Sepolia RPC endpoint
 *   POLYGON_RPC_URL          - Polygon Amoy RPC endpoint
 *   ETHERSCAN_API_KEY        - Etherscan API key for verification
 */
contract DeployCrossChain is Script {
    // Testnet contract addresses
    // Ethereum Sepolia
    address constant AXELAR_GATEWAY_SEPOLIA = 0xe432150cce91c13a887f7D836923d5597adD8E31;
    address constant AXELAR_GAS_SERVICE_SEPOLIA = 0xbE406F0189A0B4cf3A05C286473D23791Dd44Cc6;
    address constant CCIP_ROUTER_SEPOLIA = 0x0BF3dE8c5D3e8A2B34D2BEeB17ABfCeBaf363A59;

    // Polygon Amoy
    address constant AXELAR_GATEWAY_AMOY = 0xBF62eF1486468a6bD26DD669C06Db43De641D239;
    address constant AXELAR_GAS_SERVICE_AMOY = 0xbE406F0189A0B4cf3A05C286473D23791Dd44Cc6;
    address constant CCIP_ROUTER_AMOY = 0x1035CabC275068e0F4b745A29CEDf38E13aF41b1;

    // Arbitrum Sepolia
    address constant AXELAR_GATEWAY_ARBITRUM = 0xe432150cce91c13a887f7D836923d5597adD8E31;
    address constant CCIP_ROUTER_ARBITRUM = 0x88e492127709447a5AB4dA4a0d1861BAb2Be98e5;

    // Chain selectors (CCIP) - Source: https://docs.chain.link/ccip/directory/testnet
    uint64 constant CCIP_SELECTOR_SEPOLIA = 16015286601757825753;
    uint64 constant CCIP_SELECTOR_AMOY = 16281711391670634445; // ← FIXED: was 12532609583862916517
    uint64 constant CCIP_SELECTOR_ARBITRUM = 3478487238524512106; // ← FIXED: was 5800955286103778722

    struct DeploymentResult {
        address bridgeManager;
        address axelarAdapter;
        address ccipAdapter;
        address crossChainVault;
        uint256 chainId;
        string chainName;
    }

    function run() external returns (DeploymentResult memory) {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);

        console2.log("====================================");
        console2.log("Cross-Chain Contracts Deployment");
        console2.log("====================================");
        console2.log("Deployer:", deployer);
        console2.log("Chain ID:", block.chainid);
        console2.log("Balance:", deployer.balance);
        console2.log("");

        vm.startBroadcast(deployerPrivateKey);

        DeploymentResult memory result = deployContracts(deployer);

        vm.stopBroadcast();

        logDeployment(result);
        saveDeploymentArtifact(result);

        return result;
    }

    function deployContracts(address deployer) internal returns (DeploymentResult memory result) {
        result.chainId = block.chainid;
        result.chainName = getChainName(block.chainid);

        // Get testnet addresses for current chain
        (address axelarGateway, address axelarGasService, address ccipRouter, uint64 ccipSelector) =
            getTestnetAddresses(block.chainid);

        console2.log(">>> Deploying BridgeManager...");
        BridgeManager bridgeManager = new BridgeManager();
        result.bridgeManager = address(bridgeManager);
        console2.log("Deployed BridgeManager at:", result.bridgeManager);

        // Deploy Axelar Adapter
        console2.log(">>> Deploying AxelarAdapter...");
        string[] memory axelarChains = new string[](3);
        axelarChains[0] = "ethereum";
        axelarChains[1] = "polygon";
        axelarChains[2] = "arbitrum";

        AxelarAdapter axelarAdapter = new AxelarAdapter(axelarGateway, axelarGasService, axelarChains);
        result.axelarAdapter = address(axelarAdapter);
        console2.log("Deployed AxelarAdapter at:", result.axelarAdapter);

        // Deploy CCIP Adapter
        console2.log(">>> Deploying CCIPAdapter...");
        uint64[] memory ccipSelectors = new uint64[](3);
        ccipSelectors[0] = CCIP_SELECTOR_SEPOLIA;
        ccipSelectors[1] = CCIP_SELECTOR_AMOY;
        ccipSelectors[2] = CCIP_SELECTOR_ARBITRUM;

        string[] memory ccipChainNames = new string[](3);
        ccipChainNames[0] = "ethereum";
        ccipChainNames[1] = "polygon";
        ccipChainNames[2] = "arbitrum";

        CCIPAdapter ccipAdapter = new CCIPAdapter(ccipRouter, ccipSelectors, ccipChainNames);
        result.ccipAdapter = address(ccipAdapter);
        console2.log("Deployed CCIPAdapter at:", result.ccipAdapter);

        // Register adapters with BridgeManager
        console2.log(">>> Registering adapters...");
        bridgeManager.registerAdapter(axelarAdapter);
        bridgeManager.registerAdapter(ccipAdapter);
        console2.log("Adapters registered");

        // Set protocol preferences
        console2.log(">>> Setting protocol preferences...");
        bridgeManager.setPreferredProtocol("polygon", "ccip");
        bridgeManager.setPreferredProtocol("ethereum", "axelar");
        bridgeManager.setPreferredProtocol("arbitrum", "axelar");
        console2.log("Protocol preferences set");

        // Deploy CrossChainVault
        console2.log(">>> Deploying CrossChainVault...");
        string[] memory supportedChains = new string[](3);
        supportedChains[0] = "ethereum";
        supportedChains[1] = "polygon";
        supportedChains[2] = "arbitrum";

        string memory currentChainName = result.chainName;
        CrossChainVault vault = new CrossChainVault(address(bridgeManager), currentChainName, supportedChains);
        result.crossChainVault = address(vault);
        console2.log("Deployed CrossChainVault at:", result.crossChainVault);

        return result;
    }

    function getTestnetAddresses(uint256 chainId)
        internal
        pure
        returns (address axelarGateway, address axelarGasService, address ccipRouter, uint64 ccipSelector)
    {
        if (chainId == 11155111) {
            // Sepolia
            return (AXELAR_GATEWAY_SEPOLIA, AXELAR_GAS_SERVICE_SEPOLIA, CCIP_ROUTER_SEPOLIA, CCIP_SELECTOR_SEPOLIA);
        } else if (chainId == 80002) {
            // Amoy
            return (AXELAR_GATEWAY_AMOY, AXELAR_GAS_SERVICE_AMOY, CCIP_ROUTER_AMOY, CCIP_SELECTOR_AMOY);
        } else if (chainId == 421614) {
            // Arbitrum Sepolia
            return (AXELAR_GATEWAY_ARBITRUM, AXELAR_GAS_SERVICE_SEPOLIA, CCIP_ROUTER_ARBITRUM, CCIP_SELECTOR_ARBITRUM);
        } else {
            revert("Unsupported chain");
        }
    }

    function getChainName(uint256 chainId) internal pure returns (string memory) {
        if (chainId == 11155111) return "ethereum";
        if (chainId == 80002) return "polygon";
        if (chainId == 421614) return "arbitrum";
        return "unknown";
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
        console2.log("CrossChainVault:", result.crossChainVault);
        console2.log("====================================");
    }

    function saveDeploymentArtifact(DeploymentResult memory result) internal {
        string memory filename = string.concat(
            vm.projectRoot(), "/deployments/", vm.toString(result.chainId), "-", result.chainName, "-cross-chain.json"
        );

        string memory json = string.concat(
            "{\n",
            "  \"chainId\": ",
            vm.toString(result.chainId),
            ",\n",
            "  \"chainName\": \"",
            result.chainName,
            "\",\n",
            "  \"bridgeManager\": \"",
            vm.toString(result.bridgeManager),
            "\",\n",
            "  \"axelarAdapter\": \"",
            vm.toString(result.axelarAdapter),
            "\",\n",
            "  \"ccipAdapter\": \"",
            vm.toString(result.ccipAdapter),
            "\",\n",
            "  \"crossChainVault\": \"",
            vm.toString(result.crossChainVault),
            "\",\n",
            "  \"timestamp\": ",
            vm.toString(block.timestamp),
            "\n",
            "}\n"
        );

        vm.writeFile(filename, json);
        console2.log("Deployment artifact saved to:", filename);
    }
}
