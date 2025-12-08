// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import {Script} from "forge-std/Script.sol";
import {console2} from "forge-std/console2.sol";
import {VaultFactory} from "../src/VaultFactory.sol";

contract DeployNewFactory is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        vm.startBroadcast(deployerPrivateKey);

        console2.log("====================================");
        console2.log("Deploying NEW VaultFactory with V11 bytecode");
        console2.log("====================================");
        console2.log("Chain ID:", block.chainid);

        VaultFactory factory = new VaultFactory();
        console2.log("VaultFactory deployed:", address(factory));

        vm.stopBroadcast();
    }
}
