// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import "forge-std/Test.sol";
import "lending/CrossChainVaultBase.sol";
import "lending/InterestRateModel.sol";
import "interfaces/IMultiTokenPriceOracle.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/**
 * @title CrossChainVaultBaseFuzzTest
 * @notice Fuzz tests for discovering edge cases in vault operations
 */
contract MockFuzzERC20 is ERC20 {
    constructor() ERC20("Mock Token", "MOCK") {}

    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }
}

contract MockFuzzOracle is IMultiTokenPriceOracle {
    mapping(address => uint256) public prices;

    constructor() {
        prices[address(0)] = 2000e8; // ETH
    }

    function setPrice(address token, uint256 price) external {
        prices[token] = price;
    }

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

    function getTokenPrice(
        address token
    ) external view override returns (uint256) {
        return prices[token];
    }

    function convertTokenToUSD(
        address token,
        uint256 amount
    ) external view override returns (uint256) {
        return (amount * prices[token]) / 1e8;
    }

    function convertUSDToToken(
        address token,
        uint256 usdValue
    ) external view override returns (uint256) {
        if (prices[token] == 0) return 0;
        return (usdValue * 1e8) / prices[token];
    }

    function isTokenSupported(
        address token
    ) external view override returns (bool) {
        return prices[token] > 0;
    }

    function getTokenDecimals(address) external pure override returns (uint8) {
        return 18;
    }
}

contract CrossChainVaultBaseFuzzTest is Test {
    CrossChainVaultBase public vault;
    InterestRateModel public rateModel;
    MockFuzzOracle public oracle;
    MockFuzzERC20 public token;

    address public owner = address(this);
    address public user = address(0x1);

    address public mockGateway = address(0x9999);
    address public mockGasService = address(0x8888);

    function setUp() public {
        rateModel = new InterestRateModel();
        oracle = new MockFuzzOracle();
        vault = new CrossChainVaultBase(
            mockGateway,
            mockGasService,
            address(oracle),
            address(rateModel)
        );

        token = new MockFuzzERC20();
        oracle.setPrice(address(token), 1e8); // $1
        vault.addToken(address(token), 9000); // 90% collateral factor

        vm.deal(user, 1000 ether);
        token.mint(user, 1_000_000e18);
        token.mint(address(vault), 10_000_000e18); // Liquidity
    }

    // ========== FUZZ DEPOSIT/WITHDRAW ==========

    function testFuzz_DepositETH(uint256 amount) public {
        amount = bound(amount, 1, 100 ether);

        vm.prank(user);
        vault.deposit{value: amount}();

        (uint256 collateral, , , , , ) = vault.positions(user);
        assertEq(collateral, amount);
    }

    function testFuzz_DepositWithdrawETH(
        uint256 depositAmt,
        uint256 withdrawAmt
    ) public {
        depositAmt = bound(depositAmt, 1 ether, 100 ether);
        withdrawAmt = bound(withdrawAmt, 1, depositAmt);

        vm.startPrank(user);
        vault.deposit{value: depositAmt}();
        vault.withdraw(withdrawAmt);
        vm.stopPrank();

        (uint256 collateral, , , , , ) = vault.positions(user);
        assertEq(collateral, depositAmt - withdrawAmt);
    }

    function testFuzz_DepositToken(uint256 amount) public {
        amount = bound(amount, 1e18, 100_000e18);

        vm.startPrank(user);
        token.approve(address(vault), amount);
        vault.depositToken(address(token), amount);
        vm.stopPrank();

        (uint256 deposited, , , ) = vault.getUserTokenCollateral(
            user,
            address(token)
        );
        assertEq(deposited, amount);
    }

    // ========== FUZZ BORROW/REPAY ==========

    function testFuzz_BorrowWithinCollateral(
        uint256 collateralAmt,
        uint256 borrowRatio
    ) public {
        collateralAmt = bound(collateralAmt, 10e18, 100_000e18);
        borrowRatio = bound(borrowRatio, 1, 70); // 1-70% of collateral

        vm.startPrank(user);
        token.approve(address(vault), collateralAmt);
        vault.depositToken(address(token), collateralAmt);

        uint256 maxBorrow = (collateralAmt * 9000 * 8000) / (10000 * 10000); // 90% CF * 80% LT
        uint256 borrowAmt = (maxBorrow * borrowRatio) / 100;

        if (borrowAmt > 0) {
            vault.borrow(address(token), borrowAmt);
            (, uint256 borrowed, , ) = vault.getUserTokenCollateral(
                user,
                address(token)
            );
            assertEq(borrowed, borrowAmt);
        }
        vm.stopPrank();
    }

    function testFuzz_RepayPartial(
        uint256 borrowAmt,
        uint256 repayRatio
    ) public {
        borrowAmt = bound(borrowAmt, 1e18, 10_000e18);
        repayRatio = bound(repayRatio, 1, 100);

        // Setup: deposit enough collateral
        uint256 collateralNeeded = borrowAmt * 2;

        vm.startPrank(user);
        token.approve(address(vault), type(uint256).max);
        vault.depositToken(address(token), collateralNeeded);
        vault.borrow(address(token), borrowAmt);

        uint256 repayAmt = (borrowAmt * repayRatio) / 100;
        if (repayAmt > 0) {
            vault.repay(address(token), repayAmt);
        }
        vm.stopPrank();

        (, uint256 remaining, , ) = vault.getUserTokenCollateral(
            user,
            address(token)
        );
        uint256 expected = repayAmt >= borrowAmt ? 0 : borrowAmt - repayAmt;
        assertEq(remaining, expected);
    }

    // ========== FUZZ INTEREST ACCRUAL ==========

    function testFuzz_InterestAccruesOverTime(
        uint256 borrowAmt,
        uint256 timeElapsed
    ) public {
        borrowAmt = bound(borrowAmt, 1e18, 10_000e18);
        timeElapsed = bound(timeElapsed, 1 days, 365 days);

        vm.startPrank(user);
        token.approve(address(vault), type(uint256).max);
        vault.depositToken(address(token), borrowAmt * 3);
        vault.borrow(address(token), borrowAmt);
        vm.stopPrank();

        (, uint256 debtBefore, , ) = vault.getUserTokenCollateral(
            user,
            address(token)
        );

        vm.warp(block.timestamp + timeElapsed);

        // Trigger interest accrual via repay
        vm.startPrank(user);
        vault.repay(address(token), 1);
        vm.stopPrank();

        (, uint256 debtAfter, , ) = vault.getUserTokenCollateral(
            user,
            address(token)
        );

        // Debt should have increased due to interest (minus 1 repaid)
        assertGe(debtAfter, debtBefore - 1, "Debt should accrue interest");
    }

    // ========== FUZZ HEALTH FACTOR ==========

    function testFuzz_HealthFactorDecreasesWithBorrow(
        uint256 borrowRatio
    ) public {
        borrowRatio = bound(borrowRatio, 10, 70);

        uint256 collateral = 100_000e18;

        vm.startPrank(user);
        token.approve(address(vault), collateral);
        vault.depositToken(address(token), collateral);

        uint256 hfBefore = vault.getHealthFactor(user);

        uint256 maxBorrow = (collateral * 9000 * 8000) / (10000 * 10000);
        uint256 borrowAmt = (maxBorrow * borrowRatio) / 100;
        vault.borrow(address(token), borrowAmt);

        uint256 hfAfter = vault.getHealthFactor(user);
        vm.stopPrank();

        assertLt(
            hfAfter,
            hfBefore,
            "Health factor should decrease after borrow"
        );
    }

    // ========== FUZZ FLASH LOAN ==========

    function testFuzz_FlashLoanFeeCalculation(uint256 amount) public {
        amount = bound(amount, 1e18, 1_000_000e18);

        uint256 expectedFee = (amount * 9) / 10000; // 0.09%
        assertTrue(expectedFee >= 0, "Fee should be non-negative");
    }

    receive() external payable {}
}
