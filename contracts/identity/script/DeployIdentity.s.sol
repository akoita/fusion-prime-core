// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/Identity.sol";
import "../src/IdentityFactory.sol";
import "../src/ClaimIssuerRegistry.sol";

/**
 * @title DeployIdentity
 * @dev Deployment script for ERC-734/735 Identity system
 * @notice Deploys ClaimIssuerRegistry and IdentityFactory
 *
 * Usage:
 *   forge script script/DeployIdentity.s.sol:DeployIdentity \
 *     --rpc-url $ETH_RPC_URL \
 *     --private-key $DEPLOYER_PRIVATE_KEY \
 *     --broadcast \
 *     --verify \
 *     --etherscan-api-key $ETHERSCAN_API_KEY
 *
 * Or using environment:
 *   source .env.dev
 *   forge script script/DeployIdentity.s.sol:DeployIdentity \
 *     --rpc-url sepolia \
 *     --broadcast \
 *     --verify
 */
contract DeployIdentity is Script {
    function run() external {
        // Get deployer from private key
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);

        console.log("===========================================");
        console.log("Deploying ERC-734/735 Identity System");
        console.log("===========================================");
        console.log("Deployer:", deployer);
        console.log("Chain ID:", block.chainid);
        console.log("-------------------------------------------");

        vm.startBroadcast(deployerPrivateKey);

        // 1. Deploy ClaimIssuerRegistry
        console.log("\n1. Deploying ClaimIssuerRegistry...");
        ClaimIssuerRegistry registry = new ClaimIssuerRegistry();
        console.log("   ClaimIssuerRegistry deployed at:", address(registry));

        // 2. Deploy IdentityFactory
        console.log("\n2. Deploying IdentityFactory...");
        IdentityFactory factory = new IdentityFactory(address(registry));
        console.log("   IdentityFactory deployed at:", address(factory));

        // 3. Add deployer as trusted issuer (for initial setup)
        console.log("\n3. Adding deployer as trusted issuer...");
        uint256[] memory topics = new uint256[](5);
        topics[0] = 1; // KYC_VERIFIED
        topics[1] = 2; // AML_CLEARED
        topics[2] = 3; // ACCREDITED_INVESTOR
        topics[3] = 4; // SANCTIONS_CLEARED
        topics[4] = 5; // COUNTRY_ALLOWED

        registry.addIssuer(deployer, "Fusion Prime Identity Service", topics);
        console.log("   Deployer added as trusted issuer with all topic permissions");

        vm.stopBroadcast();

        // 4. Print deployment summary
        console.log("\n===========================================");
        console.log("Deployment Complete!");
        console.log("===========================================");
        console.log("ClaimIssuerRegistry:", address(registry));
        console.log("IdentityFactory:     ", address(factory));
        console.log("\nAdd these to your .env.dev:");
        console.log("-------------------------------------------");
        console.log("CLAIM_ISSUER_REGISTRY_ADDRESS=%s", address(registry));
        console.log("IDENTITY_FACTORY_ADDRESS=%s", address(factory));
        console.log("\nAdd these to frontend .env:");
        console.log("-------------------------------------------");
        console.log("VITE_CLAIM_ISSUER_REGISTRY_ADDRESS=%s", address(registry));
        console.log("VITE_IDENTITY_FACTORY_ADDRESS=%s", address(factory));
        console.log("\nVerify contracts on Etherscan:");
        console.log("-------------------------------------------");
        console.log("forge verify-contract %s ClaimIssuerRegistry --chain sepolia", address(registry));
        console.log(
            "forge verify-contract %s IdentityFactory --constructor-args $(cast abi-encode 'constructor(address)' %s) --chain sepolia",
            address(factory),
            address(registry)
        );
        console.log("===========================================\n");
    }
}
