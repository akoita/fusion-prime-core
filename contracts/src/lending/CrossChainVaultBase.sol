// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {
    SafeERC20
} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {
    ReentrancyGuard
} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {AxelarExecutable} from "base/AxelarExecutable.sol";
import {IAxelarGasService} from "interfaces/IAxelarInterfaces.sol";
import {
    IMultiTokenPriceOracle
} from "interfaces/IMultiTokenPriceOracle.sol";
import {
    IFlashLoanReceiver
} from "interfaces/IFlashLoanReceiver.sol";
import {InterestRateModel} from "./InterestRateModel.sol";

/**
 * @title CrossChainVaultBase
 * @notice Base cross-chain vault with variable/stable rates, reserves, pause, and flash loans
 * @dev Core vault implementation - extended by CrossChainVault for compliance features
 */
contract CrossChainVaultBase is AxelarExecutable, Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    // ========== STATE VARIABLES ==========

    // Rate mode enum
    enum RateMode {
        VARIABLE,
        STABLE
    }

    // User position struct
    struct Position {
        uint256 collateral; // Native ETH collateral
        uint256 borrowed; // Total borrowed in USD value
        uint256 lastUpdate; // Last interest accrual timestamp
        RateMode rateMode; // Variable or stable
        uint256 stableRate; // Locked stable rate (if stable mode)
        uint256 stableRateLockTime; // When stable rate was locked
    }

    // Token collateral struct
    struct TokenCollateral {
        uint256 deposited;
        uint256 borrowed;
        uint256 lastUpdate;
        RateMode rateMode;
        uint256 stableRate;
        uint256 stableRateLockTime;
    }

    // External contracts
    IAxelarGasService public gasService;
    IMultiTokenPriceOracle public priceOracle;
    InterestRateModel public interestRateModel;

    // User positions
    mapping(address => Position) public positions;
    mapping(address => mapping(address => TokenCollateral))
        public tokenCollateral;

    // Pool state
    mapping(address => uint256) public totalDeposited; // token => total deposited
    mapping(address => uint256) public totalBorrowed; // token => total borrowed
    mapping(address => uint256) public reserves; // token => accumulated reserves

    // Collateral factors per token (basis points, 10000 = 100%)
    mapping(address => uint256) public collateralFactors;

    // Supported tokens
    mapping(address => bool) public supportedTokens;
    address[] public tokenList;

    // ========== CONSTANTS ==========

    uint256 public constant BASIS_POINTS = 10000;
    uint256 public constant LIQUIDATION_THRESHOLD = 8000; // 80%
    uint256 public constant LIQUIDATION_BONUS = 500; // 5%
    uint256 public constant CLOSE_FACTOR = 5000; // 50%
    uint256 public constant RESERVE_FACTOR = 1000; // 10% of interest to reserves
    uint256 public constant FLASH_LOAN_FEE = 9; // 0.09%
    uint256 public constant STABLE_RATE_LOCK_PERIOD = 30 days;
    uint256 public constant UNPAUSE_TIMELOCK = 24 hours;

    // ========== PAUSE MECHANISM ==========

    bool public paused;
    uint256 public unpauseRequestTime;
    bool public unpauseRequested;

    // ========== EVENTS ==========

    event Deposit(address indexed user, address indexed token, uint256 amount);
    event Withdraw(address indexed user, address indexed token, uint256 amount);
    event Borrow(
        address indexed user,
        address indexed token,
        uint256 amount,
        RateMode rateMode
    );
    event Repay(address indexed user, address indexed token, uint256 amount);
    event Liquidation(
        address indexed liquidator,
        address indexed user,
        address indexed token,
        uint256 debtRepaid,
        uint256 collateralSeized
    );
    event RateModeChanged(
        address indexed user,
        address indexed token,
        RateMode oldMode,
        RateMode newMode
    );
    event ReservesWithdrawn(
        address indexed token,
        address indexed to,
        uint256 amount
    );
    event FlashLoan(
        address indexed receiver,
        address indexed token,
        uint256 amount,
        uint256 fee
    );
    event Paused(address indexed by, uint256 timestamp);
    event UnpauseRequested(address indexed by, uint256 unlockTime);
    event Unpaused(address indexed by, uint256 timestamp);
    event CollateralFactorUpdated(address indexed token, uint256 factor);
    event TokenAdded(address indexed token, uint256 collateralFactor);
    event CrossChainDeposit(
        string sourceChain,
        address indexed user,
        address indexed token,
        uint256 amount
    );

    // ========== MODIFIERS ==========

    modifier whenNotPaused() {
        require(!paused, "Contract is paused");
        _;
    }

    modifier onlySupportedToken(address token) {
        require(supportedTokens[token], "Token not supported");
        _;
    }

    // ========== CONSTRUCTOR ==========

    constructor(
        address _gateway,
        address _gasService,
        address _priceOracle,
        address _interestRateModel
    ) AxelarExecutable(_gateway) Ownable(msg.sender) {
        gasService = IAxelarGasService(_gasService);
        priceOracle = IMultiTokenPriceOracle(_priceOracle);
        interestRateModel = InterestRateModel(_interestRateModel);
    }

    // ========== DEPOSIT FUNCTIONS ==========

    /**
     * @notice Deposit native ETH as collateral
     */
    function deposit() external payable virtual whenNotPaused nonReentrant {
        require(msg.value > 0, "Must deposit > 0");

        positions[msg.sender].collateral += msg.value;
        positions[msg.sender].lastUpdate = block.timestamp;

        emit Deposit(msg.sender, address(0), msg.value);
    }

    /**
     * @notice Deposit ERC20 tokens as collateral
     */
    function depositToken(
        address token,
        uint256 amount
    ) external virtual whenNotPaused nonReentrant onlySupportedToken(token) {
        require(amount > 0, "Must deposit > 0");

        IERC20(token).safeTransferFrom(msg.sender, address(this), amount);

        tokenCollateral[msg.sender][token].deposited += amount;
        tokenCollateral[msg.sender][token].lastUpdate = block.timestamp;
        totalDeposited[token] += amount;

        emit Deposit(msg.sender, token, amount);
    }

    // ========== WITHDRAW FUNCTIONS ==========

    /**
     * @notice Withdraw native ETH (allowed even when paused)
     */
    function withdraw(uint256 amount) external nonReentrant {
        Position storage pos = positions[msg.sender];
        require(pos.collateral >= amount, "Insufficient collateral");

        // Check health factor after withdrawal
        pos.collateral -= amount;
        require(
            getHealthFactor(msg.sender) >= 100,
            "Would be undercollateralized"
        );

        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");

        emit Withdraw(msg.sender, address(0), amount);
    }

    /**
     * @notice Withdraw ERC20 tokens (allowed even when paused)
     */
    function withdrawToken(
        address token,
        uint256 amount
    ) external nonReentrant onlySupportedToken(token) {
        TokenCollateral storage tc = tokenCollateral[msg.sender][token];
        require(tc.deposited >= amount, "Insufficient balance");

        tc.deposited -= amount;
        totalDeposited[token] -= amount;

        // Check health factor after withdrawal
        require(
            getHealthFactor(msg.sender) >= 100,
            "Would be undercollateralized"
        );

        IERC20(token).safeTransfer(msg.sender, amount);

        emit Withdraw(msg.sender, token, amount);
    }

    // ========== BORROW FUNCTIONS ==========

    /**
     * @notice Borrow ERC20 tokens with variable rate
     */
    function borrow(
        address token,
        uint256 amount
    ) external virtual whenNotPaused nonReentrant onlySupportedToken(token) {
        _borrow(token, amount, RateMode.VARIABLE);
    }

    /**
     * @notice Borrow ERC20 tokens with chosen rate mode
     */
    function borrowWithMode(
        address token,
        uint256 amount,
        RateMode mode
    ) external virtual whenNotPaused nonReentrant onlySupportedToken(token) {
        _borrow(token, amount, mode);
    }

    function _borrow(address token, uint256 amount, RateMode mode) internal {
        require(amount > 0, "Must borrow > 0");
        require(
            totalDeposited[token] - totalBorrowed[token] >= amount,
            "Insufficient liquidity"
        );

        // Accrue interest first
        _accrueInterest(msg.sender, token);

        TokenCollateral storage tc = tokenCollateral[msg.sender][token];
        tc.borrowed += amount;
        tc.rateMode = mode;
        tc.lastUpdate = block.timestamp;

        if (mode == RateMode.STABLE) {
            tc.stableRate = interestRateModel.getStableRate(
                totalDeposited[token],
                totalBorrowed[token]
            );
            tc.stableRateLockTime = block.timestamp;
        }

        totalBorrowed[token] += amount;

        // Update position
        uint256 borrowValueUSD = priceOracle.convertTokenToUSD(token, amount);
        positions[msg.sender].borrowed += borrowValueUSD;
        positions[msg.sender].lastUpdate = block.timestamp;

        // Check health factor
        require(getHealthFactor(msg.sender) >= 100, "Undercollateralized");

        IERC20(token).safeTransfer(msg.sender, amount);

        emit Borrow(msg.sender, token, amount, mode);
    }

    // ========== REPAY FUNCTIONS ==========

    /**
     * @notice Repay borrowed tokens (allowed even when paused)
     */
    function repay(
        address token,
        uint256 amount
    ) external nonReentrant onlySupportedToken(token) {
        // Accrue interest first
        _accrueInterest(msg.sender, token);

        TokenCollateral storage tc = tokenCollateral[msg.sender][token];
        require(tc.borrowed > 0, "No debt");

        uint256 repayAmount = amount > tc.borrowed ? tc.borrowed : amount;

        IERC20(token).safeTransferFrom(msg.sender, address(this), repayAmount);

        tc.borrowed -= repayAmount;
        tc.lastUpdate = block.timestamp;
        totalBorrowed[token] -= repayAmount;

        // Update position
        uint256 repayValueUSD = priceOracle.convertTokenToUSD(
            token,
            repayAmount
        );
        if (repayValueUSD > positions[msg.sender].borrowed) {
            positions[msg.sender].borrowed = 0;
        } else {
            positions[msg.sender].borrowed -= repayValueUSD;
        }

        emit Repay(msg.sender, token, repayAmount);
    }

    // ========== RATE MODE FUNCTIONS ==========

    /**
     * @notice Switch between variable and stable rate modes
     */
    function switchRateMode(
        address token,
        RateMode newMode
    ) external whenNotPaused nonReentrant onlySupportedToken(token) {
        TokenCollateral storage tc = tokenCollateral[msg.sender][token];
        require(tc.borrowed > 0, "No active borrow");

        RateMode oldMode = tc.rateMode;
        require(oldMode != newMode, "Same rate mode");

        // If switching from stable, check lock period
        if (oldMode == RateMode.STABLE) {
            require(
                block.timestamp >=
                    tc.stableRateLockTime + STABLE_RATE_LOCK_PERIOD,
                "Stable rate still locked"
            );
        }

        // Accrue interest with old rate
        _accrueInterest(msg.sender, token);

        // Update to new rate mode
        tc.rateMode = newMode;

        if (newMode == RateMode.STABLE) {
            tc.stableRate = interestRateModel.getStableRate(
                totalDeposited[token],
                totalBorrowed[token]
            );
            tc.stableRateLockTime = block.timestamp;
        } else {
            tc.stableRate = 0;
            tc.stableRateLockTime = 0;
        }

        emit RateModeChanged(msg.sender, token, oldMode, newMode);
    }

    /**
     * @notice Rebalance a user's stable rate if it diverges too much
     */
    function rebalanceStableRate(
        address user,
        address token
    ) external whenNotPaused onlySupportedToken(token) {
        TokenCollateral storage tc = tokenCollateral[user][token];
        require(tc.rateMode == RateMode.STABLE, "Not stable mode");

        bool shouldRebalance = interestRateModel.shouldRebalanceStableRate(
            tc.stableRate,
            totalDeposited[token],
            totalBorrowed[token]
        );
        require(shouldRebalance, "Rebalance not needed");

        // Accrue interest with old rate
        _accrueInterest(user, token);

        // Update to new stable rate
        tc.stableRate = interestRateModel.getStableRate(
            totalDeposited[token],
            totalBorrowed[token]
        );
        tc.stableRateLockTime = block.timestamp;

        emit RateModeChanged(user, token, RateMode.STABLE, RateMode.STABLE);
    }

    // ========== INTEREST ACCRUAL ==========

    function _accrueInterest(address user, address token) internal {
        TokenCollateral storage tc = tokenCollateral[user][token];
        if (tc.borrowed == 0 || tc.lastUpdate == block.timestamp) return;

        uint256 timeElapsed = block.timestamp - tc.lastUpdate;

        // Get rate based on mode
        uint256 rate;
        if (tc.rateMode == RateMode.STABLE) {
            rate = tc.stableRate;
        } else {
            rate = interestRateModel.getVariableRate(
                totalDeposited[token],
                totalBorrowed[token]
            );
        }

        // Calculate interest (simple interest for clarity)
        // interest = principal * rate * time / (365 days * BASIS_POINTS)
        uint256 interest = (tc.borrowed * rate * timeElapsed) /
            (365 days * BASIS_POINTS);

        if (interest > 0) {
            // Split interest: reserve factor to reserves, rest to suppliers
            uint256 reserveShare = (interest * RESERVE_FACTOR) / BASIS_POINTS;
            reserves[token] += reserveShare;

            // Add interest to user's debt
            tc.borrowed += interest;
            totalBorrowed[token] += interest;

            // Update position
            uint256 interestValueUSD = priceOracle.convertTokenToUSD(
                token,
                interest
            );
            positions[user].borrowed += interestValueUSD;
        }

        tc.lastUpdate = block.timestamp;
    }

    // ========== LIQUIDATION ==========

    /**
     * @notice Liquidate an undercollateralized position
     */
    function liquidate(
        address user,
        address debtToken,
        uint256 debtAmount,
        address collateralToken
    )
        external
        whenNotPaused
        nonReentrant
        onlySupportedToken(debtToken)
        onlySupportedToken(collateralToken)
    {
        require(user != msg.sender, "Cannot liquidate self");

        // Check if position is liquidatable
        uint256 healthFactor = getHealthFactor(user);
        require(healthFactor < 100, "Position healthy");

        // Accrue interest first
        _accrueInterest(user, debtToken);

        TokenCollateral storage userDebt = tokenCollateral[user][debtToken];
        TokenCollateral storage userCollateral = tokenCollateral[user][
            collateralToken
        ];

        // Calculate max liquidatable (close factor)
        uint256 maxLiquidatable = (userDebt.borrowed * CLOSE_FACTOR) /
            BASIS_POINTS;
        uint256 actualDebt = debtAmount > maxLiquidatable
            ? maxLiquidatable
            : debtAmount;

        // Calculate collateral to seize (with bonus)
        uint256 debtValueUSD = priceOracle.convertTokenToUSD(
            debtToken,
            actualDebt
        );
        uint256 collateralValueWithBonus = (debtValueUSD *
            (BASIS_POINTS + LIQUIDATION_BONUS)) / BASIS_POINTS;
        uint256 collateralToSeize = priceOracle.convertUSDToToken(
            collateralToken,
            collateralValueWithBonus
        );

        require(
            userCollateral.deposited >= collateralToSeize,
            "Insufficient collateral"
        );

        // Transfer debt from liquidator
        IERC20(debtToken).safeTransferFrom(
            msg.sender,
            address(this),
            actualDebt
        );

        // Update user's debt
        userDebt.borrowed -= actualDebt;
        totalBorrowed[debtToken] -= actualDebt;

        // Update user's collateral
        userCollateral.deposited -= collateralToSeize;
        totalDeposited[collateralToken] -= collateralToSeize;

        // Transfer collateral to liquidator
        IERC20(collateralToken).safeTransfer(msg.sender, collateralToSeize);

        // Update position
        positions[user].borrowed -= debtValueUSD;

        emit Liquidation(
            msg.sender,
            user,
            debtToken,
            actualDebt,
            collateralToSeize
        );
    }

    // ========== FLASH LOANS ==========

    /**
     * @notice Execute a flash loan
     * @param token Token to borrow
     * @param amount Amount to borrow
     * @param receiver Contract that will receive the tokens
     * @param data Arbitrary data to pass to receiver
     */
    function flashLoan(
        address token,
        uint256 amount,
        address receiver,
        bytes calldata data
    ) external whenNotPaused nonReentrant onlySupportedToken(token) {
        require(amount > 0, "Amount must be > 0");

        uint256 balanceBefore = IERC20(token).balanceOf(address(this));
        require(balanceBefore >= amount, "Insufficient liquidity");

        // Calculate fee
        uint256 fee = (amount * FLASH_LOAN_FEE) / BASIS_POINTS;

        // Transfer tokens to receiver
        IERC20(token).safeTransfer(receiver, amount);

        // Call receiver's callback
        bool success = IFlashLoanReceiver(receiver).executeOperation(
            token,
            amount,
            fee,
            msg.sender,
            data
        );
        require(success, "Flash loan execution failed");

        // Check repayment
        uint256 balanceAfter = IERC20(token).balanceOf(address(this));
        require(balanceAfter >= balanceBefore + fee, "Flash loan not repaid");

        // Add fee to reserves
        reserves[token] += fee;

        emit FlashLoan(receiver, token, amount, fee);
    }

    // ========== HEALTH FACTOR ==========

    /**
     * @notice Calculate user's health factor using weighted collateral
     * @return Health factor (100 = threshold, >100 = safe, <100 = liquidatable)
     */
    function getHealthFactor(address user) public view returns (uint256) {
        uint256 totalCollateralUSD = 0;
        uint256 totalBorrowedUSD = positions[user].borrowed;

        // Add native ETH collateral (default 80% factor)
        if (positions[user].collateral > 0) {
            uint256 ethValueUSD = priceOracle.convertToUSD(
                positions[user].collateral
            );
            totalCollateralUSD += (ethValueUSD * 8000) / BASIS_POINTS; // 80% factor for ETH
        }

        // Add weighted token collateral
        for (uint256 i = 0; i < tokenList.length; i++) {
            address token = tokenList[i];
            uint256 deposited = tokenCollateral[user][token].deposited;

            if (deposited > 0) {
                uint256 tokenValueUSD = priceOracle.convertTokenToUSD(
                    token,
                    deposited
                );
                uint256 factor = collateralFactors[token];
                totalCollateralUSD += (tokenValueUSD * factor) / BASIS_POINTS;
            }
        }

        if (totalBorrowedUSD == 0) return type(uint256).max;

        // Health factor = (weighted collateral * liquidation threshold) / borrowed
        return
            (totalCollateralUSD * LIQUIDATION_THRESHOLD) /
            (totalBorrowedUSD * 100);
    }

    // ========== PAUSE MECHANISM ==========

    /**
     * @notice Pause critical functions (admin only)
     */
    function pause() external onlyOwner {
        require(!paused, "Already paused");
        paused = true;
        unpauseRequested = false;
        unpauseRequestTime = 0;
        emit Paused(msg.sender, block.timestamp);
    }

    /**
     * @notice Request unpause (starts timelock)
     */
    function requestUnpause() external onlyOwner {
        require(paused, "Not paused");
        require(!unpauseRequested, "Already requested");
        unpauseRequested = true;
        unpauseRequestTime = block.timestamp + UNPAUSE_TIMELOCK;
        emit UnpauseRequested(msg.sender, unpauseRequestTime);
    }

    /**
     * @notice Execute unpause (after timelock)
     */
    function unpause() external onlyOwner {
        require(paused, "Not paused");
        require(unpauseRequested, "Unpause not requested");
        require(block.timestamp >= unpauseRequestTime, "Timelock not expired");
        paused = false;
        unpauseRequested = false;
        unpauseRequestTime = 0;
        emit Unpaused(msg.sender, block.timestamp);
    }

    // ========== ADMIN FUNCTIONS ==========

    /**
     * @notice Add a supported token
     */
    function addToken(
        address token,
        uint256 _collateralFactor
    ) external onlyOwner {
        require(!supportedTokens[token], "Token already supported");
        require(_collateralFactor <= BASIS_POINTS, "Invalid factor");

        supportedTokens[token] = true;
        collateralFactors[token] = _collateralFactor;
        tokenList.push(token);

        emit TokenAdded(token, _collateralFactor);
    }

    /**
     * @notice Update collateral factor for a token
     */
    function setCollateralFactor(
        address token,
        uint256 factor
    ) external onlyOwner onlySupportedToken(token) {
        require(factor <= BASIS_POINTS, "Invalid factor");
        collateralFactors[token] = factor;
        emit CollateralFactorUpdated(token, factor);
    }

    /**
     * @notice Withdraw protocol reserves (governance only)
     */
    function withdrawReserves(
        address token,
        uint256 amount,
        address to
    ) external onlyOwner onlySupportedToken(token) {
        require(reserves[token] >= amount, "Insufficient reserves");
        reserves[token] -= amount;
        IERC20(token).safeTransfer(to, amount);
        emit ReservesWithdrawn(token, to, amount);
    }

    /**
     * @notice Update price oracle
     */
    function setPriceOracle(address _priceOracle) external onlyOwner {
        priceOracle = IMultiTokenPriceOracle(_priceOracle);
    }

    /**
     * @notice Update interest rate model
     */
    function setInterestRateModel(
        address _interestRateModel
    ) external onlyOwner {
        interestRateModel = InterestRateModel(_interestRateModel);
    }

    // ========== VIEW FUNCTIONS ==========

    /**
     * @notice Get current variable rate for a token
     */
    function getVariableRate(address token) external view returns (uint256) {
        return
            interestRateModel.getVariableRate(
                totalDeposited[token],
                totalBorrowed[token]
            );
    }

    /**
     * @notice Get current stable rate for a token
     */
    function getStableRate(address token) external view returns (uint256) {
        return
            interestRateModel.getStableRate(
                totalDeposited[token],
                totalBorrowed[token]
            );
    }

    /**
     * @notice Get supply rate for a token
     */
    function getSupplyRate(address token) external view returns (uint256) {
        return
            interestRateModel.getSupplyRate(
                totalDeposited[token],
                totalBorrowed[token],
                RESERVE_FACTOR
            );
    }

    /**
     * @notice Get utilization rate for a token
     */
    function getUtilization(address token) external view returns (uint256) {
        return
            interestRateModel.getUtilization(
                totalDeposited[token],
                totalBorrowed[token]
            );
    }

    /**
     * @notice Get user's token collateral info
     */
    function getUserTokenCollateral(
        address user,
        address token
    )
        external
        view
        returns (
            uint256 deposited,
            uint256 borrowed,
            RateMode rateMode,
            uint256 stableRate
        )
    {
        TokenCollateral storage tc = tokenCollateral[user][token];
        return (tc.deposited, tc.borrowed, tc.rateMode, tc.stableRate);
    }

    /**
     * @notice Get total collateral value in USD for a user
     */
    function getTotalCollateralUSD(
        address user
    ) external view returns (uint256 total) {
        // Native ETH
        if (positions[user].collateral > 0) {
            total += priceOracle.convertToUSD(positions[user].collateral);
        }

        // ERC20 tokens
        for (uint256 i = 0; i < tokenList.length; i++) {
            address token = tokenList[i];
            uint256 deposited = tokenCollateral[user][token].deposited;
            if (deposited > 0) {
                total += priceOracle.convertTokenToUSD(token, deposited);
            }
        }
    }

    /**
     * @notice Get all supported tokens
     */
    function getSupportedTokens() external view returns (address[] memory) {
        return tokenList;
    }

    // ========== CROSS-CHAIN ==========

    /**
     * @notice Execute cross-chain message from Axelar
     */
    function _execute(
        bytes32,
        string calldata sourceChain,
        string calldata,
        bytes calldata payload
    ) internal override {
        (address user, address token, uint256 amount) = abi.decode(
            payload,
            (address, address, uint256)
        );

        // Cross-chain deposit
        tokenCollateral[user][token].deposited += amount;
        totalDeposited[token] += amount;

        emit CrossChainDeposit(sourceChain, user, token, amount);
    }

    // ========== RECEIVE ==========

    receive() external payable {}
}
