// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import {Script} from "forge-std/Script.sol";
import {console2} from "forge-std/console2.sol";
import {CrossChainVault} from "../src/CrossChainVault.sol";

/**
 * @title ConfigureV19
 * @notice Configure trustedVaults for V19 deployment with AxelarExecutable
 * @dev Run this on both Sepolia and Amoy to set up cross-chain trust
 */
contract ConfigureV19 is Script {
    // V19 Vault addresses
    address constant SEPOLIA_VAULT = 0xCC8505d5E64A64D2c203AE31a3FA3D6B83A41313;
    address constant AMOY_VAULT = 0x2cdcfa269775153B63bD7eB8032462Fa8F3125A7;

    function run() external {
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        vm.startBroadcast(deployerPrivateKey);

        console2.log("====================================");
        console2.log("Configuring V19 Trusted Vaults");
        console2.log("====================================");
        console2.log("Chain ID:", block.chainid);

        address localVault;
        address remoteVault;
        string memory remoteChainName;

        if (block.chainid == 11155111) {
            // Sepolia
            localVault = SEPOLIA_VAULT;
            remoteVault = AMOY_VAULT;
            remoteChainName = "polygon";
            console2.log("Configuring on Sepolia");
        } else if (block.chainid == 80002) {
            // Polygon Amoy
            localVault = AMOY_VAULT;
            remoteVault = SEPOLIA_VAULT;
            remoteChainName = "ethereum";
            console2.log("Configuring on Polygon Amoy");
        } else {
            revert("Unsupported chain");
        }

        console2.log("Local vault:", localVault);
        console2.log("Remote vault:", remoteVault);
        console2.log("Remote chain:", remoteChainName);

        // Set trusted vault
        CrossChainVault vault = CrossChainVault(payable(localVault));
        vault.setTrustedVault(remoteChainName, remoteVault);

        console2.log("\nConfiguration complete!");
        console2.log("Trusted vault set for", remoteChainName, ":", remoteVault);

        vm.stopBroadcast();
    }
}
