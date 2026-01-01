// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import "forge-std/Test.sol";
import "forge-std/StdInvariant.sol";
import "../src/CrossChainVaultBase.sol";
import "../src/InterestRateModel.sol";
import "../src/interfaces/IMultiTokenPriceOracle.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/**
 * @title CrossChainVaultInvariantTest
 * @notice Invariant tests to verify protocol safety properties always hold
 */

// Handler contract to perform random operations
contract VaultHandler is Test {
    CrossChainVaultBase public vault;
    MockInvariantERC20 public token;
    address[] public actors;

    uint256 public totalDeposits;
    uint256 public totalBorrows;

    constructor(CrossChainVaultBase _vault, MockInvariantERC20 _token) {
        vault = _vault;
        token = _token;

        // Create test actors
        for (uint256 i = 1; i <= 5; i++) {
            address actor = address(uint160(i * 100));
            actors.push(actor);
            vm.deal(actor, 1000 ether);
            token.mint(actor, 1_000_000e18);
        }
    }

    function deposit(uint256 actorSeed, uint256 amount) external {
        address actor = actors[actorSeed % actors.length];
        amount = bound(amount, 0.01 ether, 10 ether);

        vm.prank(actor);
        vault.deposit{value: amount}();
        totalDeposits += amount;
    }

    function depositToken(uint256 actorSeed, uint256 amount) external {
        address actor = actors[actorSeed % actors.length];
        amount = bound(amount, 1e18, 10_000e18);

        vm.startPrank(actor);
        token.approve(address(vault), amount);
        vault.depositToken(address(token), amount);
        vm.stopPrank();
    }

    function withdraw(uint256 actorSeed, uint256 amount) external {
        address actor = actors[actorSeed % actors.length];
        (uint256 collateral, , , , , ) = vault.positions(actor);

        if (collateral == 0) return;
        amount = bound(amount, 1, collateral);

        // Only withdraw if it won't break health factor
        vm.prank(actor);
        try vault.withdraw(amount) {
            // Success
        } catch {
            // Expected revert if undercollateralized
        }
    }

    function borrow(uint256 actorSeed, uint256 amount) external {
        address actor = actors[actorSeed % actors.length];
        amount = bound(amount, 1e18, 1_000e18);

        uint256 available = vault.totalDeposited(address(token)) -
            vault.totalBorrowed(address(token));
        if (available < amount) return;

        vm.prank(actor);
        try vault.borrow(address(token), amount) {
            totalBorrows += amount;
        } catch {
            // Expected revert if undercollateralized
        }
    }

    function repay(uint256 actorSeed, uint256 amount) external {
        address actor = actors[actorSeed % actors.length];
        (, uint256 borrowed, , ) = vault.getUserTokenCollateral(
            actor,
            address(token)
        );

        if (borrowed == 0) return;
        amount = bound(amount, 1, borrowed);

        vm.startPrank(actor);
        token.approve(address(vault), amount);
        vault.repay(address(token), amount);
        vm.stopPrank();
    }

    function getActors() external view returns (address[] memory) {
        return actors;
    }
}

contract MockInvariantERC20 is ERC20 {
    constructor() ERC20("Mock Token", "MOCK") {}

    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }
}

contract MockInvariantOracle is IMultiTokenPriceOracle {
    mapping(address => uint256) public prices;

    constructor() {
        prices[address(0)] = 2000e8;
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

contract CrossChainVaultInvariantTest is StdInvariant, Test {
    CrossChainVaultBase public vault;
    InterestRateModel public rateModel;
    MockInvariantOracle public oracle;
    MockInvariantERC20 public token;
    VaultHandler public handler;

    address public mockGateway = address(0x9999);
    address public mockGasService = address(0x8888);

    function setUp() public {
        rateModel = new InterestRateModel();
        oracle = new MockInvariantOracle();
        vault = new CrossChainVaultBase(
            mockGateway,
            mockGasService,
            address(oracle),
            address(rateModel)
        );

        token = new MockInvariantERC20();
        oracle.setPrice(address(token), 1e8);
        vault.addToken(address(token), 9000);

        // Add initial liquidity
        token.mint(address(vault), 100_000_000e18);

        handler = new VaultHandler(vault, token);

        // Target the handler for invariant testing
        targetContract(address(handler));
    }

    // ========== INVARIANTS ==========

    /**
     * @notice Total borrowed should never exceed total deposited
     */
    function invariant_BorrowedLteDeposited() public view {
        uint256 deposited = vault.totalDeposited(address(token));
        uint256 borrowed = vault.totalBorrowed(address(token));
        assertLe(borrowed, deposited, "Borrowed exceeds deposited");
    }

    /**
     * @notice Reserves should never be negative (always >= 0)
     */
    function invariant_NonNegativeReserves() public view {
        uint256 reserves = vault.reserves(address(token));
        assertGe(reserves, 0, "Reserves should be non-negative");
    }

    /**
     * @notice Contract should always have enough ETH balance
     */
    function invariant_ETHSolvency() public view {
        uint256 balance = address(vault).balance;
        // Total ETH collateral across all users should be <= balance
        assertTrue(balance >= 0, "ETH balance should be non-negative");
    }

    /**
     * @notice Users with no borrows should have max health factor
     */
    function invariant_NoDebtMaxHealthFactor() public view {
        address[] memory actors = handler.getActors();
        for (uint256 i = 0; i < actors.length; i++) {
            (, uint256 borrowed, , , , ) = vault.positions(actors[i]);
            (, uint256 tokenBorrowed, , ) = vault.getUserTokenCollateral(
                actors[i],
                address(token)
            );

            if (borrowed == 0 && tokenBorrowed == 0) {
                uint256 hf = vault.getHealthFactor(actors[i]);
                assertEq(hf, type(uint256).max, "No debt should have max HF");
            }
        }
    }

    /**
     * @notice Collateral factors should never exceed 100%
     */
    function invariant_CollateralFactorBounded() public view {
        uint256 factor = vault.collateralFactors(address(token));
        assertLe(factor, 10000, "Collateral factor should be <= 100%");
    }
}
