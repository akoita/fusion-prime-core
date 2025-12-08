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

/// @title CrossChainVaultV26
/// @notice Unified vault with supply/lend mechanism and utilization-based interest rates
/// @dev Extends V24 with liquidity pool and interest accrual
contract CrossChainVaultV26 is AxelarExecutable {
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

    // NEW: Liquidity Pool State
    mapping(string => uint256) public chainLiquidity; // Total supplied liquidity per chain
    mapping(string => uint256) public chainUtilized; // Total borrowed from pool per chain
    mapping(address => mapping(string => uint256)) public suppliedBalances; // user => chain => amount
    mapping(address => uint256) public lastInterestUpdate; // Last time interest was accrued

    // NEW: Interest Rate Parameters
    uint256 public constant BASE_RATE = 2e16; // 2% base APY
    uint256 public constant SLOPE = 10e16; // 10% slope
    uint256 public constant BORROW_MULTIPLIER = 120; // Borrow APY = Supply APY * 1.2
    uint256 public constant SECONDS_PER_YEAR = 365 days;

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

    // NEW: Liquidity Events
    event Supplied(address indexed user, string chain, uint256 amount);
    event LiquidityWithdrawn(address indexed user, string chain, uint256 amount);
    event InterestAccrued(address indexed user, string chain, uint256 interest);
    event LiquidityUpdated(string chain, uint256 totalLiquidity, uint256 utilized);

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
    error InsufficientLiquidity(uint256 requested, uint256 available);
    error InsufficientSuppliedBalance();

    /// @notice Initialize vault with oracles for each chain
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

    // ============================================
    // NEW: LIQUIDITY POOL FUNCTIONS
    // ============================================

    /// @notice Supply liquidity to earn interest
    /// @param gasAmount Gas for cross-chain broadcasting
    function supply(uint256 gasAmount) external payable {
        if (gasAmount < MIN_GAS_AMOUNT) {
            revert InsufficientGasAmount(gasAmount, MIN_GAS_AMOUNT);
        }
        require(msg.value > gasAmount, "Amount must be greater than gas");

        uint256 supplyAmount = msg.value - gasAmount;

        // Accrue interest before updating balance
        _accrueInterest(msg.sender, thisChainName);

        // Update liquidity pool
        chainLiquidity[thisChainName] += supplyAmount;
        suppliedBalances[msg.sender][thisChainName] += supplyAmount;
        lastInterestUpdate[msg.sender] = block.timestamp;

        // Skip cross-chain broadcast for now (BridgeManager not configured)
        // _broadcastLiquidityUpdate(thisChainName, supplyAmount, true, gasAmount);

        emit Supplied(msg.sender, thisChainName, supplyAmount);
        emit LiquidityUpdated(thisChainName, chainLiquidity[thisChainName], chainUtilized[thisChainName]);
    }

    /// @notice Withdraw supplied liquidity with accrued interest
    /// @param amount Amount to withdraw
    /// @param gasAmount Gas for cross-chain broadcasting
    function withdrawSupplied(uint256 amount, uint256 gasAmount) external payable {
        if (gasAmount < MIN_GAS_AMOUNT) {
            revert InsufficientGasAmount(gasAmount, MIN_GAS_AMOUNT);
        }
        require(msg.value >= gasAmount, "Insufficient gas payment");

        // Accrue interest before withdrawal
        _accrueInterest(msg.sender, thisChainName);

        require(suppliedBalances[msg.sender][thisChainName] >= amount, "Insufficient supplied balance");

        // Check liquidity availability (can't withdraw utilized funds)
        uint256 availableLiquidity = chainLiquidity[thisChainName] - chainUtilized[thisChainName];
        require(amount <= availableLiquidity, "Insufficient available liquidity");

        // Update state
        suppliedBalances[msg.sender][thisChainName] -= amount;
        chainLiquidity[thisChainName] -= amount;
        lastInterestUpdate[msg.sender] = block.timestamp;

        // Skip cross-chain broadcast for now (BridgeManager not configured)
        // _broadcastLiquidityUpdate(thisChainName, amount, false, gasAmount);

        // Transfer funds
        payable(msg.sender).transfer(amount);

        emit LiquidityWithdrawn(msg.sender, thisChainName, amount);
        emit LiquidityUpdated(thisChainName, chainLiquidity[thisChainName], chainUtilized[thisChainName]);
    }

    /// @notice Accrue interest for a supplier
    /// @param user User address
    /// @param chain Chain name
    function _accrueInterest(address user, string memory chain) internal {
        uint256 timePassed = block.timestamp - lastInterestUpdate[user];
        if (timePassed == 0 || suppliedBalances[user][chain] == 0) {
            return;
        }

        uint256 supplyAPY = getSupplyAPY(chain);
        uint256 principal = suppliedBalances[user][chain];

        // Calculate interest: (principal * APY * timePassed) / (1e18 * SECONDS_PER_YEAR)
        uint256 interest = (principal * supplyAPY * timePassed) / (1e18 * SECONDS_PER_YEAR);

        if (interest > 0) {
            suppliedBalances[user][chain] += interest;
            chainLiquidity[chain] += interest; // Interest comes from protocol revenue
            emit InterestAccrued(user, chain, interest);
        }
    }

    /// @notice Calculate supply APY based on utilization
    /// @param chain Chain name
    /// @return supplyAPY Annual percentage yield with 18 decimals
    function getSupplyAPY(string memory chain) public view returns (uint256 supplyAPY) {
        uint256 totalLiquidity = chainLiquidity[chain];
        if (totalLiquidity == 0) return BASE_RATE;

        uint256 utilized = chainUtilized[chain];
        uint256 utilizationRate = (utilized * 1e18) / totalLiquidity;

        // APY = baseRate + (utilizationRate * slope)
        supplyAPY = BASE_RATE + (utilizationRate * SLOPE) / 1e18;
    }

    /// @notice Calculate borrow APY based on utilization
    /// @param chain Chain name
    /// @return borrowAPY Annual percentage yield with 18 decimals
    function getBorrowAPY(string memory chain) public view returns (uint256 borrowAPY) {
        uint256 supplyAPY = getSupplyAPY(chain);
        borrowAPY = (supplyAPY * BORROW_MULTIPLIER) / 100;
    }

    /// @notice Get supplier's balance with pending interest
    /// @param user User address
    /// @param chain Chain name
    /// @return balance Current balance including pending interest
    function getSuppliedBalanceWithInterest(address user, string memory chain)
        external
        view
        returns (uint256 balance)
    {
        balance = suppliedBalances[user][chain];

        uint256 timePassed = block.timestamp - lastInterestUpdate[user];
        if (timePassed > 0 && balance > 0) {
            uint256 supplyAPY = getSupplyAPY(chain);
            uint256 interest = (balance * supplyAPY * timePassed) / (1e18 * SECONDS_PER_YEAR);
            balance += interest;
        }
    }

    /// @notice Get available liquidity on a chain
    /// @param chain Chain name
    /// @return available Available liquidity for borrowing
    function getAvailableLiquidity(string memory chain) external view returns (uint256 available) {
        uint256 total = chainLiquidity[chain];
        uint256 utilized = chainUtilized[chain];
        available = total > utilized ? total - utilized : 0;
    }

    /// @notice Get utilization rate for a chain
    /// @param chain Chain name
    /// @return utilizationRate Utilization rate with 18 decimals (1e18 = 100%)
    function getUtilizationRate(string memory chain) external view returns (uint256 utilizationRate) {
        uint256 total = chainLiquidity[chain];
        if (total == 0) return 0;

        uint256 utilized = chainUtilized[chain];
        utilizationRate = (utilized * 1e18) / total;
    }

    // ============================================
    // USD VALUATION FUNCTIONS (from V24)
    // ============================================

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

    function getCreditLineUSD(address user) public view returns (uint256 creditLineUSD) {
        uint256 collateralValueUSD = getTotalCollateralValueUSD(user);
        creditLineUSD = (collateralValueUSD * COLLATERAL_RATIO) / 100;
    }

    function getHealthFactor(address user) public view returns (uint256 healthFactor) {
        uint256 totalBorrowedUSD = getTotalBorrowedValueUSD(user);

        if (totalBorrowedUSD == 0) {
            return type(uint256).max; // No debt = infinite health
        }

        uint256 collateralValueUSD = getTotalCollateralValueUSD(user);
        uint256 liquidationThresholdValue = (collateralValueUSD * LIQUIDATION_THRESHOLD) / 100;

        healthFactor = (liquidationThresholdValue * 1e18) / totalBorrowedUSD;
    }

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

    // ============================================
    // COLLATERAL & BORROWING FUNCTIONS (from V24)
    // ============================================

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

    /// @notice Borrow from liquidity pool (NEW: checks pool liquidity)
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

        // NEW: Check liquidity availability
        uint256 availableLiquidity = chainLiquidity[thisChainName] - chainUtilized[thisChainName];
        if (amount > availableLiquidity) {
            revert InsufficientLiquidity(amount, availableLiquidity);
        }

        // Check health factor after borrow
        uint256 newTotalBorrowedUSD = totalBorrowedUSD + borrowValueUSD;
        uint256 collateralValueUSD = getTotalCollateralValueUSD(msg.sender);
        uint256 liquidationValue = (collateralValueUSD * LIQUIDATION_THRESHOLD) / 100;

        if (newTotalBorrowedUSD > liquidationValue) {
            uint256 futureHealthFactor = (liquidationValue * 1e18) / newTotalBorrowedUSD;
            revert WouldTriggerLiquidation(futureHealthFactor);
        }

        // Update state
        borrowBalances[msg.sender][thisChainName] += amount;
        totalBorrowed[msg.sender] += amount;
        chainUtilized[thisChainName] += amount; // NEW: Track utilization

        // Transfer tokens
        payable(msg.sender).transfer(amount);

        // Broadcast to other chains
        _updateCreditLine(msg.sender);
        _broadcastBorrowUpdate(msg.sender, thisChainName, amount, true, gasAmount);

        emit Borrowed(msg.sender, thisChainName, amount);
        emit HealthFactorUpdated(msg.sender, getHealthFactor(msg.sender));
        emit LiquidityUpdated(thisChainName, chainLiquidity[thisChainName], chainUtilized[thisChainName]);
    }

    /// @notice Repay borrowed amount (NEW: frees up liquidity)
    function repay(uint256 amount) external payable {
        require(msg.value >= amount, "Insufficient payment");
        require(borrowBalances[msg.sender][thisChainName] >= amount, "Repaying more than borrowed");

        borrowBalances[msg.sender][thisChainName] -= amount;
        totalBorrowed[msg.sender] -= amount;
        chainUtilized[thisChainName] -= amount; // NEW: Free up liquidity

        uint256 gasForBroadcast = msg.value - amount;

        _updateCreditLine(msg.sender);
        _broadcastBorrowUpdate(msg.sender, thisChainName, amount, false, gasForBroadcast);

        emit Repaid(msg.sender, thisChainName, amount);
        emit HealthFactorUpdated(msg.sender, getHealthFactor(msg.sender));
        emit LiquidityUpdated(thisChainName, chainLiquidity[thisChainName], chainUtilized[thisChainName]);
    }

    // ============================================
    // CROSS-CHAIN MESSAGING (from V24)
    // ============================================

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

    function reconcileBalance(address user, uint256 gasAmount) external payable {
        if (gasAmount < MIN_GAS_AMOUNT) {
            revert InsufficientGasAmount(gasAmount, MIN_GAS_AMOUNT);
        }
        require(msg.value >= gasAmount, "Insufficient gas payment");

        uint256 collateralAmount = collateralBalances[user][thisChainName];
        require(collateralAmount > 0, "No collateral to reconcile");

        _broadcastCollateralUpdate(user, thisChainName, collateralAmount, true, gasAmount);
    }

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

    function ccipReceive(Client.Any2EVMMessage calldata message) external {
        require(msg.sender == ccipRouter, "CCIP: Unauthorized router");
        require(message.sender.length == 20, "CCIP: Invalid sender length");

        address sender = address(uint160(bytes20(message.sender)));
        string memory sourceChain = _getChainNameFromSelector(message.sourceChainSelector);
        require(supportedChains[sourceChain], "CCIP: Unsupported chain");

        _processMessage(sourceChain, StringAddressUtils.toString(sender), message.data);
    }

    /// @notice Process cross-chain message (NEW: handles liquidity updates)
    function _processMessage(
        string memory sourceChain,
        string memory sourceAddress,
        bytes calldata payload
    ) internal {
        // Decode message type
        uint8 messageType;
        assembly {
            messageType := calldataload(add(payload.offset, 64)) // Get action type from payload
        }

        // Action 5 = liquidity update
        if (messageType == 5) {
            (bytes32 messageId, string memory chainName, uint256 amount, bool isSupply) =
                abi.decode(payload, (bytes32, string, uint256, bool));

            require(!processedMessages[messageId], "Message already processed");
            processedMessages[messageId] = true;

            if (isSupply) {
                chainLiquidity[chainName] += amount;
            } else {
                chainLiquidity[chainName] -= amount;
            }

            emit CrossChainMessageReceived(sourceChain, messageId, address(0));
            emit LiquidityUpdated(chainName, chainLiquidity[chainName], chainUtilized[chainName]);
        } else {
            // Standard message processing (collateral/borrow)
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
                chainUtilized[chainName] += amount; // NEW
                emit Borrowed(user, chainName, amount);
            } else if (action == 4) {
                // Repay
                borrowBalances[user][chainName] -= amount;
                totalBorrowed[user] -= amount;
                chainUtilized[chainName] -= amount; // NEW
                emit Repaid(user, chainName, amount);
            }

            _updateCreditLine(user);
            emit CrossChainMessageReceived(sourceChain, messageId, user);
        }
    }

    /// @notice NEW: Broadcast liquidity update
    function _broadcastLiquidityUpdate(
        string memory chainName,
        uint256 amount,
        bool isSupply,
        uint256 gasAmount
    ) internal {
        bytes32 messageId = keccak256(abi.encodePacked(block.timestamp, messageNonce++, amount, "liquidity"));
        bytes memory payload = abi.encode(messageId, chainName, amount, isSupply);

        for (uint256 i = 0; i < allSupportedChains.length; i++) {
            if (keccak256(bytes(allSupportedChains[i])) != keccak256(bytes(thisChainName))) {
                _sendCrossChainMessage(allSupportedChains[i], payload, gasAmount / (allSupportedChains.length - 1));
                emit CrossChainMessageSent(allSupportedChains[i], messageId, address(0));
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
        uint8 action = isDeposit ? 1 : 2;
        bytes memory payload = abi.encode(messageId, user, action, amount, chainName);

        for (uint256 i = 0; i < allSupportedChains.length; i++) {
            if (keccak256(bytes(allSupportedChains[i])) != keccak256(bytes(thisChainName))) {
                _sendCrossChainMessage(allSupportedChains[i], payload, gasAmount / (allSupportedChains.length - 1));
                emit CrossChainMessageSent(allSupportedChains[i], messageId, user);
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
        bytes memory payload = abi.encode(messageId, user, isBorrow ? uint8(3) : uint8(4), amount, chainName);

        for (uint256 i = 0; i < allSupportedChains.length; i++) {
            if (keccak256(bytes(allSupportedChains[i])) != keccak256(bytes(thisChainName))) {
                _sendCrossChainMessage(allSupportedChains[i], payload, gasAmount / (allSupportedChains.length - 1));
                emit CrossChainMessageSent(allSupportedChains[i], messageId, user);
            }
        }
    }

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

    // ============================================
    // HELPER FUNCTIONS
    // ============================================

    function _getChainName(uint256 chainId) internal pure returns (string memory) {
        if (chainId == 11155111) return "ethereum";
        if (chainId == 80002) return "polygon";
        if (chainId == 421614) return "arbitrum";
        if (chainId == 1) return "ethereum";
        if (chainId == 137) return "polygon";
        if (chainId == 42161) return "arbitrum";
        revert("Unsupported chain");
    }

    function _translateFromAxelar(string memory axelarChainName) internal pure returns (string memory) {
        bytes32 nameHash = keccak256(bytes(axelarChainName));

        if (nameHash == keccak256(bytes("ethereum-sepolia"))) return "ethereum";
        if (nameHash == keccak256(bytes("polygon-sepolia"))) return "polygon";
        if (nameHash == keccak256(bytes("arbitrum-sepolia"))) return "arbitrum";
        if (nameHash == keccak256(bytes("optimism-sepolia"))) return "optimism";
        if (nameHash == keccak256(bytes("base-sepolia"))) return "base";

        return axelarChainName;
    }

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

    // Receive function to accept ETH
    receive() external payable {}
}
