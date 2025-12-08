// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.30;

import "forge-std/Script.sol";
import "../src/CrossChainVaultV25.sol";

/**
 * @title DeployVaultV25
 * @notice Deploys CrossChainVaultV25 with supply/lend mechanism and interest rates
 * @dev Usage:
 *   PRIVATE_KEY=<key> forge script script/DeployVaultV25.s.sol:DeployVaultV25 \
 *     --rpc-url <rpc-url> --broadcast
 */
contract DeployVaultV25 is Script {
    // BridgeManager addresses (from previous deployments)
    address constant SEPOLIA_BRIDGE_MANAGER = 0xA8d853C5b945924d217Ec4119E9f0e2eFf714B8a;
    address constant AMOY_BRIDGE_MANAGER = 0xEEcd2114162D577c4668B8e92a6FB34d0eA6A149;

    // Axelar Gateway addresses
    address constant SEPOLIA_AXELAR_GATEWAY = 0xe432150cce91c13a887f7D836923d5597adD8E31;
    address constant AMOY_AXELAR_GATEWAY = 0x2A723E9BBD44C27A0F0FC13f46C41Ab59EDdd6E8;

    // CCIP Router addresses
    address constant SEPOLIA_CCIP_ROUTER = 0x0BF3dE8c5D3e8A2B34D2BEeB17ABfCeBaf363A59;
    address constant AMOY_CCIP_ROUTER = 0x9C32fCB86BF0f4a1A8921a9Fe46de3198bb884B2;

    // Chainlink Oracle addresses (deployed earlier)
    address constant SEPOLIA_ORACLE = 0x184e08394672B9Bf7aE670A3867C3c97A67A4e5C;
    address constant AMOY_ORACLE = 0x895c8848429745221d540366BC7aFCD0A7AFE3bF;

    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);

        console.log("Deploying CrossChainVaultV25 with deployer:", deployer);
        console.log("Chain ID:", block.chainid);

        vm.startBroadcast(deployerPrivateKey);

        CrossChainVaultV25 vault;

        if (block.chainid == 11155111) {
            // Sepolia deployment
            console.log("\n=== Deploying on Sepolia ===");
            console.log("BridgeManager:", SEPOLIA_BRIDGE_MANAGER);
            console.log("Axelar Gateway:", SEPOLIA_AXELAR_GATEWAY);
            console.log("CCIP Router:", SEPOLIA_CCIP_ROUTER);

            string[] memory supportedChains = new string[](2);
            supportedChains[0] = "ethereum";
            supportedChains[1] = "polygon";

            address[] memory oracles = new address[](2);
            oracles[0] = SEPOLIA_ORACLE; // Sepolia ETH/USD
            oracles[1] = AMOY_ORACLE;    // Amoy MATIC/USD (for cross-chain reference)

            vault = new CrossChainVaultV25(
                SEPOLIA_BRIDGE_MANAGER,
                SEPOLIA_AXELAR_GATEWAY,
                SEPOLIA_CCIP_ROUTER,
                supportedChains,
                oracles
            );

            console.log("\n=== Sepolia Deployment Complete ===");
            console.log("CrossChainVaultV25:", address(vault));
            console.log("ETH/USD Oracle:", SEPOLIA_ORACLE);
            console.log("MATIC/USD Oracle (reference):", AMOY_ORACLE);

            // Display interest rate parameters
            console.log("\n=== Interest Rate Configuration ===");
            console.log("Base APY: 2%");
            console.log("Slope: 10%");
            console.log("Borrow Multiplier: 1.2x");
            console.log("Example APYs at different utilization:");
            console.log("  0% utilization: Supply 2%, Borrow 2.4%");
            console.log(" 50% utilization: Supply 7%, Borrow 8.4%");
            console.log("100% utilization: Supply 12%, Borrow 14.4%");

        } else if (block.chainid == 80002) {
            // Amoy deployment
            console.log("\n=== Deploying on Amoy ===");
            console.log("BridgeManager:", AMOY_BRIDGE_MANAGER);
            console.log("Axelar Gateway:", AMOY_AXELAR_GATEWAY);
            console.log("CCIP Router:", AMOY_CCIP_ROUTER);

            string[] memory supportedChains = new string[](2);
            supportedChains[0] = "ethereum";
            supportedChains[1] = "polygon";

            address[] memory oracles = new address[](2);
            oracles[0] = SEPOLIA_ORACLE; // Sepolia ETH/USD (for cross-chain reference)
            oracles[1] = AMOY_ORACLE;    // Amoy MATIC/USD

            vault = new CrossChainVaultV25(
                AMOY_BRIDGE_MANAGER,
                AMOY_AXELAR_GATEWAY,
                AMOY_CCIP_ROUTER,
                supportedChains,
                oracles
            );

            console.log("\n=== Amoy Deployment Complete ===");
            console.log("CrossChainVaultV25:", address(vault));
            console.log("ETH/USD Oracle (reference):", SEPOLIA_ORACLE);
            console.log("MATIC/USD Oracle:", AMOY_ORACLE);

            // Display interest rate parameters
            console.log("\n=== Interest Rate Configuration ===");
            console.log("Base APY: 2%");
            console.log("Slope: 10%");
            console.log("Borrow Multiplier: 1.2x");
            console.log("Example APYs at different utilization:");
            console.log("  0% utilization: Supply 2%, Borrow 2.4%");
            console.log(" 50% utilization: Supply 7%, Borrow 8.4%");
            console.log("100% utilization: Supply 12%, Borrow 14.4%");

        } else {
            revert("Unsupported chain");
        }

        vm.stopBroadcast();

        // Display next steps
        console.log("\n=== Next Steps ===");
        console.log("1. Save vault address to .env file");
        console.log("2. Deploy vault on the other chain");
        console.log("3. Configure trusted vaults:");
        if (block.chainid == 11155111) {
            console.log("   - On Sepolia: cast send <vault> 'setTrustedVault(string,address)' 'polygon' <amoy-vault-address> --private-key $PRIVATE_KEY");
        } else {
            console.log("   - On Amoy: cast send <vault> 'setTrustedVault(string,address)' 'ethereum' <sepolia-vault-address> --private-key $PRIVATE_KEY");
        }
        console.log("\n4. Test Supply/Lend Flow:");
        console.log("   - Supply liquidity: cast send <vault> 'supply(uint256)' 100000000000000 --value 110000000000000 --private-key $PRIVATE_KEY");
        console.log("   - Check APY: cast call <vault> 'getSupplyAPY(string)(uint256)' 'ethereum'");
        console.log("   - Check liquidity: cast call <vault> 'getAvailableLiquidity(string)(uint256)' 'ethereum'");
        console.log("\n5. Test Borrowing Against Liquidity:");
        console.log("   - Deposit collateral: cast send <vault> 'depositCollateral(address,uint256)' <user> 100000000000000 --value 200000000000000");
        console.log("   - Borrow: cast send <vault> 'borrow(uint256,uint256)' 50000000000000 100000000000000 --value 100000000000000");
        console.log("   - Check utilization: cast call <vault> 'getUtilizationRate(string)(uint256)' 'ethereum'");
        console.log("\n6. Test Interest Accrual:");
        console.log("   - Wait some time (or advance block.timestamp in tests)");
        console.log("   - Check balance with interest: cast call <vault> 'getSuppliedBalanceWithInterest(address,string)(uint256)' <user> 'ethereum'");
        console.log("\n7. Test Cross-Chain Features:");
        console.log("   - Supply on Sepolia, borrow on Amoy using the same credit line");
        console.log("   - Verify liquidity state syncs across chains");
    }
}
