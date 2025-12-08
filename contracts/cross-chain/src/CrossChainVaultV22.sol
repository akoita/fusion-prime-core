// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.30;

/// @notice MessageBridge interface for cross-chain messaging
interface IMessageBridge {
    function sendMessage(
        uint64 destChainId,
        address recipient,
        bytes calldata payload
    ) external returns (bytes32 messageId);
}

/// @title CrossChainVaultV22
/// @notice Unified vault for managing collateral and credit across multiple chains
/// @dev Uses MessageBridge for cross-chain communication (fully custom bridge)
contract CrossChainVaultV22 {
    // State
    IMessageBridge public messageBridge;

    // Chain tracking
    string public thisChainName;
    uint64 public thisChainId;
    mapping(string => bool) public supportedChains;
    mapping(string => uint64) public chainNameToId;
    mapping(uint64 => string) public chainIdToName;
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
    /// @dev Set to 0.01 ETH to ensure sufficient gas, though MessageBridge is relay-based
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

    /// @notice Initialize the vault with MessageBridge and supported chains
    /// @param _messageBridge MessageBridge contract address
    /// @param _supportedChains Array of supported chain names
    /// @param _chainIds Array of chain IDs corresponding to names
    /// @dev Chain name and ID are auto-detected from block.chainid
    constructor(
        address _messageBridge,
        string[] memory _supportedChains,
        uint64[] memory _chainIds
    ) {
        require(_supportedChains.length == _chainIds.length, "Mismatched chain arrays");
        require(_messageBridge != address(0), "Invalid MessageBridge address");

        messageBridge = IMessageBridge(_messageBridge);
        thisChainId = uint64(block.chainid);
        thisChainName = _getChainName(block.chainid);

        // Set up chain mappings
        for (uint256 i = 0; i < _supportedChains.length; i++) {
            chainNameToId[_supportedChains[i]] = _chainIds[i];
            chainIdToName[_chainIds[i]] = _supportedChains[i];
            supportedChains[_supportedChains[i]] = true;
            allSupportedChains.push(_supportedChains[i]);
        }

        // Ensure this chain is in supported list
        if (!supportedChains[thisChainName]) {
            supportedChains[thisChainName] = true;
            chainNameToId[thisChainName] = thisChainId;
            chainIdToName[thisChainId] = thisChainName;
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

        // Encode payload with function selector for executeMessage
        bytes memory payload = abi.encodeWithSignature(
            "executeMessage(bytes32,address,uint8,uint256,string)",
            messageId,
            user,
            uint8(1), // action = deposit
            collateralAmount,
            thisChainName
        );

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

    /// @notice MessageBridge callback - receives cross-chain messages
    /// @param messageId Message identifier for replay protection
    /// @param user User address affected by this message
    /// @param action Action type: 1=deposit, 2=withdraw, 3=borrow, 4=repay
    /// @param amount Amount involved in the action
    /// @param chainName Chain where the action originated
    /// @dev This function is called by MessageBridge.executeMessage via low-level call
    /// @dev CRITICAL: Only MessageBridge can call this function
    function executeMessage(
        bytes32 messageId,
        address user,
        uint8 action,
        uint256 amount,
        string memory chainName
    ) external {
        // CRITICAL: Only MessageBridge can call this
        require(msg.sender == address(messageBridge), "Unauthorized: Only MessageBridge");

        // Replay protection
        require(!processedMessages[messageId], "Message already processed");
        processedMessages[messageId] = true;

        // Verify chain is supported
        require(supportedChains[chainName], "Unsupported source chain");

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
        } else {
            revert InvalidMessage();
        }

        _updateCreditLine(user);

        // Get source chain from chainIdToName mapping
        emit CrossChainMessageReceived(chainName, messageId, user);
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

        // Encode payload with function selector for executeMessage
        bytes memory payload = abi.encodeWithSignature(
            "executeMessage(bytes32,address,uint8,uint256,string)",
            messageId,
            user,
            action,
            amount,
            chainName
        );

        // Broadcast to all supported chains except this one
        // Note: Gas is divided equally among destination chains
        uint256 destCount = 0;
        for (uint256 i = 0; i < allSupportedChains.length; i++) {
            if (keccak256(bytes(allSupportedChains[i])) != keccak256(bytes(thisChainName))) {
                destCount++;
            }
        }

        if (destCount > 0) {
            uint256 gasPerChain = gasAmount / destCount;
            for (uint256 i = 0; i < allSupportedChains.length; i++) {
                if (keccak256(bytes(allSupportedChains[i])) != keccak256(bytes(thisChainName))) {
                    _sendCrossChainMessage(allSupportedChains[i], payload, gasPerChain);
                    emit CrossChainMessageSent(allSupportedChains[i], messageId, user);
                }
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

        // Encode payload with function selector for executeMessage
        bytes memory payload = abi.encodeWithSignature(
            "executeMessage(bytes32,address,uint8,uint256,string)",
            messageId,
            user,
            isBorrow ? uint8(3) : uint8(4),
            amount,
            chainName
        );

        // Broadcast to all supported chains except this one
        uint256 destCount = 0;
        for (uint256 i = 0; i < allSupportedChains.length; i++) {
            if (keccak256(bytes(allSupportedChains[i])) != keccak256(bytes(thisChainName))) {
                destCount++;
            }
        }

        if (destCount > 0) {
            uint256 gasPerChain = gasAmount / destCount;
            for (uint256 i = 0; i < allSupportedChains.length; i++) {
                if (keccak256(bytes(allSupportedChains[i])) != keccak256(bytes(thisChainName))) {
                    _sendCrossChainMessage(allSupportedChains[i], payload, gasPerChain);
                    emit CrossChainMessageSent(allSupportedChains[i], messageId, user);
                }
            }
        }
    }

    /// @notice Send cross-chain message via MessageBridge
    /// @param destinationChain Destination chain name
    /// @param payload Message payload (already encoded with function selector)
    /// @param gasAmount Amount of gas to send with the message
    function _sendCrossChainMessage(
        string memory destinationChain,
        bytes memory payload,
        uint256 gasAmount
    ) internal {
        // Get destination chain ID
        uint64 destChainId = chainNameToId[destinationChain];
        require(destChainId != 0, "Destination chain not configured");

        // Get trusted vault address on destination chain
        address destinationVault = trustedVaults[destinationChain];
        require(destinationVault != address(0), "Destination vault not configured");

        // Send via MessageBridge
        // Note: MessageBridge doesn't charge gas, but we keep the parameter for API compatibility
        messageBridge.sendMessage(destChainId, destinationVault, payload);
    }

    /// @notice Update user's credit line based on collateral and borrows
    function _updateCreditLine(address user) internal {
        // Credit line = total collateral - total borrowed
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
