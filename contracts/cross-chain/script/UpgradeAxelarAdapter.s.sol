// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import {Script} from "forge-std/Script.sol";
import {console2} from "forge-std/console2.sol";
import {BridgeManager} from "../src/BridgeManager.sol";
import {AxelarAdapter} from "../src/adapters/AxelarAdapter.sol";

/**
 * @title UpgradeAxelarAdapter
 * @notice Deploy new AxelarAdapter V2 with chain name translation and update BridgeManager
 */
contract UpgradeAxelarAdapter is Script {
    // Deployed addresses (same on both chains thanks to CREATE2)
    address constant BRIDGE_MANAGER = 0xB700E59DD350D5C6648413F5eF2856467461120E;

    // Axelar addresses
    address constant AXELAR_GATEWAY = 0xe432150cce91c13a887f7D836923d5597adD8E31;
    address constant AXELAR_GAS_SERVICE = 0xbE406F0189A0B4cf3A05C286473D23791Dd44Cc6;

    // V2 salt (different from V1 to get new address)
    bytes32 constant AXELAR_ADAPTER_V2_SALT = keccak256("FusionPrime.AxelarAdapter.v2");

    function run() external returns (address) {
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");

        vm.startBroadcast(deployerPrivateKey);

        console2.log("====================================");
        console2.log("Upgrading AxelarAdapter to V2");
        console2.log("====================================");
        console2.log("Chain ID:", block.chainid);
        console2.log("");

        // Deploy new AxelarAdapter V2 with chain name translation
        string[] memory supportedChains = new string[](3);
        supportedChains[0] = "ethereum";
        supportedChains[1] = "polygon";
        supportedChains[2] = "arbitrum";

        console2.log(">>> Deploying AxelarAdapter V2 with CREATE2...");
        bytes memory bytecode = abi.encodePacked(
            type(AxelarAdapter).creationCode,
            abi.encode(AXELAR_GATEWAY, AXELAR_GAS_SERVICE, supportedChains)
        );

        bytes32 salt = AXELAR_ADAPTER_V2_SALT;
        address axelarAdapterV2;
        assembly {
            axelarAdapterV2 := create2(0, add(bytecode, 32), mload(bytecode), salt)
            if iszero(axelarAdapterV2) {
                revert(0, 0)
            }
        }
        console2.log("AxelarAdapter V2 deployed at:", axelarAdapterV2);

        // Register new adapter with BridgeManager
        console2.log(">>> Registering AxelarAdapter V2 with BridgeManager...");
        BridgeManager bridgeManager = BridgeManager(BRIDGE_MANAGER);
        bridgeManager.registerAdapter(AxelarAdapter(axelarAdapterV2));
        console2.log("Adapter registered");

        // Update protocol preferences to use V2
        console2.log(">>> Updating protocol preferences to use V2...");
        bridgeManager.setPreferredProtocol("ethereum", "axelar");
        bridgeManager.setPreferredProtocol("polygon", "axelar");
        bridgeManager.setPreferredProtocol("arbitrum", "axelar");
        console2.log("Protocol preferences updated");

        console2.log("");
        console2.log("====================================");
        console2.log("Upgrade Complete");
        console2.log("====================================");
        console2.log("AxelarAdapter V2:", axelarAdapterV2);
        console2.log("");
        console2.log("V2 now translates chain names:");
        console2.log("  ethereum -> Ethereum");
        console2.log("  polygon -> Polygon");
        console2.log("  arbitrum -> arbitrum-sepolia");

        vm.stopBroadcast();

        return axelarAdapterV2;
    }
}
