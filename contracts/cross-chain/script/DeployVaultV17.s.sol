// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import {Script} from "forge-std/Script.sol";
import {console2} from "forge-std/console2.sol";
import {CrossChainVault} from "../src/CrossChainVault.sol";
import {BridgeManager} from "../src/BridgeManager.sol";
import {CCIPAdapter} from "../src/adapters/CCIPAdapter.sol";
import {VaultFactory} from "../src/VaultFactory.sol";

/**
 * @title DeployVaultV17
 * @notice Deploy V17 with ALL CCIP encoding fixes
 * @dev Critical fixes:
 *      1. Sender decoding: Use bytes20 cast for 20-byte packed address (V16)
 *      2. Receiver encoding: Use abi.encodePacked (20 bytes) not abi.encode (32 bytes)
 *      3. Protocol preference: Set CCIP as preferred protocol for routing
 */
contract DeployVaultV17 is Script {
    // CCIP Router addresses for SENDING (used by CCIPAdapter)
    address constant SEPOLIA_CCIP_ROUTER_SEND = 0x0BF3dE8c5D3e8A2B34D2BEeB17ABfCeBaf363A59;
    address constant AMOY_CCIP_ROUTER_SEND = 0x9C32fCB86BF0f4a1A8921a9Fe46de3198bb884B2;

    // CCIP OffRamp addresses for RECEIVING (used by CrossChainVault for ccipReceive auth)
    address constant SEPOLIA_CCIP_OFFRAMP = 0x0BF3dE8c5D3e8A2B34D2BEeB17ABfCeBaf363A59;
    address constant AMOY_CCIP_OFFRAMP = 0x7Ad494C173f5845c6B4028a06cDcC6d3108bc960;

    // CCIP Chain Selectors
    uint64 constant SEPOLIA_SELECTOR = 16015286601757825753;
    uint64 constant AMOY_SELECTOR = 16281711391670634445;

    function run() external {
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        vm.startBroadcast(deployerPrivateKey);

        console2.log("====================================");
        console2.log("Deploying V17 - ALL CCIP Fixes");
        console2.log("====================================");
        console2.log("Chain ID:", block.chainid);

        address ccipRouterForSending;
        address ccipOffRampForReceiving;
        uint64 destinationChainSelector;
        string memory destinationChainName;

        if (block.chainid == 11155111) {
            // Sepolia
            ccipRouterForSending = SEPOLIA_CCIP_ROUTER_SEND;
            ccipOffRampForReceiving = SEPOLIA_CCIP_OFFRAMP;
            destinationChainSelector = AMOY_SELECTOR;
            destinationChainName = "polygon";
            console2.log("Deploying on Sepolia");
        } else if (block.chainid == 80002) {
            // Polygon Amoy
            ccipRouterForSending = AMOY_CCIP_ROUTER_SEND;
            ccipOffRampForReceiving = AMOY_CCIP_OFFRAMP;
            destinationChainSelector = SEPOLIA_SELECTOR;
            destinationChainName = "ethereum";
            console2.log("Deploying on Polygon Amoy");
        } else {
            revert("Unsupported chain");
        }

        // 1. Deploy BridgeManager
        console2.log("\n--- Step 1: Deploy BridgeManager ---");
        BridgeManager bridgeManager = new BridgeManager();
        console2.log("BridgeManager deployed:", address(bridgeManager));

        // 2. Deploy CCIPAdapter with Router address (for sending)
        console2.log("\n--- Step 2: Deploy CCIPAdapter ---");
        uint64[] memory chainSelectors = new uint64[](1);
        string[] memory chainNames = new string[](1);
        chainSelectors[0] = destinationChainSelector;
        chainNames[0] = destinationChainName;

        CCIPAdapter ccipAdapter = new CCIPAdapter(ccipRouterForSending, chainSelectors, chainNames);
        console2.log("CCIPAdapter deployed:", address(ccipAdapter));
        console2.log("  - Uses abi.encodePacked for receiver (20 bytes)");
        console2.log("  - Gas limit: 200k");

        // 3. Register CCIPAdapter with BridgeManager
        console2.log("\n--- Step 3: Register Adapter ---");
        bridgeManager.registerAdapter(ccipAdapter);
        console2.log("CCIPAdapter registered");

        // 3b. Set CCIP as preferred protocol (CRITICAL FIX)
        console2.log("\n--- Step 3b: Set Preferred Protocol ---");
        bridgeManager.setPreferredProtocol(destinationChainName, "ccip");
        console2.log("Preferred protocol set: ccip for", destinationChainName);

        // 4. Deploy CrossChainVault with OffRamp address (for receiving)
        console2.log("\n--- Step 4: Deploy CrossChainVault ---");

        string[] memory supportedChains = new string[](1);
        supportedChains[0] = destinationChainName;

        VaultFactory factory = new VaultFactory();
        console2.log("VaultFactory deployed:", address(factory));

        bytes32 salt = keccak256("CrossChainVault-V17");
        address predictedVault = factory.computeVaultAddress(
            address(bridgeManager),
            address(0), // No Axelar
            ccipOffRampForReceiving,
            supportedChains,
            salt
        );
        console2.log("Predicted vault:", predictedVault);

        address vault = factory.deployVault(
            address(bridgeManager),
            address(0), // No Axelar
            ccipOffRampForReceiving,
            supportedChains,
            salt
        );
        console2.log("CrossChainVault deployed:", vault);
        console2.log("  - Uses bytes20 cast for sender (20 bytes)");
        require(vault == predictedVault, "Vault address mismatch");

        vm.stopBroadcast();

        console2.log("\n====================================");
        console2.log("V17 Deployment Complete!");
        console2.log("====================================");
        console2.log("BridgeManager:", address(bridgeManager));
        console2.log("CCIPAdapter:", address(ccipAdapter));
        console2.log("CrossChainVault:", vault);
        console2.log("");
        console2.log("ALL FIXES APPLIED:");
        console2.log("  1. Receiver: abi.encodePacked (20 bytes)");
        console2.log("  2. Sender: bytes20 cast (20 bytes)");
        console2.log("  3. Protocol: ccip preferred for", destinationChainName);
        console2.log("  4. Gas limit: 200k");
    }
}
