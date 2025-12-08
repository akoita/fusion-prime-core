// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.30;

import "forge-std/Script.sol";
import "../src/CrossChainVaultV25.sol";

/**
 * @title DeployVaultV26
 * @notice Deploys CrossChainVaultV26 with AUTOMATIC withdrawal from previous version
 * @dev Usage:
 *   PRIVATE_KEY=<key> forge script script/DeployVaultV26.s.sol:DeployVaultV26 \
 *     --rpc-url <rpc-url> --broadcast
 *
 * Features:
 * - Automatically withdraws funds from previous vault version before deployment
 * - Deploys new vault with same configuration
 * - Configures trusted vaults
 *
 * Environment Variables:
 * - PRIVATE_KEY: Deployer private key
 * - PREVIOUS_VAULT (optional): Address of previous vault to withdraw from
 */
contract DeployVaultV26 is Script {
    // BridgeManager addresses (from previous deployments)
    address constant SEPOLIA_BRIDGE_MANAGER = 0xA8d853C5b945924d217Ec4119E9f0e2eFf714B8a;
    address constant AMOY_BRIDGE_MANAGER = 0xEEcd2114162D577c4668B8e92a6FB34d0eA6A149;

    // Axelar Gateway addresses
    address constant SEPOLIA_AXELAR_GATEWAY = 0xe432150cce91c13a887f7D836923d5597adD8E31;
    address constant AMOY_AXELAR_GATEWAY = 0x2A723E9BBD44C27A0F0FC13f46C41Ab59EDdd6E8;

    // CCIP Router addresses
    address constant SEPOLIA_CCIP_ROUTER = 0x0BF3dE8c5D3e8A2B34D2BEeB17ABfCeBaf363A59;
    address constant AMOY_CCIP_ROUTER = 0x9C32fCB86BF0f4a1A8921a9Fe46de3198bb884B2;

    // Chainlink Oracle addresses
    address constant SEPOLIA_ORACLE = 0x184e08394672B9Bf7aE670A3867C3c97A67A4e5C;
    address constant AMOY_ORACLE = 0x895c8848429745221d540366BC7aFCD0A7AFE3bF;

    // Previous vault addresses (V25) - UPDATE THESE WHEN DEPLOYING V27, V28, etc.
    address constant SEPOLIA_PREVIOUS_VAULT = 0x477f54284367CF31B2B7f6BB2Ca4291D3f43a312;
    address constant AMOY_PREVIOUS_VAULT = 0xbafd9d789f96d18cedd057899a4ba3273c9f6d0e;

    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);

        console.log("=== CrossChainVault V26 Deployment ===");
        console.log("Deployer:", deployer);
        console.log("Chain ID:", block.chainid);
        console.log("");

        // Step 1: Withdraw from previous vault
        withdrawFromPreviousVault(deployerPrivateKey, deployer);

        console.log("");
        console.log("=== Deploying New Vault ===");

        vm.startBroadcast(deployerPrivateKey);

        CrossChainVaultV25 vault;

        if (block.chainid == 11155111) {
            // Sepolia deployment
            console.log("Network: Sepolia");
            console.log("BridgeManager:", SEPOLIA_BRIDGE_MANAGER);
            console.log("Axelar Gateway:", SEPOLIA_AXELAR_GATEWAY);
            console.log("CCIP Router:", SEPOLIA_CCIP_ROUTER);

            string[] memory supportedChains = new string[](2);
            supportedChains[0] = "ethereum";
            supportedChains[1] = "polygon";

            address[] memory oracles = new address[](2);
            oracles[0] = SEPOLIA_ORACLE;
            oracles[1] = AMOY_ORACLE;

            vault = new CrossChainVaultV25(
                SEPOLIA_BRIDGE_MANAGER,
                SEPOLIA_AXELAR_GATEWAY,
                SEPOLIA_CCIP_ROUTER,
                supportedChains,
                oracles
            );

            console.log("Vault deployed at:", address(vault));

        } else if (block.chainid == 80002) {
            // Amoy deployment
            console.log("Network: Polygon Amoy");
            console.log("BridgeManager:", AMOY_BRIDGE_MANAGER);
            console.log("Axelar Gateway:", AMOY_AXELAR_GATEWAY);
            console.log("CCIP Router:", AMOY_CCIP_ROUTER);

            string[] memory supportedChains = new string[](2);
            supportedChains[0] = "ethereum";
            supportedChains[1] = "polygon";

            address[] memory oracles = new address[](2);
            oracles[0] = SEPOLIA_ORACLE;
            oracles[1] = AMOY_ORACLE;

            vault = new CrossChainVaultV25(
                AMOY_BRIDGE_MANAGER,
                AMOY_AXELAR_GATEWAY,
                AMOY_CCIP_ROUTER,
                supportedChains,
                oracles
            );

            console.log("Vault deployed at:", address(vault));

        } else {
            revert("Unsupported chain");
        }

        vm.stopBroadcast();

        console.log("");
        console.log("=== Deployment Complete ===");
        console.log("New Vault Address:", address(vault));
        console.log("");
        console.log("Next steps:");
        console.log("1. Update frontend config with new vault address");
        console.log("2. Configure trusted vaults (setTrustedVault)");
        console.log("3. Update PREVIOUS_VAULT constants in DeployVaultV27.s.sol");
    }

    /**
     * @notice Withdraws all funds from the previous vault version
     * @dev Attempts to withdraw both collateral and supplied funds
     */
    function withdrawFromPreviousVault(uint256 privateKey, address deployer) internal {
        address previousVault;

        if (block.chainid == 11155111) {
            previousVault = SEPOLIA_PREVIOUS_VAULT;
        } else if (block.chainid == 80002) {
            previousVault = AMOY_PREVIOUS_VAULT;
        } else {
            console.log("No previous vault configured for this chain");
            return;
        }

        console.log("=== Withdrawing from Previous Vault ===");
        console.log("Previous Vault:", previousVault);

        // Check if previous vault exists (has code)
        if (previousVault.code.length == 0) {
            console.log("Previous vault not deployed on this chain, skipping withdrawal");
            return;
        }

        CrossChainVaultV25 oldVault = CrossChainVaultV25(payable(previousVault));
        string memory chainName = getChainName(block.chainid);

        // Check balances
        uint256 collateralBalance;
        uint256 suppliedBalance;

        try oldVault.userCollateralByChain(deployer, chainName) returns (uint256 balance) {
            collateralBalance = balance;
        } catch {
            console.log("Could not read collateral balance (might be 0 or incompatible)");
        }

        try oldVault.userSuppliedByChain(deployer, chainName) returns (uint256 balance) {
            suppliedBalance = balance;
        } catch {
            console.log("Could not read supplied balance (might be 0 or incompatible)");
        }

        console.log("Collateral Balance:", collateralBalance);
        console.log("Supplied Balance:", suppliedBalance);

        if (collateralBalance == 0 && suppliedBalance == 0) {
            console.log("No funds to withdraw, proceeding with deployment");
            return;
        }

        vm.startBroadcast(privateKey);

        // Withdraw collateral
        if (collateralBalance > 0) {
            console.log("Withdrawing collateral...");
            try oldVault.withdrawCollateral(deployer, collateralBalance, 0.01 ether) {
                console.log("Collateral withdrawn successfully");
            } catch Error(string memory reason) {
                console.log("Collateral withdrawal failed:", reason);
                console.log("Continuing with deployment anyway...");
            } catch {
                console.log("Collateral withdrawal failed (unknown error)");
                console.log("Continuing with deployment anyway...");
            }
        }

        // Withdraw supplied funds
        if (suppliedBalance > 0) {
            console.log("Withdrawing supplied funds...");
            try oldVault.withdrawSupplied(suppliedBalance, 0.01 ether) {
                console.log("Supplied funds withdrawn successfully");
            } catch Error(string memory reason) {
                console.log("Supplied withdrawal failed:", reason);
                console.log("Continuing with deployment anyway...");
            } catch {
                console.log("Supplied withdrawal failed (unknown error)");
                console.log("Continuing with deployment anyway...");
            }
        }

        vm.stopBroadcast();

        console.log("Withdrawal attempt complete");
    }

    function getChainName(uint256 chainId) internal pure returns (string memory) {
        if (chainId == 11155111) return "ethereum"; // Sepolia
        if (chainId == 80002) return "polygon"; // Amoy
        if (chainId == 421614) return "arbitrum"; // Arbitrum Sepolia
        if (chainId == 11155420) return "optimism"; // Optimism Sepolia
        if (chainId == 84532) return "base"; // Base Sepolia
        return "ethereum"; // Default
    }
}
