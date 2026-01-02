// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import "forge-std/Script.sol";
import {CrossChainVault} from "lending/CrossChainVault.sol";
import {InterestRateModel} from "lending/InterestRateModel.sol";
import {MockPriceOracle} from "../test/mocks/MockPriceOracle.sol";
import {MockAxelarGateway} from "../test/mocks/MockAxelarGateway.sol";
import {MockAxelarGasService} from "../test/mocks/MockAxelarGasService.sol";
import {MockUSDC} from "../test/mocks/MockUSDC.sol";

/**
 * @title DeployVaultLocal
 * @notice Deployment script for CrossChainVault on local Anvil
 *
 * Deploys:
 * - MockPriceOracle (configurable prices)
 * - MockAxelarGateway & MockAxelarGasService
 * - InterestRateModel
 * - CrossChainVault
 * - MockUSDC (test token)
 *
 * Usage:
 *   anvil &
 *   forge script script/DeployVaultLocal.s.sol:DeployVaultLocal \
 *     --rpc-url http://127.0.0.1:8545 \
 *     --broadcast \
 *     --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
 */
contract DeployVaultLocal is Script {
    // Collateral factors (basis points)
    uint256 constant USDC_FACTOR = 9000; // 90%

    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");

        vm.startBroadcast(deployerPrivateKey);

        console.log("Deploying to local Anvil...");
        console.log("Deployer:", msg.sender);

        // 1. Deploy Mock Price Oracle
        console.log("\n1. Deploying MockPriceOracle...");
        MockPriceOracle oracle = new MockPriceOracle();
        console.log("   MockPriceOracle:", address(oracle));

        // 2. Deploy Interest Rate Model
        console.log("\n2. Deploying InterestRateModel...");
        InterestRateModel rateModel = new InterestRateModel();
        console.log("   InterestRateModel:", address(rateModel));

        // 3. Deploy Mock Axelar contracts
        console.log("\n3. Deploying Mock Axelar contracts...");
        MockAxelarGateway gateway = new MockAxelarGateway();
        console.log("   MockAxelarGateway:", address(gateway));
        MockAxelarGasService gasService = new MockAxelarGasService();
        console.log("   MockAxelarGasService:", address(gasService));

        // 4. Deploy CrossChainVault
        console.log("\n4. Deploying CrossChainVault...");
        CrossChainVault vault = new CrossChainVault(
            address(gateway),
            address(gasService),
            address(oracle),
            address(rateModel)
        );
        console.log("   CrossChainVault:", address(vault));

        // 5. Deploy MockUSDC
        console.log("\n5. Deploying MockUSDC...");
        MockUSDC usdc = new MockUSDC();
        console.log("   MockUSDC:", address(usdc));

        // 6. Configure oracle with USDC price ($1)
        console.log("\n6. Configuring MockPriceOracle...");
        oracle.addToken(address(usdc), 1 * 10 ** 8, 6); // $1 with 8 decimals, 6 token decimals
        console.log("   USDC price set to $1");

        // 7. Add USDC as supported token in vault
        console.log("\n7. Adding USDC to vault...");
        vault.addToken(address(usdc), USDC_FACTOR);
        console.log("   USDC added with 90% collateral factor");

        // 8. Provide USDC liquidity via depositToken (so totalDeposited is updated)
        console.log("\n8. Providing USDC liquidity to vault...");
        uint256 liquidityAmount = 1_000_000 * 10 ** 6; // 1M USDC
        address deployer = vm.addr(deployerPrivateKey);
        usdc.mint(deployer, liquidityAmount);
        usdc.approve(address(vault), liquidityAmount);
        vault.depositToken(address(usdc), liquidityAmount);
        console.log("   Deposited 1,000,000 USDC liquidity to vault");

        vm.stopBroadcast();

        // Summary
        console.log("\n========== DEPLOYMENT SUMMARY (Local) ==========");
        console.log("MockPriceOracle:      ", address(oracle));
        console.log("InterestRateModel:    ", address(rateModel));
        console.log("MockAxelarGateway:    ", address(gateway));
        console.log("MockAxelarGasService: ", address(gasService));
        console.log("CrossChainVault:      ", address(vault));
        console.log("MockUSDC:             ", address(usdc));
        console.log("");
        console.log("Default prices:");
        console.log("  - ETH/USD: $2000");
        console.log("  - USDC/USD: $1");
        console.log("================================================");

        // Export addresses for Python tests
        console.log("\n# Export for Python tests:");
        console.log("export VAULT_ADDRESS=", address(vault));
        console.log("export USDC_ADDRESS=", address(usdc));
        console.log("export ORACLE_ADDRESS=", address(oracle));
    }
}
