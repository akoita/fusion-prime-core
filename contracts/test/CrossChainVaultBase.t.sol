// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import "forge-std/Test.sol";
import "lending/CrossChainVaultBase.sol";
import "lending/InterestRateModel.sol";
import "interfaces/IMultiTokenPriceOracle.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

// Mock ERC20 for testing
contract MockERC20 is ERC20 {
    uint8 private _decimals;

    constructor(
        string memory name,
        string memory symbol,
        uint8 decimals_
    ) ERC20(name, symbol) {
        _decimals = decimals_;
    }

    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }

    function decimals() public view override returns (uint8) {
        return _decimals;
    }
}

// Mock Price Oracle compatible with IMultiTokenPriceOracle
contract MockPriceOracle is IMultiTokenPriceOracle {
    mapping(address => uint256) public prices; // Price with 8 decimals
    mapping(address => uint8) public tokenDecs;
    mapping(address => bool) public supported;

    constructor() {
        // Set default ETH price
        prices[address(0)] = 2000e8; // $2000
        supported[address(0)] = true;
    }

    function setPrice(address token, uint256 price) external {
        prices[token] = price;
        supported[token] = true;
    }

    function setTokenDecimals(address token, uint8 decs) external {
        tokenDecs[token] = decs;
    }

    // IPriceOracle implementation
    function getNativePrice() external view override returns (uint256) {
        return prices[address(0)];
    }

    function convertToUSD(
        uint256 amount
    ) external view override returns (uint256) {
        return (amount * prices[address(0)]) / 1e8;
    }

    function convertFromUSD(
        uint256 usdValue
    ) external view override returns (uint256) {
        return (usdValue * 1e8) / prices[address(0)];
    }

    // IMultiTokenPriceOracle implementation
    function getTokenPrice(
        address token
    ) external view override returns (uint256) {
        require(supported[token], "Token not supported");
        return prices[token];
    }

    function convertTokenToUSD(
        address token,
        uint256 amount
    ) external view override returns (uint256) {
        uint256 price = prices[token];
        uint8 decs = tokenDecs[token];
        if (decs == 0) decs = 18;

        // Convert to 18 decimals USD
        if (decs < 18) {
            return ((amount * price) / 1e8) * (10 ** (18 - decs));
        } else if (decs > 18) {
            return (amount * price) / 1e8 / (10 ** (decs - 18));
        }
        return (amount * price) / 1e8;
    }

    function convertUSDToToken(
        address token,
        uint256 usdValue
    ) external view override returns (uint256) {
        uint256 price = prices[token];
        uint8 decs = tokenDecs[token];
        if (decs == 0) decs = 18;

        if (decs < 18) {
            return (usdValue * 1e8) / price / (10 ** (18 - decs));
        } else if (decs > 18) {
            return (usdValue * 1e8 * (10 ** (decs - 18))) / price;
        }
        return (usdValue * 1e8) / price;
    }

    function isTokenSupported(
        address token
    ) external view override returns (bool) {
        return supported[token];
    }

    function getTokenDecimals(
        address token
    ) external view override returns (uint8) {
        return tokenDecs[token] > 0 ? tokenDecs[token] : 18;
    }
}

// Mock Flash Loan Receiver
contract MockFlashLoanReceiver is IFlashLoanReceiver {
    bool public shouldSucceed = true;

    function executeOperation(
        address token,
        uint256 amount,
        uint256 fee,
        address,
        bytes calldata
    ) external override returns (bool) {
        if (!shouldSucceed) return false;

        // Repay flash loan + fee
        IERC20(token).transfer(msg.sender, amount + fee);
        return true;
    }

    function setSuccess(bool _success) external {
        shouldSucceed = _success;
    }
}

contract CrossChainVaultBaseTest is Test {
    CrossChainVaultBase public vault;
    InterestRateModel public rateModel;
    MockPriceOracle public oracle;
    MockERC20 public usdc;
    MockERC20 public dai;
    MockERC20 public weth;
    MockFlashLoanReceiver public flashReceiver;

    address public owner = address(this);
    address public user1 = address(0x1);
    address public user2 = address(0x2);
    address public liquidator = address(0x3);

    // Mock Axelar gateway (just needs to be non-zero)
    address public mockGateway = address(0x9999);
    address public mockGasService = address(0x8888);

    function setUp() public {
        // Deploy interest rate model
        rateModel = new InterestRateModel();

        // Deploy mock oracle
        oracle = new MockPriceOracle();

        // Deploy vault
        vault = new CrossChainVaultBase(
            mockGateway,
            mockGasService,
            address(oracle),
            address(rateModel)
        );

        // Deploy mock tokens
        usdc = new MockERC20("USD Coin", "USDC", 6);
        dai = new MockERC20("Dai Stablecoin", "DAI", 18);
        weth = new MockERC20("Wrapped Ether", "WETH", 18);

        // Set prices (8 decimals for Chainlink format)
        oracle.setPrice(address(usdc), 1e8); // $1
        oracle.setPrice(address(dai), 1e8); // $1
        oracle.setPrice(address(weth), 2000e8); // $2000
        oracle.setPrice(address(0), 2000e8); // ETH = $2000

        // Set token decimals
        oracle.setTokenDecimals(address(usdc), 6);
        oracle.setTokenDecimals(address(dai), 18);
        oracle.setTokenDecimals(address(weth), 18);

        // Add tokens to vault
        vault.addToken(address(usdc), 9000); // 90% collateral factor
        vault.addToken(address(dai), 9000); // 90%
        vault.addToken(address(weth), 8500); // 85%

        // Deploy flash loan receiver
        flashReceiver = new MockFlashLoanReceiver();

        // Fund test accounts
        vm.deal(user1, 100 ether);
        vm.deal(user2, 100 ether);
        vm.deal(liquidator, 100 ether);

        usdc.mint(user1, 100_000e6);
        usdc.mint(user2, 100_000e6);
        usdc.mint(liquidator, 100_000e6);

        dai.mint(user1, 100_000e18);
        dai.mint(user2, 100_000e18);

        weth.mint(user1, 100e18);
        weth.mint(user2, 100e18);
    }

    // ========== DEPOSIT TESTS ==========

    function testDepositETH() public {
        vm.prank(user1);
        vault.deposit{value: 1 ether}();

        (uint256 collateral, , , , , ) = vault.positions(user1);
        assertEq(collateral, 1 ether);
    }

    function testDepositToken() public {
        vm.startPrank(user1);
        usdc.approve(address(vault), 1000e6);
        vault.depositToken(address(usdc), 1000e6);
        vm.stopPrank();

        (uint256 deposited, , , ) = vault.getUserTokenCollateral(
            user1,
            address(usdc)
        );
        assertEq(deposited, 1000e6);
    }

    // ========== BORROW TESTS ==========

    function testBorrowVariable() public {
        // Setup: deposit collateral and liquidity
        _setupUserWithCollateral(user1, 10_000e6);
        _addLiquidity(user2, address(usdc), 50_000e6);

        // Borrow with variable rate
        vm.startPrank(user1);
        vault.borrow(address(usdc), 1000e6);
        vm.stopPrank();

        (, uint256 borrowed, CrossChainVaultBase.RateMode mode, ) = vault
            .getUserTokenCollateral(user1, address(usdc));
        assertEq(borrowed, 1000e6);
        assertEq(uint256(mode), uint256(CrossChainVaultBase.RateMode.VARIABLE));
    }

    function testBorrowStable() public {
        _setupUserWithCollateral(user1, 10_000e6);
        _addLiquidity(user2, address(usdc), 50_000e6);

        vm.startPrank(user1);
        vault.borrowWithMode(
            address(usdc),
            1000e6,
            CrossChainVaultBase.RateMode.STABLE
        );
        vm.stopPrank();

        (, , CrossChainVaultBase.RateMode mode, uint256 stableRate) = vault
            .getUserTokenCollateral(user1, address(usdc));
        assertEq(uint256(mode), uint256(CrossChainVaultBase.RateMode.STABLE));
        assertTrue(stableRate > 0);
    }

    // ========== RATE MODE TESTS ==========

    function testSwitchRateMode() public {
        _setupUserWithCollateral(user1, 10_000e6);
        _addLiquidity(user2, address(usdc), 50_000e6);

        // Borrow with variable
        vm.startPrank(user1);
        vault.borrow(address(usdc), 1000e6);

        // Switch to stable
        vault.switchRateMode(
            address(usdc),
            CrossChainVaultBase.RateMode.STABLE
        );
        vm.stopPrank();

        (, , CrossChainVaultBase.RateMode mode, ) = vault
            .getUserTokenCollateral(user1, address(usdc));
        assertEq(uint256(mode), uint256(CrossChainVaultBase.RateMode.STABLE));
    }

    function testCannotSwitchFromStableBeforeLockPeriod() public {
        _setupUserWithCollateral(user1, 10_000e6);
        _addLiquidity(user2, address(usdc), 50_000e6);

        vm.startPrank(user1);
        vault.borrowWithMode(
            address(usdc),
            1000e6,
            CrossChainVaultBase.RateMode.STABLE
        );

        // Try to switch back to variable before 30 days
        vm.expectRevert("Stable rate still locked");
        vault.switchRateMode(
            address(usdc),
            CrossChainVaultBase.RateMode.VARIABLE
        );
        vm.stopPrank();
    }

    function testCanSwitchFromStableAfterLockPeriod() public {
        _setupUserWithCollateral(user1, 10_000e6);
        _addLiquidity(user2, address(usdc), 50_000e6);

        vm.startPrank(user1);
        vault.borrowWithMode(
            address(usdc),
            1000e6,
            CrossChainVaultBase.RateMode.STABLE
        );

        // Fast forward 31 days
        vm.warp(block.timestamp + 31 days);

        vault.switchRateMode(
            address(usdc),
            CrossChainVaultBase.RateMode.VARIABLE
        );
        vm.stopPrank();

        (, , CrossChainVaultBase.RateMode mode, ) = vault
            .getUserTokenCollateral(user1, address(usdc));
        assertEq(uint256(mode), uint256(CrossChainVaultBase.RateMode.VARIABLE));
    }

    // ========== INTEREST RATE TESTS ==========

    function testVariableRateCalculation() public view {
        uint256 rate = rateModel.getVariableRate(100_000e6, 50_000e6); // 50% utilization
        assertTrue(rate > 200); // Should be above base rate
        assertTrue(rate < 10000); // Should be reasonable
    }

    function testStableRateCalculation() public view {
        uint256 variableRate = rateModel.getVariableRate(100_000e6, 50_000e6);
        uint256 stableRate = rateModel.getStableRate(100_000e6, 50_000e6);

        // Stable rate should be higher (10% premium)
        assertTrue(stableRate > variableRate);
        assertEq(stableRate, variableRate + ((variableRate * 1000) / 10000));
    }

    // ========== RESERVE FACTOR TESTS ==========

    function testReservesAccumulate() public {
        _setupUserWithCollateral(user1, 10_000e6);
        _addLiquidity(user2, address(usdc), 50_000e6);

        vm.prank(user1);
        vault.borrow(address(usdc), 1000e6);

        // Fast forward 1 year
        vm.warp(block.timestamp + 365 days);

        // Trigger interest accrual by repaying
        vm.startPrank(user1);
        usdc.approve(address(vault), type(uint256).max);
        vault.repay(address(usdc), 1); // Repay 1 wei to trigger accrual
        vm.stopPrank();

        uint256 reserves = vault.reserves(address(usdc));
        assertTrue(reserves > 0, "Reserves should accumulate");
    }

    function testWithdrawReserves() public {
        _setupUserWithCollateral(user1, 10_000e6);
        _addLiquidity(user2, address(usdc), 50_000e6);

        vm.prank(user1);
        vault.borrow(address(usdc), 1000e6);

        // Fast forward to accumulate interest
        vm.warp(block.timestamp + 365 days);

        // Trigger accrual
        vm.startPrank(user1);
        usdc.approve(address(vault), type(uint256).max);
        vault.repay(address(usdc), 1);
        vm.stopPrank();

        uint256 reserves = vault.reserves(address(usdc));
        if (reserves > 0) {
            address treasury = address(0x5555);
            vault.withdrawReserves(address(usdc), reserves, treasury);
            assertEq(usdc.balanceOf(treasury), reserves);
        }
    }

    // ========== PAUSE MECHANISM TESTS ==========

    function testPause() public {
        vault.pause();
        assertTrue(vault.paused());
    }

    function testCannotDepositWhenPaused() public {
        vault.pause();

        vm.prank(user1);
        vm.expectRevert("Contract is paused");
        vault.deposit{value: 1 ether}();
    }

    function testCanWithdrawWhenPaused() public {
        // Deposit first
        vm.prank(user1);
        vault.deposit{value: 1 ether}();

        // Pause
        vault.pause();

        // Should still be able to withdraw
        vm.prank(user1);
        vault.withdraw(0.5 ether);

        (uint256 collateral, , , , , ) = vault.positions(user1);
        assertEq(collateral, 0.5 ether);
    }

    function testCanRepayWhenPaused() public {
        _setupUserWithCollateral(user1, 10_000e6);
        _addLiquidity(user2, address(usdc), 50_000e6);

        vm.prank(user1);
        vault.borrow(address(usdc), 1000e6);

        // Pause
        vault.pause();

        // Should still be able to repay
        vm.startPrank(user1);
        usdc.approve(address(vault), 1000e6);
        vault.repay(address(usdc), 500e6);
        vm.stopPrank();
    }

    function testUnpauseTimelock() public {
        vault.pause();

        vault.requestUnpause();
        assertTrue(vault.unpauseRequested());

        // Try to unpause immediately - should fail
        vm.expectRevert("Timelock not expired");
        vault.unpause();

        // Fast forward 24 hours
        vm.warp(block.timestamp + 24 hours);

        // Now unpause should work
        vault.unpause();
        assertFalse(vault.paused());
    }

    // ========== FLASH LOAN TESTS ==========

    function testFlashLoan() public {
        // Add liquidity
        _addLiquidity(user2, address(usdc), 50_000e6);

        // Fund flash receiver to pay fee
        usdc.mint(address(flashReceiver), 1000e6);

        // Execute flash loan
        vault.flashLoan(address(usdc), 10_000e6, address(flashReceiver), "");

        // Check that fee was collected
        uint256 expectedFee = (10_000e6 * 9) / 10000; // 0.09%
        assertGe(vault.reserves(address(usdc)), expectedFee);
    }

    function testFlashLoanFailsWithoutRepayment() public {
        _addLiquidity(user2, address(usdc), 50_000e6);

        // Make flash receiver fail
        flashReceiver.setSuccess(false);

        vm.expectRevert("Flash loan execution failed");
        vault.flashLoan(address(usdc), 10_000e6, address(flashReceiver), "");
    }

    // ========== HEALTH FACTOR TESTS ==========

    function testHealthFactorNoDebt() public {
        // Deposit USDC as collateral
        vm.startPrank(user1);
        usdc.approve(address(vault), 10_000e6);
        vault.depositToken(address(usdc), 10_000e6);
        vm.stopPrank();

        // Health factor should be max (no borrows)
        uint256 hf = vault.getHealthFactor(user1);
        assertEq(hf, type(uint256).max);
    }

    function testCollateralFactorUpdate() public {
        // Update collateral factor
        vault.setCollateralFactor(address(usdc), 5000); // 50%

        assertEq(vault.collateralFactors(address(usdc)), 5000);
    }

    // ========== LIQUIDATION TESTS ==========

    function testLiquidateUndercollateralizedPosition() public {
        // Setup: user1 deposits and borrows
        _setupUserWithCollateral(user1, 10_000e6);
        _addLiquidity(user2, address(usdc), 50_000e6);

        vm.prank(user1);
        vault.borrow(address(usdc), 5_000e6);

        // Drop price to make position undercollateralized
        oracle.setPrice(address(usdc), 0.5e8); // USDC drops to $0.50

        // Verify health factor < 100
        uint256 hf = vault.getHealthFactor(user1);
        assertLt(hf, 100, "Position should be liquidatable");

        // Liquidator repays debt and seizes collateral
        vm.startPrank(liquidator);
        usdc.approve(address(vault), type(uint256).max);
        vault.liquidate(user1, address(usdc), 2_500e6, address(usdc));
        vm.stopPrank();

        // Verify debt was reduced
        (, uint256 borrowed, , ) = vault.getUserTokenCollateral(
            user1,
            address(usdc)
        );
        assertLt(borrowed, 5_000e6, "Debt should be reduced");
    }

    function testCannotLiquidateHealthyPosition() public {
        _setupUserWithCollateral(user1, 10_000e6);
        _addLiquidity(user2, address(usdc), 50_000e6);

        vm.prank(user1);
        vault.borrow(address(usdc), 1_000e6); // Low LTV, healthy

        uint256 hf = vault.getHealthFactor(user1);
        assertGe(hf, 100, "Position should be healthy");

        vm.startPrank(liquidator);
        usdc.approve(address(vault), type(uint256).max);
        vm.expectRevert("Position healthy");
        vault.liquidate(user1, address(usdc), 500e6, address(usdc));
        vm.stopPrank();
    }

    function testCannotLiquidateSelf() public {
        _setupUserWithCollateral(user1, 10_000e6);
        _addLiquidity(user2, address(usdc), 50_000e6);

        vm.prank(user1);
        vault.borrow(address(usdc), 5_000e6);

        oracle.setPrice(address(usdc), 0.5e8);

        vm.startPrank(user1);
        usdc.approve(address(vault), type(uint256).max);
        vm.expectRevert("Cannot liquidate self");
        vault.liquidate(user1, address(usdc), 1_000e6, address(usdc));
        vm.stopPrank();
    }

    function testLiquidationRespectsCloseFactor() public {
        _setupUserWithCollateral(user1, 10_000e6);
        _addLiquidity(user2, address(usdc), 50_000e6);

        vm.prank(user1);
        vault.borrow(address(usdc), 5_000e6);

        oracle.setPrice(address(usdc), 0.5e8);

        // Try to liquidate more than close factor (50%)
        vm.startPrank(liquidator);
        usdc.approve(address(vault), type(uint256).max);
        vault.liquidate(user1, address(usdc), 5_000e6, address(usdc)); // Request full, should cap
        vm.stopPrank();

        // Should only liquidate up to close factor
        (, uint256 borrowed, , ) = vault.getUserTokenCollateral(
            user1,
            address(usdc)
        );
        assertGe(borrowed, 2_500e6, "Should respect close factor");
    }

    // ========== SECURITY EDGE CASE TESTS ==========

    function testCannotWithdrawBelowHealthFactor() public {
        _setupUserWithCollateral(user1, 10_000e6);
        _addLiquidity(user2, address(usdc), 50_000e6);

        vm.prank(user1);
        vault.borrow(address(usdc), 5_000e6);

        // Try to withdraw too much
        vm.prank(user1);
        vm.expectRevert("Would be undercollateralized");
        vault.withdrawToken(address(usdc), 9_000e6);
    }

    function testCannotBorrowBeyondCollateral() public {
        _setupUserWithCollateral(user1, 1_000e6); // Only $1000 collateral
        _addLiquidity(user2, address(usdc), 50_000e6);

        // Try to borrow more than collateral allows
        vm.prank(user1);
        vm.expectRevert("Undercollateralized");
        vault.borrow(address(usdc), 5_000e6);
    }

    function testCannotDepositZeroAmount() public {
        vm.prank(user1);
        vm.expectRevert("Must deposit > 0");
        vault.deposit{value: 0}();
    }

    function testCannotBorrowZeroAmount() public {
        _setupUserWithCollateral(user1, 10_000e6);
        _addLiquidity(user2, address(usdc), 50_000e6);

        vm.prank(user1);
        vm.expectRevert("Must borrow > 0");
        vault.borrow(address(usdc), 0);
    }

    function testCannotRepayWithNoDebt() public {
        _setupUserWithCollateral(user1, 10_000e6);

        vm.startPrank(user1);
        usdc.approve(address(vault), type(uint256).max);
        vm.expectRevert("No debt");
        vault.repay(address(usdc), 1_000e6);
        vm.stopPrank();
    }

    function testCannotWithdrawMoreThanDeposited() public {
        vm.prank(user1);
        vault.deposit{value: 1 ether}();

        vm.prank(user1);
        vm.expectRevert("Insufficient collateral");
        vault.withdraw(2 ether);
    }

    // ========== ADMIN ACCESS CONTROL TESTS ==========

    function testOnlyOwnerCanPause() public {
        vm.prank(user1);
        vm.expectRevert();
        vault.pause();
    }

    function testOnlyOwnerCanAddToken() public {
        MockERC20 newToken = new MockERC20("New Token", "NEW", 18);

        vm.prank(user1);
        vm.expectRevert();
        vault.addToken(address(newToken), 8000);
    }

    function testOnlyOwnerCanSetCollateralFactor() public {
        vm.prank(user1);
        vm.expectRevert();
        vault.setCollateralFactor(address(usdc), 5000);
    }

    function testOnlyOwnerCanWithdrawReserves() public {
        vm.prank(user1);
        vm.expectRevert();
        vault.withdrawReserves(address(usdc), 100e6, user1);
    }

    function testOnlyOwnerCanSetPriceOracle() public {
        vm.prank(user1);
        vm.expectRevert();
        vault.setPriceOracle(address(0x123));
    }

    function testOnlyOwnerCanSetInterestRateModel() public {
        vm.prank(user1);
        vm.expectRevert();
        vault.setInterestRateModel(address(0x123));
    }

    function testCannotAddDuplicateToken() public {
        vm.expectRevert("Token already supported");
        vault.addToken(address(usdc), 8000);
    }

    function testCannotSetInvalidCollateralFactor() public {
        vm.expectRevert("Invalid factor");
        vault.addToken(address(0x999), 15000); // > 100%
    }

    // ========== HELPER FUNCTIONS ==========

    function _setupUserWithCollateral(
        address user,
        uint256 usdcAmount
    ) internal {
        vm.startPrank(user);
        usdc.approve(address(vault), usdcAmount);
        vault.depositToken(address(usdc), usdcAmount);
        vm.stopPrank();
    }

    function _addLiquidity(
        address provider,
        address token,
        uint256 amount
    ) internal {
        vm.startPrank(provider);
        IERC20(token).approve(address(vault), amount);
        vault.depositToken(token, amount);
        vm.stopPrank();
    }
}
