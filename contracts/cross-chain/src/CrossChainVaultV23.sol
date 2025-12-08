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

/// @title CrossChainVaultV23
/// @notice Unified vault for managing collateral and credit across multiple chains
/// @dev V23: Adds absolute state sync (ACTION_SYNC_STATE) to prevent double-counting
contract CrossChainVaultV23 {
    // Action type constants
    uint8 constant ACTION_DEPOSIT = 1;
    uint8 constant ACTION_WITHDRAW = 2;
    uint8 constant ACTION_BORROW = 3;
    uint8 constant ACTION_REPAY = 4;
    uint8 constant ACTION_SYNC_STATE = 5;  // NEW: Absolute state sync

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
    event StateSynced(address indexed user, string chain, uint256 absoluteAmount);  // NEW event

    // Errors
    error UnsupportedChain(string chainName);
    error InsufficientCollateral();
    error MessageAlreadyProcessed(bytes32 messageId);
    error InvalidMessage();
    error Unauthorized();
    error InsufficientGasAmount(uint256 provided, uint256 required);

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

    function setTrustedVault(string memory chainName, address vaultAddress) external {
        trustedVaults[chainName] = vaultAddress;
    }

    function _getChainName(uint256 chainId) internal pure returns (string memory) {
        if (chainId == 11155111) return "ethereum"; // Sepolia
        if (chainId == 80002) return "polygon";     // Amoy
        if (chainId == 421614) return "arbitrum";   // Arbitrum Sepolia
        if (chainId == 1) return "ethereum";         // Mainnet
        if (chainId == 137) return "polygon";        // Polygon Mainnet
        if (chainId == 42161) return "arbitrum";     // Arbitrum One
        revert("Unsupported chain");
    }

    function depositCollateral(address user, uint256 gasAmount) external payable {
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

    function withdrawCollateral(uint256 amount, uint256 gasAmount) external payable {
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

    function borrow(uint256 amount, uint256 gasAmount) external payable {
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

    function repay(uint256 amount) external payable {
        require(msg.value >= amount, "Insufficient payment");
        require(borrowBalances[msg.sender][thisChainName] >= amount, "Repaying more than borrowed");

        borrowBalances[msg.sender][thisChainName] -= amount;
        totalBorrowed[msg.sender] -= amount;

        uint256 gasForBroadcast = msg.value - amount;
        _updateCreditLine(msg.sender);
        _broadcastBorrowUpdate(msg.sender, thisChainName, amount, false, gasForBroadcast);

        emit Repaid(msg.sender, thisChainName, amount);
    }

    function manualSync(address user, string memory destinationChain, uint256 gasAmount) external payable {
        if (gasAmount < MIN_GAS_AMOUNT) {
            revert InsufficientGasAmount(gasAmount, MIN_GAS_AMOUNT);
        }
        require(msg.value >= gasAmount, "Insufficient gas payment");
        require(supportedChains[destinationChain], "Unsupported destination chain");
        require(
            keccak256(bytes(destinationChain)) != keccak256(bytes(thisChainName)),
            "Cannot sync to same chain"
        );

        uint256 collateralAmount = collateralBalances[user][thisChainName];
        require(collateralAmount > 0, "No collateral to sync");

        bytes32 messageId = keccak256(abi.encodePacked(
            block.timestamp,
            messageNonce++,
            user,
            collateralAmount,
            "manual-sync"
        ));

        // Use incremental update for manualSync
        bytes memory payload = abi.encodeWithSignature(
            "executeMessage(bytes32,address,uint8,uint256,string)",
            messageId,
            user,
            ACTION_DEPOSIT,
            collateralAmount,
            thisChainName
        );

        _sendCrossChainMessage(destinationChain, payload, gasAmount);

        emit ManualSyncInitiated(user, destinationChain, gasAmount);
        emit CrossChainMessageSent(destinationChain, messageId, user);
    }

    /// @notice Reconcile user's balance by broadcasting ABSOLUTE state to all chains
    /// @dev V23: Uses ACTION_SYNC_STATE for absolute state updates (prevents double-counting)
    /// @param user Address of the user to reconcile
    /// @param gasAmount Total gas amount (divided among destination chains)
    function reconcileBalance(address user, uint256 gasAmount) external payable {
        if (gasAmount < MIN_GAS_AMOUNT) {
            revert InsufficientGasAmount(gasAmount, MIN_GAS_AMOUNT);
        }
        require(msg.value >= gasAmount, "Insufficient gas payment");

        uint256 collateralAmount = collateralBalances[user][thisChainName];
        require(collateralAmount > 0, "No collateral to reconcile");

        // V23: Broadcast ABSOLUTE state using ACTION_SYNC_STATE
        _broadcastStateSync(user, thisChainName, collateralAmount, gasAmount);
    }

    /// @notice MessageBridge callback - receives cross-chain messages
    /// @dev V23: Handles ACTION_SYNC_STATE for absolute state synchronization
    function executeMessage(
        bytes32 messageId,
        address user,
        uint8 action,
        uint256 amount,
        string memory chainName
    ) external {
        require(msg.sender == address(messageBridge), "Unauthorized: Only MessageBridge");
        require(!processedMessages[messageId], "Message already processed");
        processedMessages[messageId] = true;
        require(supportedChains[chainName], "Unsupported source chain");

        if (action == ACTION_DEPOSIT) {
            // Incremental update: ADD amount
            collateralBalances[user][chainName] += amount;
            totalCollateral[user] += amount;
            emit CollateralDeposited(user, chainName, amount);
        } else if (action == ACTION_WITHDRAW) {
            // Incremental update: SUBTRACT amount
            collateralBalances[user][chainName] -= amount;
            totalCollateral[user] -= amount;
            emit CollateralWithdrawn(user, chainName, amount);
        } else if (action == ACTION_BORROW) {
            // Incremental update: ADD amount
            borrowBalances[user][chainName] += amount;
            totalBorrowed[user] += amount;
            emit Borrowed(user, chainName, amount);
        } else if (action == ACTION_REPAY) {
            // Incremental update: SUBTRACT amount
            borrowBalances[user][chainName] -= amount;
            totalBorrowed[user] -= amount;
            emit Repaid(user, chainName, amount);
        } else if (action == ACTION_SYNC_STATE) {
            // V23: Absolute state update - REPLACE balance instead of adding
            uint256 oldBalance = collateralBalances[user][chainName];
            collateralBalances[user][chainName] = amount;  // SET (not ADD)

            // Adjust totalCollateral accordingly
            if (amount > oldBalance) {
                totalCollateral[user] += (amount - oldBalance);
            } else if (oldBalance > amount) {
                totalCollateral[user] -= (oldBalance - amount);
            }
            // If amount == oldBalance, no change needed

            emit StateSynced(user, chainName, amount);
        } else {
            revert InvalidMessage();
        }

        _updateCreditLine(user);
        emit CrossChainMessageReceived(chainName, messageId, user);
    }

    /// @notice V23: Broadcast ABSOLUTE state to all chains
    /// @dev Uses ACTION_SYNC_STATE which REPLACES the balance instead of adding
    function _broadcastStateSync(
        address user,
        string memory chainName,
        uint256 absoluteAmount,
        uint256 gasAmount
    ) internal {
        bytes32 messageId = keccak256(abi.encodePacked(
            block.timestamp,
            messageNonce++,
            user,
            absoluteAmount,
            "state-sync"
        ));

        // Action 5 = ACTION_SYNC_STATE (absolute replacement)
        bytes memory payload = abi.encodeWithSignature(
            "executeMessage(bytes32,address,uint8,uint256,string)",
            messageId,
            user,
            ACTION_SYNC_STATE,
            absoluteAmount,
            chainName
        );

        // Broadcast to all chains except this one
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

    function _broadcastCollateralUpdate(
        address user,
        string memory chainName,
        uint256 amount,
        bool isDeposit,
        uint256 gasAmount
    ) internal {
        bytes32 messageId = keccak256(abi.encodePacked(block.timestamp, messageNonce++, user, amount));
        uint8 action = isDeposit ? ACTION_DEPOSIT : ACTION_WITHDRAW;

        bytes memory payload = abi.encodeWithSignature(
            "executeMessage(bytes32,address,uint8,uint256,string)",
            messageId,
            user,
            action,
            amount,
            chainName
        );

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

    function _broadcastBorrowUpdate(
        address user,
        string memory chainName,
        uint256 amount,
        bool isBorrow,
        uint256 gasAmount
    ) internal {
        bytes32 messageId = keccak256(abi.encodePacked(block.timestamp, messageNonce++, user, amount));

        bytes memory payload = abi.encodeWithSignature(
            "executeMessage(bytes32,address,uint8,uint256,string)",
            messageId,
            user,
            isBorrow ? ACTION_BORROW : ACTION_REPAY,
            amount,
            chainName
        );

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

    function _sendCrossChainMessage(
        string memory destinationChain,
        bytes memory payload,
        uint256 gasAmount
    ) internal {
        uint64 destChainId = chainNameToId[destinationChain];
        require(destChainId != 0, "Destination chain not configured");

        address destinationVault = trustedVaults[destinationChain];
        require(destinationVault != address(0), "Destination vault not configured");

        messageBridge.sendMessage(destChainId, destinationVault, payload);
    }

    function _updateCreditLine(address user) internal {
        uint256 collateral = totalCollateral[user];
        uint256 borrowed = totalBorrowed[user];

        if (collateral >= borrowed) {
            totalCreditLine[user] = collateral - borrowed;
        } else {
            totalCreditLine[user] = 0;
        }

        emit CreditLineUpdated(user, totalCreditLine[user], collateral, borrowed);
    }

    function _checkCollateralSufficiency(address user) internal view {
        require(totalCollateral[user] >= totalBorrowed[user], "Insufficient total collateral");
    }

    function getTotalCollateral(address user) external view returns (uint256) {
        return totalCollateral[user];
    }

    function getTotalBorrowed(address user) external view returns (uint256) {
        return totalBorrowed[user];
    }

    function getCreditLine(address user) external view returns (uint256) {
        return totalCreditLine[user];
    }

    function getCollateralOnChain(address user, string memory chainName) external view returns (uint256) {
        return collateralBalances[user][chainName];
    }
}
