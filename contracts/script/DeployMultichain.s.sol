// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Script} from "forge-std/Script.sol";
import {console2} from "forge-std/console2.sol";
import {EscrowFactory} from "../escrow/src/EscrowFactory.sol";

/**
 * @title DeployMultichain
 * @notice Foundry script for deploying Fusion Prime contracts across multiple chains
 * @dev Supports deterministic deployment (CREATE2) and verification
 *
 * Usage:
 *   # Deploy to Sepolia
 *   forge script script/DeployMultichain.s.sol:DeployMultichain \
 *     --rpc-url $SEPOLIA_RPC_URL \
 *     --broadcast --verify -vvvv
 *
 *   # Deploy to Polygon Mumbai
 *   forge script script/DeployMultichain.s.sol:DeployMultichain \
 *     --rpc-url $MUMBAI_RPC_URL \
 *     --broadcast --verify -vvvv
 *
 *   # Deploy to all chains (requires multicall)
 *   forge script script/DeployMultichain.s.sol:DeployAll \
 *     --broadcast --verify -vvvv
 *
 * Environment Variables:
 *   PRIVATE_KEY              - Deployer private key
 *   SEPOLIA_RPC_URL          - Sepolia RPC endpoint
 *   AMOY_RPC_URL             - Polygon Amoy RPC endpoint
 *   ETHERSCAN_API_KEY        - Etherscan V2 API key (works for all supported chains)
 *   DEPLOYER_ADDRESS         - Override deployer address (optional)
 *   CREATE2_SALT             - Custom salt for deterministic deployment (optional)
 */
contract DeployMultichain is Script {
    // Deployment state
    struct DeploymentResult {
        address escrowFactory;
        uint256 chainId;
        string chainName;
    }

    // Default salt for CREATE2
    bytes32 public constant DEFAULT_SALT = keccak256("FUSION_PRIME_V1");

    // Chain configurations are now in ChainConfig.sol

    /**
     * @notice Main deployment function for single chain
     * @dev Called by `forge script` with specific RPC URL
     */
    function run() external returns (DeploymentResult memory) {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);

        console2.log("====================================");
        console2.log("Fusion Prime Multichain Deployment");
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

    /**
     * @notice Deploy contracts to current chain
     * @return result Deployment addresses and metadata
     */
    function deployContracts(
        address /* deployer */
    )
        internal
        returns (DeploymentResult memory result)
    {
        result.chainId = block.chainid;
        result.chainName = getChainName(block.chainid);

        // Deploy EscrowFactory
        console2.log(">>> Deploying EscrowFactory...");

        EscrowFactory factory = new EscrowFactory();
        result.escrowFactory = address(factory);
        console2.log("Factory deployed:", result.escrowFactory);

        // Verify deployment
        console2.log("");
        console2.log(">>> Verifying deployment...");
        verifyDeployment(result);

        return result;
    }

    /**
     * @notice Verify that deployed contracts are correctly configured
     * @param result Deployment result to verify
     */
    function verifyDeployment(DeploymentResult memory result) internal view {
        // Verify factory
        require(result.escrowFactory.code.length > 0, "Factory not deployed");
        EscrowFactory factory = EscrowFactory(result.escrowFactory);
        require(factory.getEscrowCount() == 0, "Factory should start with 0 escrows");

        console2.log("[OK] EscrowFactory verified");
    }

    /**
     * @notice Log deployment results
     * @param result Deployment result to log
     */
    function logDeployment(DeploymentResult memory result) internal pure {
        console2.log("");
        console2.log("====================================");
        console2.log("Deployment Summary");
        console2.log("====================================");
        console2.log("Chain:", result.chainName);
        console2.log("Chain ID:", result.chainId);
        console2.log("");
        console2.log("EscrowFactory:", result.escrowFactory);
        console2.log("====================================");
    }

    /**
     * @notice Save deployment artifact to JSON
     * @param result Deployment result to save
     */
    function saveDeploymentArtifact(DeploymentResult memory result) internal {
        string memory json = string.concat(
            "{",
            '"chainId":',
            vm.toString(result.chainId),
            ",",
            '"chainName":"',
            result.chainName,
            '",',
            '"escrowFactory":"',
            vm.toString(result.escrowFactory),
            '",',
            '"timestamp":',
            vm.toString(block.timestamp),
            "}"
        );

        string memory filename = string.concat(
            vm.projectRoot(), "/deployments/", vm.toString(result.chainId), "-", result.chainName, ".json"
        );

        vm.writeJson(json, filename);
        console2.log("");
        console2.log("Deployment artifact saved:", filename);
    }

    /**
     * @notice Get human-readable chain name
     * @param chainId Chain ID
     * @return Chain name
     */
    function getChainName(uint256 chainId) internal pure returns (string memory) {
        // Common chain IDs - can be extended via environment configuration
        if (chainId == 31337) return "local"; // Anvil
        if (chainId == 11155111) return "sepolia"; // Sepolia
        if (chainId == 80002) return "amoy"; // Polygon Amoy
        if (chainId == 1) return "mainnet"; // Ethereum
        if (chainId == 137) return "polygon"; // Polygon
        if (chainId == 8453) return "base"; // Base
        if (chainId == 84532) return "base-sepolia"; // Base Sepolia
        return "unknown";
    }

    /**
     * @notice Compute deterministic CREATE2 address
     * @param deployer Deployer address
     * @param salt Salt for CREATE2
     * @param bytecode Contract creation bytecode
     * @return predicted Predicted contract address
     */
    function computeCreate2Address(address deployer, bytes32 salt, bytes memory bytecode)
        public
        pure
        returns (address predicted)
    {
        bytes32 hash = keccak256(abi.encodePacked(bytes1(0xff), deployer, salt, keccak256(bytecode)));
        predicted = address(uint160(uint256(hash)));
    }
}

/**
 * @title DeployAll
 * @notice Deploy contracts to multiple chains in sequence
 * @dev Requires RPC URLs for all target chains
 */
contract DeployAll is Script {
    function run() external {
        console2.log("====================================");
        console2.log("Multi-Chain Deployment");
        console2.log("====================================");
        console2.log("");

        // Deploy to Sepolia
        if (vm.envOr("DEPLOY_SEPOLIA", false)) {
            console2.log(">>> Deploying to Sepolia...");
            string memory sepoliaRpc = vm.envString("SEPOLIA_RPC_URL");
            vm.createSelectFork(sepoliaRpc);

            DeployMultichain deployer = new DeployMultichain();
            deployer.run();
        }

        // Deploy to Amoy
        if (vm.envOr("DEPLOY_AMOY", false)) {
            console2.log("");
            console2.log(">>> Deploying to Amoy...");
            string memory amoyRpc = vm.envString("AMOY_RPC_URL");
            vm.createSelectFork(amoyRpc);

            DeployMultichain deployer = new DeployMultichain();
            deployer.run();
        }

        console2.log("");
        console2.log("====================================");
        console2.log("Multi-Chain Deployment Complete");
        console2.log("====================================");
    }
}
