// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.30;

import "forge-std/Script.sol";
import "../src/CrossChainVaultV24.sol";

/**
 * @title DeployVaultV24
 * @notice Deploys CrossChainVaultV24 with Chainlink oracle integration
 * @dev Usage:
 *   PRIVATE_KEY=<key> forge script script/DeployVaultV24.s.sol:DeployVaultV24 \
 *     --rpc-url <rpc-url> --broadcast
 */
contract DeployVaultV24 is Script {
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

        console.log("Deploying CrossChainVaultV24 with deployer:", deployer);
        console.log("Chain ID:", block.chainid);

        vm.startBroadcast(deployerPrivateKey);

        CrossChainVaultV24 vault;

        if (block.chainid == 11155111) {
            // Sepolia deployment
            console.log("Deploying on Sepolia...");
            console.log("BridgeManager:", SEPOLIA_BRIDGE_MANAGER);
            console.log("Axelar Gateway:", SEPOLIA_AXELAR_GATEWAY);
            console.log("CCIP Router:", SEPOLIA_CCIP_ROUTER);

            string[] memory supportedChains = new string[](2);
            supportedChains[0] = "ethereum";
            supportedChains[1] = "polygon";

            address[] memory oracles = new address[](2);
            oracles[0] = SEPOLIA_ORACLE; // Sepolia ETH/USD
            oracles[1] = AMOY_ORACLE;    // Amoy MATIC/USD (for cross-chain reference)

            vault = new CrossChainVaultV24(
                SEPOLIA_BRIDGE_MANAGER,
                SEPOLIA_AXELAR_GATEWAY,
                SEPOLIA_CCIP_ROUTER,
                supportedChains,
                oracles
            );

            console.log("\n=== Sepolia Deployment ===");
            console.log("CrossChainVaultV24:", address(vault));
            console.log("ETH/USD Oracle:", SEPOLIA_ORACLE);
            console.log("MATIC/USD Oracle (reference):", AMOY_ORACLE);

        } else if (block.chainid == 80002) {
            // Amoy deployment
            console.log("Deploying on Amoy...");
            console.log("BridgeManager:", AMOY_BRIDGE_MANAGER);
            console.log("Axelar Gateway:", AMOY_AXELAR_GATEWAY);
            console.log("CCIP Router:", AMOY_CCIP_ROUTER);

            string[] memory supportedChains = new string[](2);
            supportedChains[0] = "ethereum";
            supportedChains[1] = "polygon";

            address[] memory oracles = new address[](2);
            oracles[0] = SEPOLIA_ORACLE; // Sepolia ETH/USD (for cross-chain reference)
            oracles[1] = AMOY_ORACLE;    // Amoy MATIC/USD

            vault = new CrossChainVaultV24(
                AMOY_BRIDGE_MANAGER,
                AMOY_AXELAR_GATEWAY,
                AMOY_CCIP_ROUTER,
                supportedChains,
                oracles
            );

            console.log("\n=== Amoy Deployment ===");
            console.log("CrossChainVaultV24:", address(vault));
            console.log("ETH/USD Oracle (reference):", SEPOLIA_ORACLE);
            console.log("MATIC/USD Oracle:", AMOY_ORACLE);

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
            console.log("   - On Sepolia: setTrustedVault('polygon', <amoy-vault-address>)");
        } else {
            console.log("   - On Amoy: setTrustedVault('ethereum', <sepolia-vault-address>)");
        }
        console.log("4. Test USD valuations with getUserSummaryUSD()");
        console.log("5. Test cross-chain deposits and borrowing");
    }
}
