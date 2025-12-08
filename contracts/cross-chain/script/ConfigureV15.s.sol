// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import {Script} from "forge-std/Script.sol";
import {console2} from "forge-std/console2.sol";
import {CrossChainVault} from "../src/CrossChainVault.sol";

/**
 * @title ConfigureV15
 * @notice Configure trustedVaults mapping for V15 deployment
 */
contract ConfigureV15 is Script {
    // V15 Vault addresses
    address constant SEPOLIA_VAULT = 0x719175Cd948A60540fA9d897543c8Cf51466b78D;
    address constant AMOY_VAULT = 0x29a63aE20Dd743db2BaF80240a039a593dD6C3be;

    function run() external {
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        vm.startBroadcast(deployerPrivateKey);

        console2.log("====================================");
        console2.log("Configuring V15 Vaults");
        console2.log("====================================");
        console2.log("Chain ID:", block.chainid);

        CrossChainVault vault;
        address trustedVaultAddress;
        string memory trustedChain;

        if (block.chainid == 11155111) {
            // Sepolia -> trust Amoy vault
            vault = CrossChainVault(payable(SEPOLIA_VAULT));
            trustedVaultAddress = AMOY_VAULT;
            trustedChain = "polygon";
            console2.log("Configuring Sepolia vault");
        } else if (block.chainid == 80002) {
            // Amoy -> trust Sepolia vault
            vault = CrossChainVault(payable(AMOY_VAULT));
            trustedVaultAddress = SEPOLIA_VAULT;
            trustedChain = "ethereum";
            console2.log("Configuring Amoy vault");
        } else {
            revert("Unsupported chain");
        }

        console2.log("Setting trusted vault for chain:", trustedChain);
        console2.log("Trusted vault address:", trustedVaultAddress);

        vault.setTrustedVault(trustedChain, trustedVaultAddress);

        console2.log("Trusted vault configured successfully!");

        vm.stopBroadcast();

        console2.log("\n====================================");
        console2.log("Configuration Complete!");
        console2.log("====================================");
        console2.log("Vault:", address(vault));
        console2.log("Trusted Chain:", trustedChain);
        console2.log("Trusted Vault:", trustedVaultAddress);
    }
}
