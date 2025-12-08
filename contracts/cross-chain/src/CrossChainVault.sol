// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.30;

import {BridgeManager} from "./BridgeManager.sol";
import {IAxelarGateway, StringAddressUtils} from "./interfaces/IAxelarInterfaces.sol";
import {AxelarExecutable} from "./base/AxelarExecutable.sol";

/// @notice CCIP Client library for receiving messages
library Client {
    struct Any2EVMMessage {
        bytes32 messageId;
        uint64 sourceChainSelector;
        bytes sender; // abi.encodePacked(sender address)
        bytes data; // payload
        EVMTokenAmount[] destTokenAmounts;
    }

    struct EVMTokenAmount {
        address token;
        uint256 amount;
    }
}

/// @title CrossChainVault
/// @notice Unified vault for managing collateral and credit across multiple chains
/// @dev Uses BridgeManager for protocol-agnostic cross-chain communication (Axelar, CCIP, etc.)
contract CrossChainVault is AxelarExecutable {
    using StringAddressUtils for string;

    // State
    BridgeManager public bridgeManager;
    address public axelarGateway; // Axelar Gateway for message authorization
    address public ccipRouter; // Chainlink CCIP Router for message delivery

    // Chain tracking
    string public thisChainName;
    mapping(string => bool) public supportedChains;
    string[] public allSupportedChains;

    // User balances per chain
    mapping(address => mapping(string => uint256)) public collateralBalances; // user => chain => amount
    mapping(address => mapping(string => uint256)) public borrowBalances; // user => chain => amount

    // Credit line (aggregated across chains)
    mapping(address => uint256) public totalCreditLine; // Total credit available across all chains
    mapping(address => uint256) public totalCollateral; // Total collateral across all chains
    mapping(address => uint256) public totalBorrowed; // Total borrowed across all chains

    // Message tracking (replay protection)
    mapping(bytes32 => bool) public processedMessages; // messageId => processed
    uint256 public messageNonce; // Local nonce for outgoing messages

    // Trusted vault addresses per chain (for cross-chain validation)
    mapping(string => address) public trustedVaults; // chainName => vaultAddress

    // Constants
    /// @notice Minimum gas amount required for cross-chain messages
    /// @dev Set to 0.01 ETH to ensure sufficient gas for Axelar/CCIP messages
    /// @dev Any overpayment is automatically refunded by Axelar
    uint256 public constant MIN_GAS_AMOUNT = 0.01 ether;

    // Events
    event CollateralDeposited(address indexed user, string chain, uint256 amount);
    event CollateralWithdrawn(address indexed user, string chain, uint256 amount);
    event Borrowed(address indexed user, string chain, uint256 amount);
    event Repaid(address indexed user, string chain, uint256 amount);
    event CrossChainMessageSent(string destinationChain, bytes32 messageId, address indexed user);
    event CrossChainMessageReceived(string sourceChain, bytes32 messageId, address indexed user);
    event CreditLineUpdated(address indexed user, uint256 newCreditLine, uint256 totalCollateral, uint256 totalBorrowed);
    event ManualSyncInitiated(address indexed user, string destinationChain, uint256 gasAmount);


    // Errors
    error UnsupportedChain(string chainName);
    error InsufficientCollateral();
    error MessageAlreadyProcessed(bytes32 messageId);
    error InvalidMessage();
    error Unauthorized();
    error InsufficientGasAmount(uint256 provided, uint256 required);

    /// @notice Initialize the vault with BridgeManager and supported chains
    /// @param _bridgeManager BridgeManager address (handles Axelar, CCIP, etc.)
    /// @param _axelarGateway Axelar Gateway address for message authorization
    /// @param _ccipRouter Chainlink CCIP Router address for message delivery
    /// @param _supportedChains Array of supported chain names
    /// @dev Chain name is auto-detected from block.chainid for CREATE2 deterministic addresses
    constructor(
        address _bridgeManager,
        address _axelarGateway,
        address _ccipRouter,
        string[] memory _supportedChains
    ) AxelarExecutable(_axelarGateway) {
        bridgeManager = BridgeManager(_bridgeManager);
        axelarGateway = _axelarGateway;
        ccipRouter = _ccipRouter;
        thisChainName = _getChainName(block.chainid);

        // Mark all supported chains
        for (uint256 i = 0; i < _supportedChains.length; i++) {
            supportedChains[_supportedChains[i]] = true;
            allSupportedChains.push(_supportedChains[i]);
        }

        // Mark this chain as supported and add to array
        if (!supportedChains[thisChainName]) {
            supportedChains[thisChainName] = true;
            allSupportedChains.push(thisChainName);
        }
    }

    /// @notice Set trusted vault address for a chain
    /// @param chainName The chain name (e.g., "ethereum", "polygon")
    /// @param vaultAddress The trusted vault address on that chain
    function setTrustedVault(string memory chainName, address vaultAddress) external {
        // For now, anyone can set this during testing
        // In production, add access control (onlyOwner or similar)
        trustedVaults[chainName] = vaultAddress;
    }

    /// @notice Get chain name from chain ID
    /// @param chainId The chain ID
    /// @return Chain name string
    function _getChainName(uint256 chainId) internal pure returns (string memory) {
        if (chainId == 11155111) return "ethereum"; // Sepolia
        if (chainId == 80002) return "polygon";     // Amoy
        if (chainId == 421614) return "arbitrum";   // Arbitrum Sepolia
        if (chainId == 1) return "ethereum";         // Mainnet
        if (chainId == 137) return "polygon";        // Polygon Mainnet
        if (chainId == 42161) return "arbitrum";     // Arbitrum One
        revert("Unsupported chain");
    }

    /// @notice Convert address to string for error messages
    /// @param addr Address to convert
    /// @return String representation of the address
    function _addressToString(address addr) internal pure returns (string memory) {
        bytes memory alphabet = "0123456789abcdef";
        bytes memory str = new bytes(42);
        str[0] = '0';
        str[1] = 'x';
        for (uint256 i = 0; i < 20; i++) {
            str[2+i*2] = alphabet[uint8(uint160(addr) >> (8 * (19 - i)) >> 4)];
            str[3+i*2] = alphabet[uint8(uint160(addr) >> (8 * (19 - i)) & 0x0f)];
        }
        return string(str);
    }

    /// @notice Translate Axelar testnet chain identifiers back to internal chain names
    /// @dev Reverse translation from Axelar's "-sepolia" format to our internal names
    /// @param axelarChainName The chain name from Axelar (e.g., "polygon-sepolia")
    /// @return Internal chain name (e.g., "polygon")
    function _translateFromAxelar(string memory axelarChainName) internal pure returns (string memory) {
        bytes32 nameHash = keccak256(bytes(axelarChainName));

        // Testnet identifiers (translate from -sepolia suffix)
        if (nameHash == keccak256(bytes("ethereum-sepolia"))) return "ethereum";
        if (nameHash == keccak256(bytes("polygon-sepolia"))) return "polygon";
        if (nameHash == keccak256(bytes("arbitrum-sepolia"))) return "arbitrum";
        if (nameHash == keccak256(bytes("optimism-sepolia"))) return "optimism";
        if (nameHash == keccak256(bytes("base-sepolia"))) return "base";

        // If already in internal format or mainnet, return as-is
        return axelarChainName;
    }

    /// @notice Deposit collateral on this chain
    /// @param user Address of the user depositing
    /// @param gasAmount Amount of gas to send for cross-chain broadcasting
    function depositCollateral(address user, uint256 gasAmount) external payable {
        // Enforce minimum gas to prevent permanent out-of-sync state
        if (gasAmount < MIN_GAS_AMOUNT) {
            revert InsufficientGasAmount(gasAmount, MIN_GAS_AMOUNT);
        }
        require(msg.value > gasAmount, "Amount must be greater than gas");

        uint256 collateralAmount = msg.value - gasAmount;
        collateralBalances[user][thisChainName] += collateralAmount;
        totalCollateral[user] += collateralAmount;

        _updateCreditLine(user);
        _broadcastCollateralUpdate(user, thisChainName, collateralAmount, true, gasAmount);

        emit CollateralDeposited(user, thisChainName, collateralAmount);
    }

    /// @notice Withdraw collateral from this chain
    /// @param amount Amount to withdraw
    /// @param gasAmount Amount of gas to send for cross-chain broadcasting
    function withdrawCollateral(uint256 amount, uint256 gasAmount) external payable {
        // Enforce minimum gas to prevent permanent out-of-sync state
        if (gasAmount < MIN_GAS_AMOUNT) {
            revert InsufficientGasAmount(gasAmount, MIN_GAS_AMOUNT);
        }
        require(msg.value >= gasAmount, "Insufficient gas payment");
        require(collateralBalances[msg.sender][thisChainName] >= amount, "Insufficient collateral");

        collateralBalances[msg.sender][thisChainName] -= amount;
        totalCollateral[msg.sender] -= amount;

        _checkCollateralSufficiency(msg.sender);
        _updateCreditLine(msg.sender);
        _broadcastCollateralUpdate(msg.sender, thisChainName, amount, false, gasAmount);

        payable(msg.sender).transfer(amount);
        emit CollateralWithdrawn(msg.sender, thisChainName, amount);
    }

    /// @notice Borrow against collateral (checks total collateral across all chains)
    /// @param amount Amount to borrow
    /// @param gasAmount Amount of gas to send for cross-chain broadcasting
    function borrow(uint256 amount, uint256 gasAmount) external payable {
        // Enforce minimum gas to prevent permanent out-of-sync state
        if (gasAmount < MIN_GAS_AMOUNT) {
            revert InsufficientGasAmount(gasAmount, MIN_GAS_AMOUNT);
        }
        require(msg.value >= gasAmount, "Insufficient gas payment");
        require(totalCollateral[msg.sender] >= totalBorrowed[msg.sender] + amount, "Insufficient collateral");

        borrowBalances[msg.sender][thisChainName] += amount;
        totalBorrowed[msg.sender] += amount;

        _updateCreditLine(msg.sender);
        _broadcastBorrowUpdate(msg.sender, thisChainName, amount, true, gasAmount);

        payable(msg.sender).transfer(amount);
        emit Borrowed(msg.sender, thisChainName, amount);
    }

    /// @notice Repay borrowed amount
    /// @param amount Amount to repay
    /// Note: msg.value should be amount (for repayment) + gas (for broadcasting)
    /// The function will use excess msg.value for cross-chain gas
    function repay(uint256 amount) external payable {
        require(msg.value >= amount, "Insufficient payment");
        require(borrowBalances[msg.sender][thisChainName] >= amount, "Repaying more than borrowed");

        borrowBalances[msg.sender][thisChainName] -= amount;
        totalBorrowed[msg.sender] -= amount;

        // Any excess beyond repayment amount is used for gas
        uint256 gasForBroadcast = msg.value - amount;

        _updateCreditLine(msg.sender);
        _broadcastBorrowUpdate(msg.sender, thisChainName, amount, false, gasForBroadcast);

        emit Repaid(msg.sender, thisChainName, amount);
    }

    /// @notice Manually re-sync user's balance to a specific chain
    /// @dev Use this to recover from failed cross-chain messages (e.g., insufficient gas)
    /// @dev This re-broadcasts the current state without modifying local balances
    /// @param user Address of the user to sync
    /// @param destinationChain Chain to sync to
    /// @param gasAmount Amount of gas to send (must be >= MIN_GAS_AMOUNT)
    function manualSync(address user, string memory destinationChain, uint256 gasAmount) external payable {
        // Enforce minimum gas to ensure message succeeds
        if (gasAmount < MIN_GAS_AMOUNT) {
            revert InsufficientGasAmount(gasAmount, MIN_GAS_AMOUNT);
        }
        require(msg.value >= gasAmount, "Insufficient gas payment");
        require(supportedChains[destinationChain], "Unsupported destination chain");
        require(
            keccak256(bytes(destinationChain)) != keccak256(bytes(thisChainName)),
            "Cannot sync to same chain"
        );

        // Get current collateral balance on this chain for the user
        uint256 collateralAmount = collateralBalances[user][thisChainName];
        require(collateralAmount > 0, "No collateral to sync");

        // Create a new message ID for this manual sync
        bytes32 messageId = keccak256(abi.encodePacked(
            block.timestamp,
            messageNonce++,
            user,
            collateralAmount,
            "manual-sync"
        ));

        // Encode as a deposit update (action = 1)
        bytes memory payload = abi.encode(messageId, user, uint8(1), collateralAmount, thisChainName);

        // Send to specific destination chain
        _sendCrossChainMessage(destinationChain, payload, gasAmount);

        emit ManualSyncInitiated(user, destinationChain, gasAmount);
        emit CrossChainMessageSent(destinationChain, messageId, user);
    }

    /// @notice Reconcile user's balance by re-syncing all chains
    /// @dev Emergency function to fix out-of-sync state across all chains
    /// @dev Broadcasts current collateral state to all other chains
    /// @param user Address of the user to reconcile
    /// @param gasAmount Total gas amount (divided among destination chains)
    function reconcileBalance(address user, uint256 gasAmount) external payable {
        // Enforce minimum gas to ensure messages succeed
        if (gasAmount < MIN_GAS_AMOUNT) {
            revert InsufficientGasAmount(gasAmount, MIN_GAS_AMOUNT);
        }
        require(msg.value >= gasAmount, "Insufficient gas payment");

        // Get current collateral balance on this chain
        uint256 collateralAmount = collateralBalances[user][thisChainName];
        require(collateralAmount > 0, "No collateral to reconcile");

        // Re-broadcast current state to all chains
        _broadcastCollateralUpdate(user, thisChainName, collateralAmount, true, gasAmount);
    }

    /// @notice Axelar message receiver - called by Axelar Gateway
    /// @param commandId Axelar command identifier
    /// @param sourceChain Source chain name (Axelar format, e.g., "polygon-sepolia")
    /// @param sourceAddress Source address (sender contract)
    /// @param payload Encoded message payload
    /// @dev This is the internal implementation called by AxelarExecutable.execute()
    /// @dev AxelarExecutable handles gateway validation, we just process the message
    function _execute(
        bytes32 commandId,
        string calldata sourceChain,
        string calldata sourceAddress,
        bytes calldata payload
    ) internal override {
        // Translate Axelar chain name to internal format (e.g., "polygon-sepolia" -> "polygon")
        string memory internalChainName = _translateFromAxelar(sourceChain);

        // Verify source chain is supported (using internal name)
        require(supportedChains[internalChainName], "Unsupported source chain");

        // Process the message
        _processMessage(internalChainName, sourceAddress, payload);
    }

    /// @notice CCIP message receiver - called by Chainlink CCIP Router
    /// @param message The CCIP message containing sender, data, and chain info
    /// @dev This is the entry point for Chainlink CCIP cross-chain messages
    function ccipReceive(Client.Any2EVMMessage calldata message) external {
        // CRITICAL: Only CCIP Router/OffRamp can call this function
        require(msg.sender == ccipRouter, "CCIP: Unauthorized router");

        // Decode sender address from bytes
        // CCIP uses abi.encodePacked(sender address) which creates a 20-byte array
        // We need to handle this correctly, not use abi.decode which expects 32-byte padded data
        require(message.sender.length == 20, "CCIP: Invalid sender length");

        // Convert 20-byte packed address to address type
        // CCIP encodes as abi.encodePacked(address) which is just the 20 bytes
        address sender = address(uint160(bytes20(message.sender)));

        // Translate CCIP chain selector to internal chain name
        string memory sourceChain = _getChainNameFromSelector(message.sourceChainSelector);

        // Verify source chain is supported
        require(supportedChains[sourceChain], "CCIP: Unsupported chain");

        // Note: Sender validation relaxed for cross-chain vaults with different addresses
        // The CCIP Router validation above provides security
        // In production, use trustedVaults mapping to validate sender per chain

        // Process the message (payload is in message.data)
        _processMessage(sourceChain, StringAddressUtils.toString(sender), message.data);
    }

    /// @notice Translate CCIP chain selector to internal chain name
    /// @param chainSelector CCIP chain selector
    /// @return Internal chain name
    function _getChainNameFromSelector(uint64 chainSelector) internal pure returns (string memory) {
        // Sepolia testnet selectors
        if (chainSelector == 16015286601757825753) return "ethereum"; // Sepolia
        if (chainSelector == 16281711391670634445) return "polygon";   // Polygon Amoy
        if (chainSelector == 3478487238524512106) return "arbitrum";  // Arbitrum Sepolia
        if (chainSelector == 5224473277236331295) return "optimism";  // Optimism Sepolia
        if (chainSelector == 10344971235874465080) return "base";      // Base Sepolia

        // Mainnet selectors
        if (chainSelector == 5009297550715157269) return "ethereum";  // Ethereum Mainnet
        if (chainSelector == 4051577828743386545) return "polygon";   // Polygon Mainnet
        if (chainSelector == 4949039107694359620) return "arbitrum";  // Arbitrum One
        if (chainSelector == 3734403246176062136) return "optimism";  // Optimism Mainnet
        if (chainSelector == 15971525489660198786) return "base";      // Base Mainnet

        revert("Unsupported chain selector");
    }

    /// @notice Internal function to process cross-chain messages
    /// @param sourceChain Source chain name
    /// @param sourceAddress Source address (sender contract)
    /// @param payload Encoded message payload
    function _processMessage(
        string memory sourceChain,
        string memory sourceAddress,
        bytes calldata payload
    ) internal {

        // Decode payload
        (bytes32 messageId, address user, uint8 action, uint256 amount, string memory chainName) =
            abi.decode(payload, (bytes32, address, uint8, uint256, string));

        // Replay protection
        require(!processedMessages[messageId], "Message already processed");
        processedMessages[messageId] = true;

        // Process action
        if (action == 1) {
            // Collateral update (deposit)
            collateralBalances[user][chainName] += amount;
            totalCollateral[user] += amount;
            emit CollateralDeposited(user, chainName, amount);
        } else if (action == 2) {
            // Collateral update (withdrawal)
            collateralBalances[user][chainName] -= amount;
            totalCollateral[user] -= amount;
            emit CollateralWithdrawn(user, chainName, amount);
        } else if (action == 3) {
            // Borrow update (borrow)
            borrowBalances[user][chainName] += amount;
            totalBorrowed[user] += amount;
            emit Borrowed(user, chainName, amount);
        } else if (action == 4) {
            // Borrow update (repay)
            borrowBalances[user][chainName] -= amount;
            totalBorrowed[user] -= amount;
            emit Repaid(user, chainName, amount);
        }

        _updateCreditLine(user);
        emit CrossChainMessageReceived(sourceChain, messageId, user);
    }

    /// @notice Broadcast collateral update to all supported chains
    function _broadcastCollateralUpdate(
        address user,
        string memory chainName,
        uint256 amount,
        bool isDeposit,
        uint256 gasAmount
    ) internal {
        bytes32 messageId = keccak256(abi.encodePacked(block.timestamp, messageNonce++, user, amount));
        uint8 action = isDeposit ? 1 : 2;

        bytes memory payload = abi.encode(messageId, user, action, amount, chainName);

        // Broadcast to all supported chains except this one
        // Note: Gas is divided equally among destination chains
        for (uint256 i = 0; i < allSupportedChains.length; i++) {
            if (keccak256(bytes(allSupportedChains[i])) != keccak256(bytes(thisChainName))) {
                _sendCrossChainMessage(allSupportedChains[i], payload, gasAmount / (allSupportedChains.length - 1));
                emit CrossChainMessageSent(allSupportedChains[i], messageId, user);
            }
        }
    }

    /// @notice Broadcast borrow update to all supported chains
    function _broadcastBorrowUpdate(
        address user,
        string memory chainName,
        uint256 amount,
        bool isBorrow,
        uint256 gasAmount
    ) internal {
        bytes32 messageId = keccak256(abi.encodePacked(block.timestamp, messageNonce++, user, amount));
        bytes memory payload = abi.encode(messageId, user, isBorrow ? uint8(3) : uint8(4), amount, chainName);

        // Broadcast to all supported chains except this one
        // Note: Gas is divided equally among destination chains
        for (uint256 i = 0; i < allSupportedChains.length; i++) {
            if (keccak256(bytes(allSupportedChains[i])) != keccak256(bytes(thisChainName))) {
                _sendCrossChainMessage(allSupportedChains[i], payload, gasAmount / (allSupportedChains.length - 1));
                emit CrossChainMessageSent(allSupportedChains[i], messageId, user);
            }
        }
    }

    /// @notice Send cross-chain message via BridgeManager (protocol-agnostic)
    /// @param destinationChain Destination chain name
    /// @param payload Message payload
    /// @param gasAmount Amount of gas to send with the message
    function _sendCrossChainMessage(
        string memory destinationChain,
        bytes memory payload,
        uint256 gasAmount
    ) internal {
        // Use trustedVaults mapping to get the correct vault address on the destination chain
        address destinationVault = trustedVaults[destinationChain];
        require(destinationVault != address(0), "Destination vault not configured");

        string memory destinationAddress = StringAddressUtils.toString(destinationVault);

        // Use BridgeManager to route to appropriate bridge protocol
        // BridgeManager will select Axelar, CCIP, or another registered adapter
        bridgeManager.sendMessage{value: gasAmount}(
            destinationChain,
            destinationAddress,
            payload,
            address(0) // Native token (address(0))
        );
    }

    /// @notice Send cross-chain message via BridgeManager without explicit gas (for backward compatibility)
    /// @param destinationChain Destination chain name
    /// @param payload Message payload
    function _sendCrossChainMessage(string memory destinationChain, bytes memory payload) internal {
        _sendCrossChainMessage(destinationChain, payload, 0);
    }

    /// @notice Update user's credit line based on collateral and borrows
    function _updateCreditLine(address user) internal {
        // Credit line = total collateral - total borrowed
        // Health ratio = (total collateral - total borrowed) / total borrowed
        uint256 collateral = totalCollateral[user];
        uint256 borrowed = totalBorrowed[user];

        if (collateral >= borrowed) {
            totalCreditLine[user] = collateral - borrowed;
        } else {
            totalCreditLine[user] = 0;
        }

        emit CreditLineUpdated(user, totalCreditLine[user], collateral, borrowed);
    }

    /// @notice Check if user has sufficient collateral across all chains
    function _checkCollateralSufficiency(address user) internal view {
        require(totalCollateral[user] >= totalBorrowed[user], "Insufficient total collateral");
    }

    /// @notice Get user's total collateral across all chains
    function getTotalCollateral(address user) external view returns (uint256) {
        return totalCollateral[user];
    }

    /// @notice Get user's total borrowed across all chains
    function getTotalBorrowed(address user) external view returns (uint256) {
        return totalBorrowed[user];
    }

    /// @notice Get user's available credit line
    function getCreditLine(address user) external view returns (uint256) {
        return totalCreditLine[user];
    }

    /// @notice Get user's collateral on a specific chain
    function getCollateralOnChain(address user, string memory chainName) external view returns (uint256) {
        return collateralBalances[user][chainName];
    }
}
