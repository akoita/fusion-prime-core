// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import {Script, console2} from "forge-std/Script.sol";
import {CrossChainVault} from "../src/CrossChainVault.sol";

/**
 * @title ConfigureV20
 * @notice Configures trustedVaults for V20 deployment after both chains are deployed
 *
 * @dev This script must be run AFTER deploying on both Sepolia and Amoy
 *
 * @dev Run on Sepolia to configure Amoy vault:
 *      DEPLOYER_PRIVATE_KEY=<key> forge script script/ConfigureV20.s.sol:ConfigureV20 \
 *        --rpc-url https://sepolia.infura.io/v3/YOUR_KEY \
 *        --broadcast
 *
 * @dev Run on Amoy to configure Sepolia vault:
 *      DEPLOYER_PRIVATE_KEY=<key> forge script script/ConfigureV20.s.sol:ConfigureV20 \
 *        --rpc-url https://polygon-amoy.infura.io/v3/YOUR_KEY \
 *        --broadcast
 */
contract ConfigureV20 is Script {
    // V20 deployment addresses
    address constant SEPOLIA_VAULT = 0x5820443E51ED666cDFe3d19f293f72CD61829C5d;
    address constant AMOY_VAULT = 0xb0e352b60264C926f7B19F0fC5A1eeE499163c19;

    function run() external {
        require(SEPOLIA_VAULT != address(0), "Update SEPOLIA_VAULT address");
        require(AMOY_VAULT != address(0), "Update AMOY_VAULT address");

        uint256 deployerKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        vm.startBroadcast(deployerKey);

        uint256 chainId = block.chainid;
        console2.log("Configuring V20 on chain:", chainId);

        address localVault;
        address remoteVault;
        string memory remoteChainName;

        if (chainId == 11155111) {
            // We're on Sepolia, configure Polygon vault
            localVault = SEPOLIA_VAULT;
            remoteVault = AMOY_VAULT;
            remoteChainName = "polygon";
            console2.log("Network: Ethereum Sepolia");
            console2.log("Configuring trust with Polygon Amoy vault");
        } else if (chainId == 80002) {
            // We're on Amoy, configure Sepolia vault
            localVault = AMOY_VAULT;
            remoteVault = SEPOLIA_VAULT;
            remoteChainName = "ethereum";
            console2.log("Network: Polygon Amoy");
            console2.log("Configuring trust with Ethereum Sepolia vault");
        } else {
            revert("Unsupported chain");
        }

        CrossChainVault vault = CrossChainVault(payable(localVault));

        console2.log("Local vault:", localVault);
        console2.log("Remote vault:", remoteVault);
        console2.log("Remote chain:", remoteChainName);

        // Set trusted vault
        vault.setTrustedVault(remoteChainName, remoteVault);

        console2.log("\nConfiguration complete!");
        console2.log("Trusted vault configured for", remoteChainName);

        vm.stopBroadcast();
    }
}
