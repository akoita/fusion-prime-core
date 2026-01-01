// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.30;

import {CrossChainVault} from "./CrossChainVault.sol";

/// @title VaultFactory
/// @notice Factory for deploying CrossChainVault with deterministic addresses using CREATE2
/// @dev Ensures vaults have the same address across all chains by using CREATE2
contract VaultFactory {
    event VaultDeployed(address indexed vault, uint256 chainId, bytes32 salt);

    /// @notice Deploy a CrossChainVault with deterministic address using CREATE2
    /// @param bridgeManager BridgeManager address (should be same across chains)
    /// @param axelarGateway Axelar Gateway address (same across testnets)
    /// @param ccipRouter Chainlink CCIP Router address
    /// @param supportedChains Array of supported chain names (must be same across chains)
    /// @param salt Salt for CREATE2 (use same salt across all chains for same address)
    /// @return vault Address of the deployed vault
    function deployVault(
        address bridgeManager,
        address axelarGateway,
        address ccipRouter,
        string[] memory supportedChains,
        bytes32 salt
    ) external returns (address vault) {
        // Deploy vault using CREATE2 - chainName auto-detected from block.chainid
        bytes memory bytecode = abi.encodePacked(
            type(CrossChainVault).creationCode,
            abi.encode(
                bridgeManager,
                axelarGateway,
                ccipRouter,
                supportedChains
            )
        );

        assembly {
            vault := create2(0, add(bytecode, 32), mload(bytecode), salt)
            if iszero(vault) {
                revert(0, 0)
            }
        }

        emit VaultDeployed(vault, block.chainid, salt);
    }

    /// @notice Compute the deterministic address for a vault before deployment
    /// @param bridgeManager BridgeManager address
    /// @param axelarGateway Axelar Gateway address
    /// @param ccipRouter Chainlink CCIP Router address
    /// @param supportedChains Array of supported chain names
    /// @param salt Salt for CREATE2
    /// @return predicted The address the vault will have
    function computeVaultAddress(
        address bridgeManager,
        address axelarGateway,
        address ccipRouter,
        string[] memory supportedChains,
        bytes32 salt
    ) external view returns (address predicted) {
        bytes memory bytecode = abi.encodePacked(
            type(CrossChainVault).creationCode,
            abi.encode(
                bridgeManager,
                axelarGateway,
                ccipRouter,
                supportedChains
            )
        );

        bytes32 hash = keccak256(
            abi.encodePacked(
                bytes1(0xff),
                address(this),
                salt,
                keccak256(bytecode)
            )
        );

        predicted = address(uint160(uint256(hash)));
    }
}
