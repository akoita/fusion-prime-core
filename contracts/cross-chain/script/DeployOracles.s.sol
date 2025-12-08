// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/oracles/ChainlinkPriceOracle.sol";

/**
 * @title DeployOracles
 * @notice Deploy Chainlink price oracles for Sepolia and Amoy
 *
 * Usage:
 * # Deploy on Sepolia
 * PRIVATE_KEY=<key> forge script script/DeployOracles.s.sol:DeployOracles \
 *   --rpc-url https://sepolia.infura.io/v3/YOUR_KEY \
 *   --broadcast
 *
 * # Deploy on Amoy
 * PRIVATE_KEY=<key> forge script script/DeployOracles.s.sol:DeployOracles \
 *   --rpc-url https://polygon-amoy.infura.io/v3/YOUR_KEY \
 *   --broadcast
 */
contract DeployOracles is Script {
    // Chainlink Price Feed addresses
    address constant SEPOLIA_ETH_USD = 0x694AA1769357215DE4FAC081bf1f309aDC325306;
    address constant AMOY_MATIC_USD = 0x001382149eBa3441043c1c66972b4772963f5D43;

    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);

        console.log("Deploying oracles with deployer:", deployer);
        console.log("Chain ID:", block.chainid);

        vm.startBroadcast(deployerPrivateKey);

        ChainlinkPriceOracle oracle;

        if (block.chainid == 11155111) {
            // Sepolia
            console.log("Deploying Sepolia ETH/USD oracle...");
            oracle = new ChainlinkPriceOracle(SEPOLIA_ETH_USD);
            console.log("Sepolia Oracle deployed at:", address(oracle));

            // Test price feed
            uint256 price = oracle.getNativePrice();
            console.log("Current ETH price (8 decimals):", price);
            console.log("Current ETH price in USD:", price / 1e8);

            // Test conversion
            uint256 oneEth = 1 ether;
            uint256 usdValue = oracle.convertToUSD(oneEth);
            console.log("1 ETH in USD (18 decimals):", usdValue / 1e18);

        } else if (block.chainid == 80002) {
            // Amoy
            console.log("Deploying Amoy MATIC/USD oracle...");
            oracle = new ChainlinkPriceOracle(AMOY_MATIC_USD);
            console.log("Amoy Oracle deployed at:", address(oracle));

            // Test price feed
            uint256 price = oracle.getNativePrice();
            console.log("Current MATIC price (8 decimals):", price);
            console.log("Current MATIC price in USD:", price / 1e8);

            // Test conversion
            uint256 oneMatic = 1 ether;
            uint256 usdValue = oracle.convertToUSD(oneMatic);
            console.log("1 MATIC in USD (18 decimals):", usdValue / 1e18);

        } else {
            revert("Unsupported chain ID");
        }

        vm.stopBroadcast();

        console.log("\n=== Deployment Summary ===");
        console.log("Oracle Address:", address(oracle));
        console.log("Owner:", oracle.owner());
        console.log("\nNext steps:");
        console.log("1. Save oracle address to .env file");
        console.log("2. Update CrossChainVault to use this oracle");
        console.log("3. Test price feeds are working correctly");
    }
}
