// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "forge-std/Script.sol";
import "../src/CrossChainVaultV25.sol";

/**
 * @title EmergencyWithdrawAll
 * @notice TEMPORARY DEV TOOL - Withdraw all funds from a vault before redeployment
 * @dev This script allows the deployer/admin to recover testnet tokens during development
 *
 * WARNING: This is for TESTNET DEVELOPMENT ONLY
 * - Remove this script before mainnet deployment
 * - Only works if deployer has collateral in the vault
 *
 * Usage:
 *   forge script script/EmergencyWithdrawAll.s.sol:EmergencyWithdrawAll \
 *     --rpc-url $RPC_URL \
 *     --broadcast \
 *     --sig "run(address)" <VAULT_ADDRESS>
 *
 * Example (Sepolia):
 *   forge script script/EmergencyWithdrawAll.s.sol:EmergencyWithdrawAll \
 *     --rpc-url https://sepolia.infura.io/v3/YOUR_KEY \
 *     --broadcast \
 *     --sig "run(address)" 0x477f54284367CF31B2B7f6BB2Ca4291D3f43a312
 *
 * Example (Amoy):
 *   forge script script/EmergencyWithdrawAll.s.sol:EmergencyWithdrawAll \
 *     --rpc-url https://polygon-amoy.infura.io/v3/YOUR_KEY \
 *     --broadcast --legacy \
 *     --sig "run(address)" 0xbafd9d789f96d18cedd057899a4ba3273c9f6d0e
 */
contract EmergencyWithdrawAll is Script {
    function run(address vaultAddress) external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);

        CrossChainVaultV25 vault = CrossChainVaultV25(payable(vaultAddress));

        console.log("=== Emergency Withdrawal Tool ===");
        console.log("Vault Address:", vaultAddress);
        console.log("Deployer Address:", deployer);
        console.log("");

        // Get chain name
        string memory chainName = getChainName(block.chainid);
        console.log("Chain:", chainName);
        console.log("");

        // Check collateral balance
        uint256 collateralBalance;
        try vault.userCollateralByChain(deployer, chainName) returns (uint256 balance) {
            collateralBalance = balance;
            console.log("Collateral Balance:", collateralBalance);
        } catch {
            console.log("Could not read collateral balance (might be 0 or incompatible vault version)");
            collateralBalance = 0;
        }

        // Check supplied balance
        uint256 suppliedBalance;
        try vault.userSuppliedByChain(deployer, chainName) returns (uint256 balance) {
            suppliedBalance = balance;
            console.log("Supplied Balance:", suppliedBalance);
        } catch {
            console.log("Could not read supplied balance (might be 0 or incompatible vault version)");
            suppliedBalance = 0;
        }

        console.log("");

        if (collateralBalance == 0 && suppliedBalance == 0) {
            console.log("No funds to withdraw. Exiting.");
            return;
        }

        vm.startBroadcast(deployerPrivateKey);

        // Withdraw collateral if any
        if (collateralBalance > 0) {
            console.log("Withdrawing collateral:", collateralBalance);
            try vault.withdrawCollateral(deployer, collateralBalance, 0.01 ether) {
                console.log("Collateral withdrawn successfully");
            } catch Error(string memory reason) {
                console.log("Collateral withdrawal failed:", reason);
            } catch {
                console.log("Collateral withdrawal failed (unknown error)");
            }
        }

        // Withdraw supplied funds if any
        if (suppliedBalance > 0) {
            console.log("Withdrawing supplied funds:", suppliedBalance);
            try vault.withdrawSupplied(suppliedBalance, 0.01 ether) {
                console.log("Supplied funds withdrawn successfully");
            } catch Error(string memory reason) {
                console.log("Supplied withdrawal failed:", reason);
            } catch {
                console.log("Supplied withdrawal failed (unknown error)");
            }
        }

        vm.stopBroadcast();

        console.log("");
        console.log("Withdrawal complete!");
        console.log("Check your wallet for returned funds.");
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
