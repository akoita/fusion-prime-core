// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import {Script, console2} from "forge-std/Script.sol";
import {CrossChainVault} from "../src/CrossChainVault.sol";
import {BridgeManager} from "../src/BridgeManager.sol";
import {MessageBridgeAdapter} from "../src/adapters/MessageBridgeAdapter.sol";

/**
 * @title DeployVaultV21
 * @notice Deploys CrossChainVault V21 with MessageBridge integration
 * @dev V21 uses custom MessageBridge instead of Axelar for:
 *      - Full control over cross-chain messaging
 *      - Zero external gas fees (only transaction costs)
 *      - Instant message execution via relayer
 *      - Better reliability than testnet Axelar
 *
 * Prerequisites:
 *   - MessageBridge deployed on both chains
 *   - MessageBridgeAdapter deployed on both chains
 *   - Network pairs configured in BridgeRegistry
 *
 * Usage:
 *   # Deploy on Sepolia
 *   DEPLOYER_PRIVATE_KEY=<key> forge script script/DeployVaultV21.s.sol:DeployVaultV21 \
 *     --rpc-url https://sepolia.infura.io/v3/YOUR_KEY \
 *     --broadcast --verify
 *
 *   # Deploy on Amoy
 *   DEPLOYER_PRIVATE_KEY=<key> forge script script/DeployVaultV21.s.sol:DeployVaultV21 \
 *     --rpc-url https://polygon-amoy.infura.io/v3/YOUR_KEY \
 *     --broadcast --verify
 */
contract DeployVaultV21 is Script {
    // MessageBridge addresses (from DEPLOYMENT_ADDRESSES.md)
    address constant SEPOLIA_MESSAGE_BRIDGE = 0xd04ef4fb6f49850c9Bf3D48666ec5Af10b0EFa2C;
    address constant AMOY_MESSAGE_BRIDGE = 0x5e67D35a38E2BCBD76e56729A8AFC78Ef8A5bDB2;

    // MessageBridgeAdapter addresses
    address constant SEPOLIA_ADAPTER = 0xD9AA2c78Ae73c0DEc20D8e71923eF28d2A522075;
    address constant AMOY_ADAPTER = 0xC435c5E43d4A25824eAcFc6a1F148c92B59c97De;

    // Axelar/CCIP addresses (still required by constructor but won't be used)
    address constant AXELAR_GATEWAY = 0xe432150cce91c13a887f7D836923d5597adD8E31;  // Same on both testnets
    address constant CCIP_ROUTER_SEPOLIA = 0x0BF3dE8c5D3e8A2B34D2BEeB17ABfCeBaf363A59;
    address constant CCIP_ROUTER_AMOY = 0x9C32fCB86BF0f4a1A8921a9Fe46de3198bb884B2;

    function run() external {
        uint256 deployerKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        vm.startBroadcast(deployerKey);

        // Determine current chain
        uint256 chainId = block.chainid;
        console2.log("Deploying V21 on chain:", chainId);

        address messageBridgeAdapter;
        address ccipRouter;
        string memory networkName;

        if (chainId == 11155111) {
            // Sepolia
            messageBridgeAdapter = SEPOLIA_ADAPTER;
            ccipRouter = CCIP_ROUTER_SEPOLIA;
            networkName = "Ethereum Sepolia";
            console2.log("Network:", networkName);
            console2.log("MessageBridge:", SEPOLIA_MESSAGE_BRIDGE);
        } else if (chainId == 80002) {
            // Polygon Amoy
            messageBridgeAdapter = AMOY_ADAPTER;
            ccipRouter = CCIP_ROUTER_AMOY;
            networkName = "Polygon Amoy";
            console2.log("Network:", networkName);
            console2.log("MessageBridge:", AMOY_MESSAGE_BRIDGE);
        } else {
            revert("Unsupported chain");
        }

        // Create deterministic salt for CREATE2 deployment
        // V21: MessageBridge integration
        bytes32 salt = keccak256("CrossChainVault-V21-MessageBridge");

        // Step 1: Deploy BridgeManager
        console2.log("\nStep 1: Deploying BridgeManager...");
        BridgeManager bridgeManager = new BridgeManager{salt: salt}();
        console2.log("BridgeManager deployed at:", address(bridgeManager));

        // Step 2: Register MessageBridgeAdapter as the only protocol
        console2.log("\nStep 2: Registering MessageBridgeAdapter...");
        console2.log("Adapter address:", messageBridgeAdapter);

        // Create a new instance to register (pre-deployed adapters)
        MessageBridgeAdapter adapter = MessageBridgeAdapter(messageBridgeAdapter);
        bridgeManager.registerAdapter(adapter);

        // Set MessageBridge as preferred protocol for all chains
        bridgeManager.setPreferredProtocol("ethereum", "messagebridge");
        bridgeManager.setPreferredProtocol("polygon", "messagebridge");
        console2.log("MessageBridge set as default protocol");

        // Step 3: Deploy CrossChainVault
        console2.log("\nStep 3: Deploying CrossChainVault...");
        string[] memory supportedChains = new string[](2);
        supportedChains[0] = "ethereum";
        supportedChains[1] = "polygon";

        CrossChainVault vault = new CrossChainVault{salt: salt}(
            address(bridgeManager),
            AXELAR_GATEWAY,  // Required by constructor but MessageBridge will be used instead
            ccipRouter,      // Required by constructor but MessageBridge will be used instead
            supportedChains
        );
        console2.log("CrossChainVault deployed at:", address(vault));

        // Display deployment summary
        console2.log("\n================================================");
        console2.log("V21 Deployment Complete");
        console2.log("================================================");
        console2.log("Network:", networkName);
        console2.log("Chain ID:", chainId);
        console2.log("BridgeManager:", address(bridgeManager));
        console2.log("MessageBridgeAdapter:", messageBridgeAdapter);
        console2.log("CrossChainVault:", address(vault));
        console2.log("================================================");
        console2.log("\nV21 Features:");
        console2.log("- Custom MessageBridge (no Axelar/CCIP)");
        console2.log("- Zero external gas fees");
        console2.log("- Instant relayer execution");
        console2.log("- Full control over messaging");
        console2.log("\nNext steps:");
        console2.log("1. Deploy on the other chain");
        console2.log("2. Configure trustedVaults on both chains");
        console2.log("3. Start the relayer service");
        console2.log("4. Test deposit and sync flow");

        vm.stopBroadcast();
    }
}
