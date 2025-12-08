// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import {Script} from "forge-std/Script.sol";
import {console2} from "forge-std/console2.sol";
import {BridgeManager} from "../cross-chain/src/BridgeManager.sol";
import {AxelarAdapter} from "../cross-chain/src/adapters/AxelarAdapter.sol";

/**
 * @title FixAxelarChainNames
 * @notice Fix Axelar adapter chain names to use correct Axelar testnet identifiers
 * @dev Deploys new AxelarAdapter with correct chain names and updates BridgeManager
 *
 * Issue: AxelarAdapters were deployed with simplified chain names ("ethereum", "polygon")
 * Fix: Axelar Gateway requires testnet-specific names ("ethereum-sepolia", "polygon-sepolia")
 * Source: https://github.com/axelarnetwork/axelar-contract-deployments/blob/main/axelar-chains-config/info/testnet.json
 *
 * Usage on Sepolia:
 *   DEPLOYER_PRIVATE_KEY=0x... forge script script/FixAxelarChainNames.s.sol:FixAxelarChainNames \
 *     --rpc-url https://ethereum-sepolia-rpc.publicnode.com \
 *     --broadcast -vvv
 *
 * Usage on Amoy:
 *   DEPLOYER_PRIVATE_KEY=0x... forge script script/FixAxelarChainNames.s.sol:FixAxelarChainNames \
 *     --rpc-url https://rpc-amoy.polygon.technology \
 *     --broadcast -vvv
 */
contract FixAxelarChainNames is Script {
    // Existing deployed contracts
    // Sepolia
    address constant BRIDGE_MANAGER_SEPOLIA = 0xC96DA7e94E8407e0988bb60A1b23B9358Cd63A56;
    address constant AXELAR_GATEWAY_SEPOLIA = 0xe432150cce91c13a887f7D836923d5597adD8E31;
    address constant AXELAR_GAS_SERVICE_SEPOLIA = 0xbE406F0189A0B4cf3A05C286473D23791Dd44Cc6;

    // Amoy
    address constant BRIDGE_MANAGER_AMOY = 0x3481dbE036C0F4076B397e27FFb8dC32B88d8882;
    address constant AXELAR_GATEWAY_AMOY = 0xBF62eF1486468a6bD26DD669C06Db43De641D239;
    address constant AXELAR_GAS_SERVICE_AMOY = 0xbE406F0189A0B4cf3A05C286473D23791Dd44Cc6;

    function run() external {
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);
        uint256 chainId = block.chainid;

        console2.log("====================================");
        console2.log("Fix Axelar Chain Names");
        console2.log("====================================");
        console2.log("Deployer:", deployer);
        console2.log("Chain ID:", chainId);
        console2.log("");

        address bridgeManager;
        address gateway;
        address gasService;

        if (chainId == 11155111) {
            // Sepolia
            console2.log("Network: Ethereum Sepolia");
            bridgeManager = BRIDGE_MANAGER_SEPOLIA;
            gateway = AXELAR_GATEWAY_SEPOLIA;
            gasService = AXELAR_GAS_SERVICE_SEPOLIA;
        } else if (chainId == 80002) {
            // Amoy
            console2.log("Network: Polygon Amoy");
            bridgeManager = BRIDGE_MANAGER_AMOY;
            gateway = AXELAR_GATEWAY_AMOY;
            gasService = AXELAR_GAS_SERVICE_AMOY;
        } else {
            revert("Unsupported chain");
        }

        console2.log("BridgeManager:", bridgeManager);
        console2.log("");

        vm.startBroadcast(deployerPrivateKey);

        // Deploy new AxelarAdapter with correct Axelar testnet chain names
        console2.log(">>> Deploying new AxelarAdapter with correct chain names...");

        string[] memory chainNames = new string[](3);
        chainNames[0] = "ethereum-sepolia"; // ← CORRECT Axelar testnet name
        chainNames[1] = "polygon-sepolia"; // ← CORRECT Axelar testnet name
        chainNames[2] = "arbitrum-sepolia"; // ← CORRECT Axelar testnet name

        AxelarAdapter newAxelarAdapter = new AxelarAdapter(gateway, gasService, chainNames);
        console2.log("New AxelarAdapter deployed at:", address(newAxelarAdapter));

        // Verify the new adapter has correct chain names
        string memory testChain = newAxelarAdapter.supportedChains(0);
        console2.log("First supported chain:", testChain);
        require(keccak256(bytes(testChain)) == keccak256(bytes("ethereum-sepolia")), "Chain name mismatch!");

        // Register new adapter with BridgeManager
        console2.log("");
        console2.log(">>> Registering new AxelarAdapter with BridgeManager...");
        BridgeManager(payable(bridgeManager)).registerAdapter(newAxelarAdapter);
        console2.log("New AxelarAdapter registered!");

        // Verify registration
        address registeredAdapter = address(BridgeManager(payable(bridgeManager)).adapters("axelar"));
        console2.log("Axelar adapter in BridgeManager:", registeredAdapter);
        require(registeredAdapter == address(newAxelarAdapter), "Registration failed!");

        vm.stopBroadcast();

        console2.log("");
        console2.log("====================================");
        console2.log("Fix Complete!");
        console2.log("====================================");
        console2.log(
            "Old Axelar Adapter:",
            chainId == 11155111
                ? "0x3C8e965aFF06DFcaE9f6cc778b38d72D54D1381d"
                : "0x6e48D179CD80979c8eDf65A5d783B501A0313159"
        );
        console2.log("New Axelar Adapter:", address(newAxelarAdapter));
        console2.log("Chain names: ethereum-sepolia, polygon-sepolia, arbitrum-sepolia");
        console2.log("");
        console2.log("You can now test cross-chain transfers!");
    }
}
