// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import {Script} from "forge-std/Script.sol";
import {console2} from "forge-std/console2.sol";
import {BridgeManager} from "../src/BridgeManager.sol";
import {CCIPAdapter} from "../src/adapters/CCIPAdapter.sol";
import {CrossChainVault} from "../src/CrossChainVault.sol";
import {VaultFactory} from "../src/VaultFactory.sol";

/**
 * @title DeployCCIP
 * @notice Deploy with Chainlink CCIP (reliable testnet infrastructure)
 * @dev Uses CCIP Router for cross-chain messaging
 */
contract DeployCCIP is Script {
    // CCIP Router addresses (testnet)
    address constant SEPOLIA_CCIP_ROUTER = 0x0BF3dE8c5D3e8A2B34D2BEeB17ABfCeBaf363A59;
    address constant AMOY_CCIP_ROUTER = 0x9C32fCB86BF0f4a1A8921a9Fe46de3198bb884B2;

    // Dummy Axelar addresses (vault still needs them in constructor but won't use them)
    address constant DUMMY_AXELAR_GATEWAY = address(0);

    // CCIP chain selectors
    uint64 constant SEPOLIA_SELECTOR = 16015286601757825753;
    uint64 constant AMOY_SELECTOR = 16281711391670634445;

    // CCIP deployment salts
    bytes32 constant BRIDGE_MANAGER_SALT = keccak256("FusionPrime.BridgeManager.ccip");
    bytes32 constant VAULT_FACTORY_SALT = keccak256("FusionPrime.VaultFactory.ccip");
    bytes32 constant CCIP_ADAPTER_SALT = keccak256("FusionPrime.CCIPAdapter.ccip");
    bytes32 constant VAULT_SALT = keccak256("FusionPrime.CrossChainVault.ccip.v7");

    struct DeploymentResult {
        address bridgeManager;
        address ccipAdapter;
        address vaultFactory;
        address crossChainVault;
        uint256 chainId;
    }

    function run() external returns (DeploymentResult memory) {
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");

        vm.startBroadcast(deployerPrivateKey);

        console2.log("====================================");
        console2.log("CCIP Deployment - Reliable Testnet");
        console2.log("====================================");
        console2.log("Chain ID:", block.chainid);
        console2.log("");

        DeploymentResult memory result = deployContracts();

        vm.stopBroadcast();

        logDeployment(result);
        return result;
    }

    function deployContracts() internal returns (DeploymentResult memory result) {
        result.chainId = block.chainid;

        // Get CCIP router for this chain
        address ccipRouter = getCCIPRouter(block.chainid);

        // 1. Deploy BridgeManager
        console2.log(">>> Deploying BridgeManager...");
        result.bridgeManager = deployWithCREATE2(
            type(BridgeManager).creationCode,
            BRIDGE_MANAGER_SALT
        );
        console2.log("BridgeManager:", result.bridgeManager);

        // 2. Deploy VaultFactory
        console2.log(">>> Deploying VaultFactory...");
        result.vaultFactory = deployWithCREATE2(
            type(VaultFactory).creationCode,
            VAULT_FACTORY_SALT
        );
        console2.log("VaultFactory:", result.vaultFactory);

        // 3. Deploy CCIPAdapter
        console2.log(">>> Deploying CCIPAdapter...");
        uint64[] memory chainSelectors = new uint64[](2);
        string[] memory chainNames = new string[](2);

        chainSelectors[0] = SEPOLIA_SELECTOR;
        chainSelectors[1] = AMOY_SELECTOR;
        chainNames[0] = "ethereum";
        chainNames[1] = "polygon";

        bytes memory ccipBytecode = abi.encodePacked(
            type(CCIPAdapter).creationCode,
            abi.encode(ccipRouter, chainSelectors, chainNames)
        );
        result.ccipAdapter = deployWithCREATE2(ccipBytecode, CCIP_ADAPTER_SALT);
        console2.log("CCIPAdapter:", result.ccipAdapter);

        // 4. Register adapter
        console2.log(">>> Registering CCIP adapter...");
        BridgeManager bridgeManager = BridgeManager(result.bridgeManager);
        bridgeManager.registerAdapter(CCIPAdapter(result.ccipAdapter));

        // 5. Set protocol preferences
        console2.log(">>> Setting protocol preferences...");
        bridgeManager.setPreferredProtocol("ethereum", "ccip");
        bridgeManager.setPreferredProtocol("polygon", "ccip");

        // 6. Deploy CrossChainVault via Factory
        console2.log(">>> Deploying CrossChainVault...");
        string[] memory supportedChains = new string[](2);
        supportedChains[0] = "ethereum";
        supportedChains[1] = "polygon";

        VaultFactory factory = VaultFactory(result.vaultFactory);
        result.crossChainVault = factory.deployVault(
            result.bridgeManager,
            DUMMY_AXELAR_GATEWAY, // Not used for CCIP
            ccipRouter,
            supportedChains,
            VAULT_SALT
        );
        console2.log("CrossChainVault:", result.crossChainVault);

        return result;
    }

    function deployWithCREATE2(bytes memory bytecode, bytes32 salt) internal returns (address deployed) {
        assembly {
            deployed := create2(0, add(bytecode, 32), mload(bytecode), salt)
            if iszero(deployed) { revert(0, 0) }
        }
    }

    function getCCIPRouter(uint256 chainId) internal pure returns (address) {
        if (chainId == 11155111) return SEPOLIA_CCIP_ROUTER;  // Sepolia
        if (chainId == 80002) return AMOY_CCIP_ROUTER;        // Polygon Amoy
        revert("Unsupported chain");
    }

    function logDeployment(DeploymentResult memory result) internal pure {
        console2.log("");
        console2.log("====================================");
        console2.log("CCIP Deployment Complete");
        console2.log("====================================");
        console2.log("BridgeManager:    ", result.bridgeManager);
        console2.log("CCIPAdapter:      ", result.ccipAdapter);
        console2.log("VaultFactory:     ", result.vaultFactory);
        console2.log("CrossChainVault:  ", result.crossChainVault);
        console2.log("");
        console2.log("Using Chainlink CCIP for reliable cross-chain messaging");
        console2.log("====================================");
    }
}
