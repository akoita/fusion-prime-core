// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.30;

import {BridgeManager} from "./BridgeManager.sol";
import {IAxelarGateway, StringAddressUtils} from "./interfaces/IAxelarInterfaces.sol";
import {AxelarExecutable} from "./base/AxelarExecutable.sol";
import {IPriceOracle} from "./interfaces/IPriceOracle.sol";

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

/// @title CrossChainVaultV24
/// @notice Unified vault with USD-based valuations using Chainlink oracles
/// @dev Uses BridgeManager for cross-chain communication + oracles for accurate pricing
contract CrossChainVaultV24 is AxelarExecutable {
    using StringAddressUtils for string;

    // State
    BridgeManager public bridgeManager;
    address public axelarGateway;
    address public ccipRouter;

    // Chain tracking
    string public thisChainName;
    mapping(string => bool) public supportedChains;
    string[] public allSupportedChains;

    // Oracle mapping per chain
    mapping(string => IPriceOracle) public chainOracles;

    // User balances per chain (in native token amounts)
    mapping(address => mapping(string => uint256)) public collateralBalances; // user => chain => amount
    mapping(address => mapping(string => uint256)) public borrowBalances; // user => chain => amount

    // Aggregated totals (in native tokens for backward compatibility)
    mapping(address => uint256) public totalCollateral; // Total in native tokens
    mapping(address => uint256) public totalBorrowed; // Total in native tokens
    mapping(address => uint256) public totalCreditLine; // Deprecated - use getCreditLineUSD()

    // Message tracking
    mapping(bytes32 => bool) public processedMessages;
    uint256 public messageNonce;

    // Trusted vaults
    mapping(string => address) public trustedVaults;

    // Constants
    uint256 public constant MIN_GAS_AMOUNT = 0.01 ether;
    uint256 public constant COLLATERAL_RATIO = 70; // 70% LTV
    uint256 public constant LIQUIDATION_THRESHOLD = 80; // Can be liquidated at 80%

    // Events
    event CollateralDeposited(address indexed user, string chain, uint256 amount);
    event CollateralWithdrawn(address indexed user, string chain, uint256 amount);
    event Borrowed(address indexed user, string chain, uint256 amount);
    event Repaid(address indexed user, string chain, uint256 amount);
    event CrossChainMessageSent(string destinationChain, bytes32 messageId, address indexed user);
    event CrossChainMessageReceived(string sourceChain, bytes32 messageId, address indexed user);
    event CreditLineUpdated(address indexed user, uint256 newCreditLine, uint256 totalCollateral, uint256 totalBorrowed);
    event ManualSyncInitiated(address indexed user, string destinationChain, uint256 gasAmount);
    event OracleUpdated(string indexed chainName, address indexed oracle);
    event HealthFactorUpdated(address indexed user, uint256 healthFactor);

    // Errors
    error UnsupportedChain(string chainName);
    error InsufficientCollateral();
    error MessageAlreadyProcessed(bytes32 messageId);
    error InvalidMessage();
    error Unauthorized();
    error InsufficientGasAmount(uint256 provided, uint256 required);
    error OracleNotSet(string chainName);
    error ExceedsCreditLine(uint256 requested, uint256 available);
    error WouldTriggerLiquidation(uint256 healthFactor);

    /// @notice Initialize vault with oracles for each chain
    /// @param _bridgeManager BridgeManager address
    /// @param _axelarGateway Axelar Gateway address
    /// @param _ccipRouter CCIP Router address
    /// @param _supportedChains Array of supported chain names
    /// @param _oracleAddresses Array of oracle addresses (same order as chains)
    constructor(
        address _bridgeManager,
        address _axelarGateway,
        address _ccipRouter,
        string[] memory _supportedChains,
        address[] memory _oracleAddresses
    ) AxelarExecutable(_axelarGateway) {
        require(_oracleAddresses.length == _supportedChains.length, "Mismatched oracle array");

        bridgeManager = BridgeManager(_bridgeManager);
        axelarGateway = _axelarGateway;
        ccipRouter = _ccipRouter;
        thisChainName = _getChainName(block.chainid);

        // Set up supported chains and oracles
        for (uint256 i = 0; i < _supportedChains.length; i++) {
            supportedChains[_supportedChains[i]] = true;
            allSupportedChains.push(_supportedChains[i]);

            if (_oracleAddresses[i] != address(0)) {
                chainOracles[_supportedChains[i]] = IPriceOracle(_oracleAddresses[i]);
                emit OracleUpdated(_supportedChains[i], _oracleAddresses[i]);
            }
        }

        // Ensure this chain is supported
        if (!supportedChains[thisChainName]) {
            supportedChains[thisChainName] = true;
            allSupportedChains.push(thisChainName);
        }
    }

    /// @notice Set trusted vault for a chain
    function setTrustedVault(string memory chainName, address vaultAddress) external {
        trustedVaults[chainName] = vaultAddress;
    }

    /// @notice Update oracle for a chain (owner-only in production)
    function setOracle(string memory chainName, address oracleAddress) external {
        require(supportedChains[chainName], "Unsupported chain");
        chainOracles[chainName] = IPriceOracle(oracleAddress);
        emit OracleUpdated(chainName, oracleAddress);
    }

    /// @notice Get total collateral value in USD across ALL chains
    /// @param user User address
    /// @return totalValueUSD Total collateral value in USD (18 decimals)
    function getTotalCollateralValueUSD(address user) public view returns (uint256 totalValueUSD) {
        for (uint256 i = 0; i < allSupportedChains.length; i++) {
            string memory chainName = allSupportedChains[i];
            uint256 nativeAmount = collateralBalances[user][chainName];

            if (nativeAmount > 0) {
                IPriceOracle oracle = chainOracles[chainName];
                if (address(oracle) == address(0)) revert OracleNotSet(chainName);

                uint256 usdValue = oracle.convertToUSD(nativeAmount);
                totalValueUSD += usdValue;
            }
        }
    }

    /// @notice Get total borrowed value in USD across ALL chains
    /// @param user User address
    /// @return totalValueUSD Total borrowed value in USD (18 decimals)
    function getTotalBorrowedValueUSD(address user) public view returns (uint256 totalValueUSD) {
        for (uint256 i = 0; i < allSupportedChains.length; i++) {
            string memory chainName = allSupportedChains[i];
            uint256 borrowedAmount = borrowBalances[user][chainName];

            if (borrowedAmount > 0) {
                IPriceOracle oracle = chainOracles[chainName];
                if (address(oracle) == address(0)) revert OracleNotSet(chainName);

                uint256 usdValue = oracle.convertToUSD(borrowedAmount);
                totalValueUSD += usdValue;
            }
        }
    }

    /// @notice Calculate credit line in USD (70% of collateral value)
    /// @param user User address
    /// @return creditLineUSD Maximum borrowing capacity in USD (18 decimals)
    function getCreditLineUSD(address user) public view returns (uint256 creditLineUSD) {
        uint256 collateralValueUSD = getTotalCollateralValueUSD(user);
        creditLineUSD = (collateralValueUSD * COLLATERAL_RATIO) / 100;
    }

    /// @notice Calculate health factor (Aave-style)
    /// @param user User address
    /// @return healthFactor Health factor with 18 decimals (1e18 = 100%)
    /// @dev healthFactor = (collateral * liquidationThreshold) / totalBorrowed
    /// Examples:
    /// - 2.0e18 = Very healthy (200%)
    /// - 1.5e18 = Healthy (150%)
    /// - 1.1e18 = Warning (110%)
    /// - 1.0e18 = At liquidation threshold
    /// - <1.0e18 = Can be liquidated
    function getHealthFactor(address user) public view returns (uint256 healthFactor) {
        uint256 totalBorrowedUSD = getTotalBorrowedValueUSD(user);

        if (totalBorrowedUSD == 0) {
            return type(uint256).max; // No debt = infinite health
        }

        uint256 collateralValueUSD = getTotalCollateralValueUSD(user);
        uint256 liquidationThresholdValue = (collateralValueUSD * LIQUIDATION_THRESHOLD) / 100;

        healthFactor = (liquidationThresholdValue * 1e18) / totalBorrowedUSD;
    }

    /// @notice Get user's complete financial summary in USD
    /// @return collateralUSD Total collateral in USD
    /// @return borrowedUSD Total borrowed in USD
    /// @return creditLineUSD Available credit in USD
    /// @return healthFactor Health factor (1e18 = 100%)
    /// @return availableUSD Remaining borrowing capacity in USD
    function getUserSummaryUSD(address user)
        external
        view
        returns (
            uint256 collateralUSD,
            uint256 borrowedUSD,
            uint256 creditLineUSD,
            uint256 healthFactor,
            uint256 availableUSD
        )
    {
        collateralUSD = getTotalCollateralValueUSD(user);
        borrowedUSD = getTotalBorrowedValueUSD(user);
        creditLineUSD = getCreditLineUSD(user);
        healthFactor = getHealthFactor(user);

        availableUSD = creditLineUSD > borrowedUSD ? creditLineUSD - borrowedUSD : 0;
    }

    /// @notice Get per-chain breakdown in USD
    /// @param user User address
    /// @param chainName Chain name
    /// @return collateralNative Collateral amount in native token
    /// @return collateralUSD Collateral value in USD
    /// @return borrowedNative Borrowed amount in native token
    /// @return borrowedUSD Borrowed value in USD
    function getChainBreakdownUSD(address user, string memory chainName)
        external
        view
        returns (
            uint256 collateralNative,
            uint256 collateralUSD,
            uint256 borrowedNative,
            uint256 borrowedUSD
        )
    {
        collateralNative = collateralBalances[user][chainName];
        borrowedNative = borrowBalances[user][chainName];

        IPriceOracle oracle = chainOracles[chainName];
        if (address(oracle) != address(0)) {
            collateralUSD = oracle.convertToUSD(collateralNative);
            borrowedUSD = oracle.convertToUSD(borrowedNative);
        }
    }

    /// @notice Deposit collateral on this chain
    /// @param user Address of the user depositing
    /// @param gasAmount Amount of gas for cross-chain broadcasting
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

    /// @notice Withdraw collateral from this chain
    /// @param amount Amount to withdraw
    /// @param gasAmount Amount of gas for cross-chain broadcasting
    function withdrawCollateral(uint256 amount, uint256 gasAmount) external payable {
        if (gasAmount < MIN_GAS_AMOUNT) {
            revert InsufficientGasAmount(gasAmount, MIN_GAS_AMOUNT);
        }
        require(msg.value >= gasAmount, "Insufficient gas payment");
        require(collateralBalances[msg.sender][thisChainName] >= amount, "Insufficient collateral");

        collateralBalances[msg.sender][thisChainName] -= amount;
        totalCollateral[msg.sender] -= amount;

        // Check health factor after withdrawal
        uint256 healthFactor = getHealthFactor(msg.sender);
        if (healthFactor < 1.0e18 && getTotalBorrowedValueUSD(msg.sender) > 0) {
            revert WouldTriggerLiquidation(healthFactor);
        }

        _updateCreditLine(msg.sender);
        _broadcastCollateralUpdate(msg.sender, thisChainName, amount, false, gasAmount);

        payable(msg.sender).transfer(amount);
        emit CollateralWithdrawn(msg.sender, thisChainName, amount);
    }

    /// @notice Borrow native token (uses USD valuations)
    /// @param amount Amount to borrow in native token
    /// @param gasAmount Gas for cross-chain message
    function borrow(uint256 amount, uint256 gasAmount) external payable {
        require(msg.value >= gasAmount, "Insufficient gas");
        if (gasAmount < MIN_GAS_AMOUNT) {
            revert InsufficientGasAmount(gasAmount, MIN_GAS_AMOUNT);
        }

        // Calculate values in USD
        IPriceOracle oracle = chainOracles[thisChainName];
        if (address(oracle) == address(0)) revert OracleNotSet(thisChainName);

        uint256 borrowValueUSD = oracle.convertToUSD(amount);
        uint256 totalBorrowedUSD = getTotalBorrowedValueUSD(msg.sender);
        uint256 creditLineUSD = getCreditLineUSD(msg.sender);

        // Check credit line in USD
        if (totalBorrowedUSD + borrowValueUSD > creditLineUSD) {
            revert ExceedsCreditLine(borrowValueUSD, creditLineUSD - totalBorrowedUSD);
        }

        // Check health factor after borrow
        uint256 newTotalBorrowedUSD = totalBorrowedUSD + borrowValueUSD;
        uint256 collateralValueUSD = getTotalCollateralValueUSD(msg.sender);
        uint256 liquidationValue = (collateralValueUSD * LIQUIDATION_THRESHOLD) / 100;

        if (newTotalBorrowedUSD > liquidationValue) {
            uint256 futureHealthFactor = (liquidationValue * 1e18) / newTotalBorrowedUSD;
            revert WouldTriggerLiquidation(futureHealthFactor);
        }

        // Transfer tokens
        payable(msg.sender).transfer(amount);

        // Update state
        borrowBalances[msg.sender][thisChainName] += amount;
        totalBorrowed[msg.sender] += amount;

        // Broadcast to other chains
        _updateCreditLine(msg.sender);
        _broadcastBorrowUpdate(msg.sender, thisChainName, amount, true, gasAmount);

        emit Borrowed(msg.sender, thisChainName, amount);
        emit HealthFactorUpdated(msg.sender, getHealthFactor(msg.sender));
    }

    /// @notice Repay borrowed amount
    /// @param amount Amount to repay
    function repay(uint256 amount) external payable {
        require(msg.value >= amount, "Insufficient payment");
        require(borrowBalances[msg.sender][thisChainName] >= amount, "Repaying more than borrowed");

        borrowBalances[msg.sender][thisChainName] -= amount;
        totalBorrowed[msg.sender] -= amount;

        uint256 gasForBroadcast = msg.value - amount;

        _updateCreditLine(msg.sender);
        _broadcastBorrowUpdate(msg.sender, thisChainName, amount, false, gasForBroadcast);

        emit Repaid(msg.sender, thisChainName, amount);
        emit HealthFactorUpdated(msg.sender, getHealthFactor(msg.sender));
    }

    /// @notice Manually re-sync user's balance to a specific chain
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

        bytes memory payload = abi.encode(messageId, user, uint8(1), collateralAmount, thisChainName);
        _sendCrossChainMessage(destinationChain, payload, gasAmount);

        emit ManualSyncInitiated(user, destinationChain, gasAmount);
        emit CrossChainMessageSent(destinationChain, messageId, user);
    }

    /// @notice Reconcile user's balance across all chains
    function reconcileBalance(address user, uint256 gasAmount) external payable {
        if (gasAmount < MIN_GAS_AMOUNT) {
            revert InsufficientGasAmount(gasAmount, MIN_GAS_AMOUNT);
        }
        require(msg.value >= gasAmount, "Insufficient gas payment");

        uint256 collateralAmount = collateralBalances[user][thisChainName];
        require(collateralAmount > 0, "No collateral to reconcile");

        _broadcastCollateralUpdate(user, thisChainName, collateralAmount, true, gasAmount);
    }

    /// @notice Axelar message receiver
    function _execute(
        bytes32 commandId,
        string calldata sourceChain,
        string calldata sourceAddress,
        bytes calldata payload
    ) internal override {
        string memory internalChainName = _translateFromAxelar(sourceChain);
        require(supportedChains[internalChainName], "Unsupported source chain");
        _processMessage(internalChainName, sourceAddress, payload);
    }

    /// @notice CCIP message receiver
    function ccipReceive(Client.Any2EVMMessage calldata message) external {
        require(msg.sender == ccipRouter, "CCIP: Unauthorized router");
        require(message.sender.length == 20, "CCIP: Invalid sender length");

        address sender = address(uint160(bytes20(message.sender)));
        string memory sourceChain = _getChainNameFromSelector(message.sourceChainSelector);
        require(supportedChains[sourceChain], "CCIP: Unsupported chain");

        _processMessage(sourceChain, StringAddressUtils.toString(sender), message.data);
    }

    /// @notice Process cross-chain message
    function _processMessage(
        string memory sourceChain,
        string memory sourceAddress,
        bytes calldata payload
    ) internal {
        (bytes32 messageId, address user, uint8 action, uint256 amount, string memory chainName) =
            abi.decode(payload, (bytes32, address, uint8, uint256, string));

        require(!processedMessages[messageId], "Message already processed");
        processedMessages[messageId] = true;

        if (action == 1) {
            // Collateral deposit
            collateralBalances[user][chainName] += amount;
            totalCollateral[user] += amount;
            emit CollateralDeposited(user, chainName, amount);
        } else if (action == 2) {
            // Collateral withdrawal
            collateralBalances[user][chainName] -= amount;
            totalCollateral[user] -= amount;
            emit CollateralWithdrawn(user, chainName, amount);
        } else if (action == 3) {
            // Borrow
            borrowBalances[user][chainName] += amount;
            totalBorrowed[user] += amount;
            emit Borrowed(user, chainName, amount);
        } else if (action == 4) {
            // Repay
            borrowBalances[user][chainName] -= amount;
            totalBorrowed[user] -= amount;
            emit Repaid(user, chainName, amount);
        }

        _updateCreditLine(user);
        emit CrossChainMessageReceived(sourceChain, messageId, user);
    }

    /// @notice Broadcast collateral update
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

        for (uint256 i = 0; i < allSupportedChains.length; i++) {
            if (keccak256(bytes(allSupportedChains[i])) != keccak256(bytes(thisChainName))) {
                _sendCrossChainMessage(allSupportedChains[i], payload, gasAmount / (allSupportedChains.length - 1));
                emit CrossChainMessageSent(allSupportedChains[i], messageId, user);
            }
        }
    }

    /// @notice Broadcast borrow update
    function _broadcastBorrowUpdate(
        address user,
        string memory chainName,
        uint256 amount,
        bool isBorrow,
        uint256 gasAmount
    ) internal {
        bytes32 messageId = keccak256(abi.encodePacked(block.timestamp, messageNonce++, user, amount));
        bytes memory payload = abi.encode(messageId, user, isBorrow ? uint8(3) : uint8(4), amount, chainName);

        for (uint256 i = 0; i < allSupportedChains.length; i++) {
            if (keccak256(bytes(allSupportedChains[i])) != keccak256(bytes(thisChainName))) {
                _sendCrossChainMessage(allSupportedChains[i], payload, gasAmount / (allSupportedChains.length - 1));
                emit CrossChainMessageSent(allSupportedChains[i], messageId, user);
            }
        }
    }

    /// @notice Send cross-chain message
    function _sendCrossChainMessage(
        string memory destinationChain,
        bytes memory payload,
        uint256 gasAmount
    ) internal {
        address destinationVault = trustedVaults[destinationChain];
        require(destinationVault != address(0), "Destination vault not configured");

        string memory destinationAddress = StringAddressUtils.toString(destinationVault);

        bridgeManager.sendMessage{value: gasAmount}(
            destinationChain,
            destinationAddress,
            payload,
            address(0)
        );
    }

    /// @notice Update credit line (backward compatibility)
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

    /// @notice Get chain name from chain ID
    function _getChainName(uint256 chainId) internal pure returns (string memory) {
        if (chainId == 11155111) return "ethereum";
        if (chainId == 80002) return "polygon";
        if (chainId == 421614) return "arbitrum";
        if (chainId == 1) return "ethereum";
        if (chainId == 137) return "polygon";
        if (chainId == 42161) return "arbitrum";
        revert("Unsupported chain");
    }

    /// @notice Translate Axelar chain name
    function _translateFromAxelar(string memory axelarChainName) internal pure returns (string memory) {
        bytes32 nameHash = keccak256(bytes(axelarChainName));

        if (nameHash == keccak256(bytes("ethereum-sepolia"))) return "ethereum";
        if (nameHash == keccak256(bytes("polygon-sepolia"))) return "polygon";
        if (nameHash == keccak256(bytes("arbitrum-sepolia"))) return "arbitrum";
        if (nameHash == keccak256(bytes("optimism-sepolia"))) return "optimism";
        if (nameHash == keccak256(bytes("base-sepolia"))) return "base";

        return axelarChainName;
    }

    /// @notice Get chain name from CCIP selector
    function _getChainNameFromSelector(uint64 chainSelector) internal pure returns (string memory) {
        if (chainSelector == 16015286601757825753) return "ethereum";
        if (chainSelector == 16281711391670634445) return "polygon";
        if (chainSelector == 3478487238524512106) return "arbitrum";
        if (chainSelector == 5224473277236331295) return "optimism";
        if (chainSelector == 10344971235874465080) return "base";

        if (chainSelector == 5009297550715157269) return "ethereum";
        if (chainSelector == 4051577828743386545) return "polygon";
        if (chainSelector == 4949039107694359620) return "arbitrum";
        if (chainSelector == 3734403246176062136) return "optimism";
        if (chainSelector == 15971525489660198786) return "base";

        revert("Unsupported chain selector");
    }

    // Backward compatibility functions
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
