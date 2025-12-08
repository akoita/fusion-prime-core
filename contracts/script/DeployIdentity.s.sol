// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../identity/src/Identity.sol";
import "../identity/src/IdentityFactory.sol";
import "../identity/src/ClaimIssuerRegistry.sol";

/**
 * @title DeployIdentity
 * @notice Deployment script for the complete identity system
 * @dev Deploys ClaimIssuerRegistry, IdentityFactory, and sets up initial configuration
 */
contract DeployIdentity is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);

        console.log("Deploying Identity System...");
        console.log("Deployer address:", deployer);

        vm.startBroadcast(deployerPrivateKey);

        // Step 1: Deploy ClaimIssuerRegistry
        console.log("\n1. Deploying ClaimIssuerRegistry...");
        ClaimIssuerRegistry registry = new ClaimIssuerRegistry();
        console.log("ClaimIssuerRegistry deployed at:", address(registry));

        // Step 2: Deploy IdentityFactory
        console.log("\n2. Deploying IdentityFactory...");
        IdentityFactory factory = new IdentityFactory(address(registry));
        console.log("IdentityFactory deployed at:", address(factory));

        // Step 3: Add backend service as trusted issuer (if configured)
        address backendIssuer = vm.envOr("BACKEND_ISSUER_ADDRESS", address(0));
        if (backendIssuer != address(0)) {
            console.log("\n3. Adding backend service as trusted issuer...");
            uint256[] memory allowedTopics = new uint256[](5);
            allowedTopics[0] = 1; // KYC_VERIFIED
            allowedTopics[1] = 2; // AML_CLEARED
            allowedTopics[2] = 3; // ACCREDITED_INVESTOR
            allowedTopics[3] = 4; // SANCTIONS_CLEARED
            allowedTopics[4] = 5; // COUNTRY_ALLOWED

            registry.addIssuer(backendIssuer, "Fusion Prime Backend Service", allowedTopics);
            console.log("Backend issuer added:", backendIssuer);
        }

        vm.stopBroadcast();

        // Print deployment summary
        console.log("\n========================================");
        console.log("DEPLOYMENT SUMMARY");
        console.log("========================================");
        console.log("Network:", block.chainid);
        console.log("Deployer:", deployer);
        console.log("ClaimIssuerRegistry:", address(registry));
        console.log("IdentityFactory:", address(factory));
        if (backendIssuer != address(0)) {
            console.log("Backend Issuer:", backendIssuer);
        }
        console.log("========================================");

        // Save deployment info
        string memory deploymentInfo = string(
            abi.encodePacked(
                "{\n",
                '  "network": "',
                vm.toString(block.chainid),
                '",\n',
                '  "deployer": "',
                vm.toString(deployer),
                '",\n',
                '  "ClaimIssuerRegistry": "',
                vm.toString(address(registry)),
                '",\n',
                '  "IdentityFactory": "',
                vm.toString(address(factory)),
                '",\n',
                '  "BackendIssuer": "',
                vm.toString(backendIssuer),
                '"\n',
                "}\n"
            )
        );

        string memory deploymentPath =
            string(abi.encodePacked("./deployments/identity-", vm.toString(block.chainid), ".json"));

        vm.writeFile(deploymentPath, deploymentInfo);
        console.log("\nDeployment info saved to:", deploymentPath);
    }
}
