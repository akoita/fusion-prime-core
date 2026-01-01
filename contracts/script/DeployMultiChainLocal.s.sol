// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import "forge-std/Script.sol";
import {CrossChainVault} from "../src/CrossChainVault.sol";
import {InterestRateModel} from "../src/InterestRateModel.sol";
import {MockPriceOracle} from "../test/mocks/MockPriceOracle.sol";
import {MockAxelarGateway} from "../test/mocks/MockAxelarGateway.sol";
import {MockAxelarGasService} from "../test/mocks/MockAxelarGasService.sol";
import {MockUSDC} from "../test/mocks/MockUSDC.sol";

/**
 * @title DeployMultiChainLocal
 * @notice Deployment script for CrossChainVaultV31 on local multi-chain Anvil setup
 *
 * Deploys:
 * - MockPriceOracle
 * - MockAxelarGateway & MockAxelarGasService
 * - InterestRateModel
 * - CrossChainVault
 * - MockUSDC (test token)
 *
 * Usage (per chain):
 *   PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
 *   forge script script/DeployMultiChainLocal.s.sol:DeployMultiChainLocal \
 *     --rpc-url http://127.0.0.1:31447 \
 *     --broadcast
 */
contract DeployMultiChainLocal is Script {
    // Collateral factors (basis points)
    uint256 constant USDC_FACTOR = 9000; // 90%

    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);
        uint256 chainId = block.chainid;

        vm.startBroadcast(deployerPrivateKey);

        console.log("===============================================");
        console.log("Deploying CrossChainVault to Chain ID:", chainId);
        console.log("Deployer:", deployer);
        console.log("===============================================");

        // 1. Deploy Mock Price Oracle
        MockPriceOracle oracle = new MockPriceOracle();
        console.log("MockPriceOracle:", address(oracle));

        // 2. Deploy Interest Rate Model
        InterestRateModel rateModel = new InterestRateModel();
        console.log("InterestRateModel:", address(rateModel));

        // 3. Deploy Mock Axelar contracts
        MockAxelarGateway gateway = new MockAxelarGateway();
        console.log("MockAxelarGateway:", address(gateway));
        MockAxelarGasService gasService = new MockAxelarGasService();
        console.log("MockAxelarGasService:", address(gasService));

        // 4. Deploy CrossChainVault
        CrossChainVault vault = new CrossChainVault(
            address(gateway),
            address(gasService),
            address(oracle),
            address(rateModel)
        );
        console.log("CrossChainVault:", address(vault));

        // 5. Deploy MockUSDC
        MockUSDC usdc = new MockUSDC();
        console.log("MockUSDC:", address(usdc));

        // 6. Configure oracle with USDC price ($1)
        oracle.addToken(address(usdc), 1 * 10 ** 8, 6); // $1 with 8 decimals, 6 token decimals
        console.log("Oracle configured: USDC = $1");

        // 7. Add USDC as supported token in vault
        vault.addToken(address(usdc), USDC_FACTOR);
        console.log("USDC added to vault with 90% collateral factor");

        // 8. Add a trusted issuer for KYC (test address)
        address testIssuer = address(0x100);
        vault.addTrustedIssuer(testIssuer);
        console.log("Test issuer added:", testIssuer);

        // 9. Provide USDC liquidity
        uint256 liquidityAmount = 1_000_000 * 10 ** 6; // 1M USDC
        usdc.mint(deployer, liquidityAmount);
        usdc.approve(address(vault), liquidityAmount);
        vault.depositToken(address(usdc), liquidityAmount);
        console.log("Deposited 1,000,000 USDC liquidity to vault");

        vm.stopBroadcast();

        // Output JSON-formatted addresses for test consumption
        console.log("\n--- DEPLOYMENT JSON START ---");
        console.log("{");
        console.log('  "chainId":', chainId, ",");
        console.log('  "vault": "', address(vault), '",');
        console.log('  "oracle": "', address(oracle), '",');
        console.log('  "rateModel": "', address(rateModel), '",');
        console.log('  "gateway": "', address(gateway), '",');
        console.log('  "gasService": "', address(gasService), '",');
        console.log('  "usdc": "', address(usdc), '"');
        console.log("}");
        console.log("--- DEPLOYMENT JSON END ---");
    }
}
