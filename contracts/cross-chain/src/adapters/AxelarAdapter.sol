// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.30;

import {IBridgeAdapter} from "../interfaces/IBridgeAdapter.sol";
import {IAxelarGateway, IAxelarGasService, StringAddressUtils} from "../interfaces/IAxelarInterfaces.sol";

/// @title AxelarAdapter
/// @notice Bridge adapter for Axelar General Message Passing (GMP)
/// @dev Implements IBridgeAdapter for Axelar protocol
contract AxelarAdapter is IBridgeAdapter {
    using StringAddressUtils for string;

    IAxelarGateway public immutable gateway;
    IAxelarGasService public immutable gasService;
    string[] public supportedChains;
    mapping(string => bool) public isSupported;

    event MessageSent(string destinationChain, string destinationAddress, bytes32 messageId);
    event GasEstimated(string destinationChain, uint256 estimatedGas);

    constructor(
        address _gateway,
        address _gasService,
        string[] memory _supportedChains
    ) {
        gateway = IAxelarGateway(_gateway);
        gasService = IAxelarGasService(_gasService);

        for (uint256 i = 0; i < _supportedChains.length; i++) {
            supportedChains.push(_supportedChains[i]);
            isSupported[_supportedChains[i]] = true;
        }
    }

    /// @notice Translate internal chain names to Axelar testnet chain identifiers
    /// @dev Axelar testnet uses -sepolia suffix for most testnet chains
    function _translateChainName(string memory internalName) internal pure returns (string memory) {
        bytes32 nameHash = keccak256(bytes(internalName));

        // Testnet identifiers (with -sepolia suffix)
        if (nameHash == keccak256(bytes("ethereum"))) return "ethereum-sepolia";
        if (nameHash == keccak256(bytes("polygon"))) return "polygon-sepolia";
        if (nameHash == keccak256(bytes("arbitrum"))) return "arbitrum-sepolia";
        if (nameHash == keccak256(bytes("optimism"))) return "optimism-sepolia";
        if (nameHash == keccak256(bytes("base"))) return "base-sepolia";

        // Also handle if capitalized names are passed (from V2 deployment)
        if (nameHash == keccak256(bytes("Ethereum"))) return "ethereum-sepolia";
        if (nameHash == keccak256(bytes("Polygon"))) return "polygon-sepolia";

        // If no translation needed, return original
        return internalName;
    }

    /// @inheritdoc IBridgeAdapter
    function sendMessage(
        string memory destinationChain,
        string memory destinationAddress,
        bytes memory payload,
        address gasToken
    ) external payable returns (bytes32 messageId) {
        require(isChainSupported(destinationChain), "Unsupported destination chain");

        // Translate to Axelar testnet chain name
        string memory axelarChainName = _translateChainName(destinationChain);

        messageId = keccak256(abi.encodePacked(block.timestamp, block.number, msg.sender, payload));

        // Pay for gas (native token for now)
        if (gasToken == address(0) && msg.value > 0) {
            gasService.payNativeGasForContractCall{value: msg.value}(
                address(this),
                axelarChainName,
                destinationAddress,
                payload,
                msg.sender
            );
        }

        // Send message via gateway with translated chain name
        gateway.callContract(axelarChainName, destinationAddress, payload);

        emit MessageSent(axelarChainName, destinationAddress, messageId);
        return messageId;
    }

    /// @inheritdoc IBridgeAdapter
    function estimateGas(
        string memory destinationChain,
        bytes memory payload
    ) external view returns (uint256 estimatedGas) {
        // Axelar gas estimation is typically done off-chain via their API
        // This is a placeholder - actual implementation would query Axelar's gas oracle
        // For now, return a base estimate based on payload size
        estimatedGas = 50000 + (payload.length * 100);
        // Note: Cannot emit events in view functions, but gas estimation events are optional
        return estimatedGas;
    }

    /// @inheritdoc IBridgeAdapter
    function getProtocolName() external pure returns (string memory) {
        return "axelar";
    }

    /// @inheritdoc IBridgeAdapter
    function isChainSupported(string memory chainName) public view returns (bool) {
        return isSupported[chainName];
    }

    /// @inheritdoc IBridgeAdapter
    function getSupportedChains() external view returns (string[] memory) {
        return supportedChains;
    }
}
