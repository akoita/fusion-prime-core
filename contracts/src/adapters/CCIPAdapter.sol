// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.30;

import {IBridgeAdapter} from "interfaces/IBridgeAdapter.sol";
import {StringAddressUtils} from "interfaces/IAxelarInterfaces.sol";

/// @notice CCIP Client library
library Client {
    struct EVMTokenAmount {
        address token; // token address on the local chain
        uint256 amount; // Amount of tokens
    }

    struct EVM2AnyMessage {
        bytes receiver; // abi.encodePacked(receiver address)
        bytes data; // Data payload
        EVMTokenAmount[] tokenAmounts; // Token transfers
        address feeToken; // Address of feeToken. address(0) means you will send msg.value.
        bytes extraArgs; // Populate this with _argsToBytes(EVMExtraArgsV2)
    }
}

/// @notice Chainlink CCIP Router interface
interface IRouterClient {
    function ccipSend(
        uint64 destinationChainSelector,
        Client.EVM2AnyMessage calldata message
    ) external payable returns (bytes32 messageId);

    function getFee(
        uint64 destinationChainSelector,
        Client.EVM2AnyMessage calldata message
    ) external view returns (uint256 fee);
}

/// @title CCIPAdapter
/// @notice Bridge adapter for Chainlink CCIP (Cross-Chain Interoperability Protocol)
/// @dev Implements IBridgeAdapter for Chainlink CCIP
contract CCIPAdapter is IBridgeAdapter {
    using StringAddressUtils for string;

    IRouterClient public immutable router;
    mapping(uint64 => string) public chainSelectorToName;
    mapping(string => uint64) public chainNameToSelector;
    string[] public supportedChains;

    event MessageSent(uint64 destinationChainSelector, address destinationAddress, bytes32 messageId);
    event GasEstimated(uint64 destinationChainSelector, uint256 estimatedGas);

    /// @notice Constructor for CCIPAdapter
    /// @param _router Chainlink CCIP Router address
    /// @param _chainSelectors Array of chain selectors
    /// @param _chainNames Array of chain names corresponding to selectors
    constructor(
        address _router,
        uint64[] memory _chainSelectors,
        string[] memory _chainNames
    ) {
        require(_chainSelectors.length == _chainNames.length, "Mismatched arrays");

        router = IRouterClient(_router);

        for (uint256 i = 0; i < _chainSelectors.length; i++) {
            chainSelectorToName[_chainSelectors[i]] = _chainNames[i];
            chainNameToSelector[_chainNames[i]] = _chainSelectors[i];
            supportedChains.push(_chainNames[i]);
        }
    }

    /// @inheritdoc IBridgeAdapter
    function sendMessage(
        string memory destinationChain,
        string memory destinationAddress,
        bytes memory payload,
        address /* gasToken - CCIP uses native token */
    ) external payable returns (bytes32 messageId) {
        require(isChainSupported(destinationChain), "Unsupported destination chain");

        uint64 destinationChainSelector = chainNameToSelector[destinationChain];
        address destination = destinationAddress.toAddress();

        // Build CCIP message with custom gas limit
        // CCIP extraArgs V1: tag + gasLimit
        // 200k gas is enough for cross-chain vault operations (simulation showed 144k needed)
        bytes memory extraArgs = abi.encodePacked(
            bytes4(0x97a657c9), // EVMExtraArgsV1 tag
            abi.encode(200000)    // gasLimit
        );

        Client.EVM2AnyMessage memory message = Client.EVM2AnyMessage({
            receiver: abi.encodePacked(destination), // CRITICAL: CCIP expects abi.encodePacked (20 bytes), not abi.encode (32 bytes)
            data: payload,
            tokenAmounts: new Client.EVMTokenAmount[](0), // No token transfers
            feeToken: address(0), // Pay fees in native token
            extraArgs: extraArgs // Custom gas limit for vault operations
        });

        // Send via CCIP Router
        messageId = router.ccipSend{value: msg.value}(destinationChainSelector, message);

        emit MessageSent(destinationChainSelector, destination, messageId);
        return messageId;
    }

    /// @inheritdoc IBridgeAdapter
    function estimateGas(
        string memory destinationChain,
        bytes memory payload
    ) external view returns (uint256 estimatedGas) {
        require(isChainSupported(destinationChain), "Unsupported destination chain");

        uint64 destinationChainSelector = chainNameToSelector[destinationChain];

        // Placeholder destination address for fee estimation
        address destination = address(0x1111111111111111111111111111111111111111);

        // Build CCIP message for fee estimation
        Client.EVM2AnyMessage memory message = Client.EVM2AnyMessage({
            receiver: abi.encodePacked(destination), // CRITICAL: CCIP expects abi.encodePacked (20 bytes)
            data: payload,
            tokenAmounts: new Client.EVMTokenAmount[](0), // No token transfers
            feeToken: address(0), // Pay fees in native token
            extraArgs: "" // Default extra args
        });

        estimatedGas = router.getFee(destinationChainSelector, message);
        // Note: Cannot emit events in view functions, but gas estimation events are optional
        return estimatedGas;
    }

    /// @inheritdoc IBridgeAdapter
    function getProtocolName() external pure returns (string memory) {
        return "ccip";
    }

    /// @inheritdoc IBridgeAdapter
    function isChainSupported(string memory chainName) public view returns (bool) {
        return chainNameToSelector[chainName] != 0;
    }

    /// @inheritdoc IBridgeAdapter
    function getSupportedChains() external view returns (string[] memory) {
        return supportedChains;
    }

}
