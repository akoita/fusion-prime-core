// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import "forge-std/Test.sol";
import "adapters/AaveV3Adapter.sol";
import "adapters/CompoundV3Adapter.sol";
import "adapters/MorphoAdapter.sol";
import "interfaces/ILiquiditySource.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @title ExternalProtocolsTest
 * @notice Fork tests for external protocol adapters (Aave, Compound, Morpho)
 * @dev Run with: forge test --match-contract ExternalProtocolsTest --fork-url $ETH_RPC_URL -vvv
 *
 * These tests require a mainnet fork to interact with real deployed contracts.
 * Set ETH_RPC_URL to an Ethereum mainnet RPC endpoint.
 */
contract ExternalProtocolsTest is Test {
    // ============ Mainnet Addresses ============

    // Aave V3 - Ethereum Mainnet
    address constant AAVE_POOL = 0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2;
    address constant AAVE_DATA_PROVIDER =
        0x7B4EB56E7CD4b454BA8ff71E4518426369a138a3;

    // Compound V3 - USDC Market
    address constant COMPOUND_USDC_COMET =
        0xc3d688B66703497DAA19211EEdff47f25384cdc3;

    // Morpho Blue - Ethereum Mainnet
    address constant MORPHO = 0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb;

    // Tokens
    address constant WETH = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2;
    address constant USDC = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48;
    address constant DAI = 0x6b175474E89094c44dA98B954eEDecD73ABc4300;

    // Aave aTokens
    address constant A_WETH = 0x4d5F47FA6A74757f35C14fD3a6Ef8E3C9BC514E8;
    address constant A_USDC = 0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c;

    // Adapters
    AaveV3Adapter public aaveAdapter;
    CompoundV3Adapter public compoundAdapter;
    MorphoAdapter public morphoAdapter;

    // Test addresses
    address public owner = address(this);
    address public user1 = address(0x1);
    address public whale = 0x8EB8a3b98659Cce290402893d0123abb75E3ab28; // Binance hot wallet

    // Fork block
    uint256 constant FORK_BLOCK = 19000000; // Early 2024

    function setUp() public {
        // Only run on mainnet fork
        if (block.chainid != 1) {
            return;
        }

        // Deploy adapters
        aaveAdapter = new AaveV3Adapter(AAVE_POOL, AAVE_DATA_PROVIDER, WETH);
        compoundAdapter = new CompoundV3Adapter(WETH);
        morphoAdapter = new MorphoAdapter(MORPHO, WETH);

        // Configure Aave adapter
        aaveAdapter.addSupportedToken(WETH, A_WETH);
        aaveAdapter.addSupportedToken(USDC, A_USDC);

        // Configure Compound adapter
        compoundAdapter.addComet(COMPOUND_USDC_COMET);

        // Fund test user
        vm.deal(user1, 100 ether);
    }

    // ============ Aave V3 Tests ============

    function test_Aave_GetAvailableLiquidity() public {
        if (block.chainid != 1) return; // Skip if not forked

        uint256 available = aaveAdapter.getAvailableLiquidity(WETH);

        // Aave should have significant ETH liquidity
        assertGt(available, 1000 ether, "Should have >1000 ETH available");
        console.log("Aave WETH available:", available / 1e18, "ETH");
    }

    function test_Aave_GetQuote() public {
        if (block.chainid != 1) return;

        ILiquiditySource.LiquidityQuote memory quote = aaveAdapter.getQuote(
            WETH,
            10 ether
        );

        assertEq(
            uint(quote.sourceType),
            uint(ILiquiditySource.SourceType.EXTERNAL_AAVE)
        );
        assertEq(quote.feeBps, 0, "Aave has no upfront fee");
        assertEq(quote.estimatedTime, 0, "Aave is instant");
        assertGt(quote.rateAPY, 0, "Should have positive APY");

        console.log("Aave WETH borrow APY:");
        console.log(quote.rateAPY);
        console.log("bps =");
        console.log(quote.rateAPY / 100);
    }

    function test_Aave_GetCurrentAPY() public {
        if (block.chainid != 1) return;

        uint256 wethAPY = aaveAdapter.getCurrentAPY(WETH);
        uint256 usdcAPY = aaveAdapter.getCurrentAPY(USDC);

        console.log("Aave WETH APY:");
        console.log(wethAPY);
        console.log("bps =");
        console.log(wethAPY / 100);
        console.log("Aave USDC APY:");
        console.log(usdcAPY);
        console.log("bps =");
        console.log(usdcAPY / 100);

        // APYs should be reasonable (0.1% - 20%)
        assertGt(wethAPY, 10, "WETH APY should be > 0.1%");
        assertLt(wethAPY, 2000, "WETH APY should be < 20%");
    }

    function test_Aave_SupportsToken() public {
        if (block.chainid != 1) return;

        assertTrue(aaveAdapter.supportsToken(WETH));
        assertTrue(aaveAdapter.supportsToken(USDC));
        assertFalse(aaveAdapter.supportsToken(address(0x123))); // Random unsupported
    }

    // ============ Compound V3 Tests ============

    function test_Compound_GetAvailableLiquidity() public {
        if (block.chainid != 1) return;

        uint256 available = compoundAdapter.getAvailableLiquidity(USDC);

        // Compound USDC market should have significant liquidity
        assertGt(available, 1_000_000 * 1e6, "Should have >1M USDC available");
        console.log("Compound USDC available:", available / 1e6, "USDC");
    }

    function test_Compound_GetQuote() public {
        if (block.chainid != 1) return;

        ILiquiditySource.LiquidityQuote memory quote = compoundAdapter.getQuote(
            USDC,
            10_000 * 1e6
        );

        assertEq(
            uint(quote.sourceType),
            uint(ILiquiditySource.SourceType.EXTERNAL_COMPOUND)
        );
        assertEq(quote.feeBps, 0);
        assertEq(quote.estimatedTime, 0);
        assertGt(quote.rateAPY, 0);

        console.log("Compound USDC borrow APY:");
        console.log(quote.rateAPY);
        console.log("bps =");
        console.log(quote.rateAPY / 100);
    }

    function test_Compound_GetCurrentAPY() public {
        if (block.chainid != 1) return;

        uint256 usdcAPY = compoundAdapter.getCurrentAPY(USDC);

        console.log("Compound USDC APY:");
        console.log(usdcAPY);
        console.log("bps =");
        console.log(usdcAPY / 100);

        // Should be reasonable
        assertGt(usdcAPY, 10);
        assertLt(usdcAPY, 3000);
    }

    // ============ Rate Comparison Tests ============

    function test_CompareRates_USDC() public {
        if (block.chainid != 1) return;

        uint256 aaveUSDC = aaveAdapter.getCurrentAPY(USDC);
        uint256 compoundUSDC = compoundAdapter.getCurrentAPY(USDC);

        console.log("=== USDC Borrow Rate Comparison ===");
        console.log("Aave V3:", aaveUSDC / 100, "%");
        console.log("Compound V3:", compoundUSDC / 100, "%");

        // Log which is cheaper
        if (aaveUSDC < compoundUSDC) {
            console.log("Winner: Aave V3 (lower rate)");
        } else if (compoundUSDC < aaveUSDC) {
            console.log("Winner: Compound V3 (lower rate)");
        } else {
            console.log("Tie: Same rates");
        }
    }

    // ============ Mock Borrow Flow Tests ============

    /**
     * @notice Test the full borrow flow with mocked collateral
     * @dev In production, the LiquidityRouter would handle collateral management
     */
    function test_Aave_BorrowFlow_Simulated() public {
        if (block.chainid != 1) return;

        // Get quote
        ILiquiditySource.LiquidityQuote memory quote = aaveAdapter.getQuote(
            WETH,
            1 ether
        );

        console.log("=== Aave Borrow Simulation ===");
        console.log("Amount:", 1, "ETH");
        console.log("Available:", quote.availableAmount / 1e18, "ETH");
        console.log("APY:", quote.rateAPY / 100, "%");
        console.log("Fee:", quote.feeBps, "bps");
        console.log("Time:", quote.estimatedTime, "seconds");

        // Verify the quote is valid
        assertTrue(
            quote.availableAmount >= 1 ether,
            "Should have enough liquidity"
        );

        // Note: Actual borrowing requires collateral to be deposited first
        // This is handled by the LiquidityRouter in production
    }

    function test_Compound_BorrowFlow_Simulated() public {
        if (block.chainid != 1) return;

        uint256 borrowAmount = 10_000 * 1e6; // 10k USDC

        // Get quote
        ILiquiditySource.LiquidityQuote memory quote = compoundAdapter.getQuote(
            USDC,
            borrowAmount
        );

        console.log("=== Compound Borrow Simulation ===");
        console.log("Amount:", borrowAmount / 1e6, "USDC");
        console.log("Available:", quote.availableAmount / 1e6, "USDC");
        console.log("APY:", quote.rateAPY / 100, "%");

        assertTrue(quote.availableAmount >= borrowAmount);
    }

    // ============ Source Type Verification ============

    function test_SourceTypes_Correct() public {
        if (block.chainid != 1) return;

        assertEq(
            uint(aaveAdapter.getSourceType()),
            uint(ILiquiditySource.SourceType.EXTERNAL_AAVE)
        );

        assertEq(
            uint(compoundAdapter.getSourceType()),
            uint(ILiquiditySource.SourceType.EXTERNAL_COMPOUND)
        );

        assertEq(
            uint(morphoAdapter.getSourceType()),
            uint(ILiquiditySource.SourceType.EXTERNAL_MORPHO)
        );
    }

    function test_AllAdapters_NotAsync() public {
        if (block.chainid != 1) return;

        assertFalse(aaveAdapter.isAsync(), "Aave should be instant");
        assertFalse(compoundAdapter.isAsync(), "Compound should be instant");
        assertFalse(morphoAdapter.isAsync(), "Morpho should be instant");
    }
}

/**
 * @title ExternalProtocolsMockTest
 * @notice Unit tests with mocked external protocols (no fork required)
 */
contract ExternalProtocolsMockTest is Test {
    AaveV3Adapter public aaveAdapter;
    CompoundV3Adapter public compoundAdapter;
    MorphoAdapter public morphoAdapter;

    MockAavePool public mockAavePool;
    MockAaveDataProvider public mockDataProvider;
    MockComet public mockComet;
    MockMorpho public mockMorpho;

    address constant WETH = address(0x1111);
    address constant USDC = address(0x2222);
    address constant A_WETH = address(0x3333);

    function setUp() public {
        // Deploy mocks
        mockAavePool = new MockAavePool();
        mockDataProvider = new MockAaveDataProvider();
        mockComet = new MockComet(USDC);
        mockMorpho = new MockMorpho();

        // Deploy adapters with mocks
        aaveAdapter = new AaveV3Adapter(
            address(mockAavePool),
            address(mockDataProvider),
            WETH
        );

        compoundAdapter = new CompoundV3Adapter(WETH);

        morphoAdapter = new MorphoAdapter(address(mockMorpho), WETH);

        // Configure
        aaveAdapter.addSupportedToken(WETH, A_WETH);
        compoundAdapter.addComet(address(mockComet));
    }

    function test_Mock_Aave_Quote() public {
        // Set mock data
        mockDataProvider.setReserveData(WETH, 1000 ether, 500 ether, 5e25); // 5% APY

        ILiquiditySource.LiquidityQuote memory quote = aaveAdapter.getQuote(
            WETH,
            10 ether
        );

        assertEq(
            uint(quote.sourceType),
            uint(ILiquiditySource.SourceType.EXTERNAL_AAVE)
        );
        assertGt(quote.availableAmount, 0);
    }

    function test_Mock_Compound_Quote() public {
        // Comet mock returns values in constructor
        ILiquiditySource.LiquidityQuote memory quote = compoundAdapter.getQuote(
            USDC,
            1000 * 1e6
        );

        assertEq(
            uint(quote.sourceType),
            uint(ILiquiditySource.SourceType.EXTERNAL_COMPOUND)
        );
    }

    function test_Mock_SupportedTokens() public {
        assertTrue(aaveAdapter.supportsToken(WETH));
        assertFalse(aaveAdapter.supportsToken(address(0x123)));

        assertTrue(compoundAdapter.supportsToken(USDC));
    }
}

// ============ Mock Contracts ============

contract MockAavePool {
    function borrow(address, uint256, uint256, uint16, address) external {}
    function repay(
        address,
        uint256,
        uint256,
        address
    ) external returns (uint256) {
        return 0;
    }
    function getUserAccountData(
        address
    )
        external
        pure
        returns (uint256, uint256, uint256, uint256, uint256, uint256)
    {
        return (100 ether, 0, 50 ether, 8000, 7500, 1e18);
    }
}

contract MockAaveDataProvider {
    mapping(address => uint256) public totalATokenSupply;
    mapping(address => uint256) public totalDebt;
    mapping(address => uint256) public borrowRate;

    function setReserveData(
        address asset,
        uint256 supply,
        uint256 debt,
        uint256 rate
    ) external {
        totalATokenSupply[asset] = supply;
        totalDebt[asset] = debt;
        borrowRate[asset] = rate;
    }

    function getReserveData(
        address asset
    )
        external
        view
        returns (
            uint256,
            uint256,
            uint256,
            uint256,
            uint256,
            uint256,
            uint256,
            uint256,
            uint256,
            uint256,
            uint256,
            uint40
        )
    {
        return (
            0,
            0,
            totalATokenSupply[asset],
            0,
            totalDebt[asset],
            0,
            borrowRate[asset],
            0,
            0,
            0,
            0,
            uint40(block.timestamp)
        );
    }

    function getATokenTotalSupply(
        address asset
    ) external view returns (uint256) {
        return totalATokenSupply[asset];
    }

    function getTotalDebt(address asset) external view returns (uint256) {
        return totalDebt[asset];
    }
}

contract MockComet {
    address public baseToken;

    constructor(address _baseToken) {
        baseToken = _baseToken;
    }

    function totalSupply() external pure returns (uint256) {
        return 10_000_000 * 1e6;
    }
    function totalBorrow() external pure returns (uint256) {
        return 5_000_000 * 1e6;
    }
    function getUtilization() external pure returns (uint256) {
        return 5e17;
    } // 50%
    function getBorrowRate(uint256) external pure returns (uint64) {
        return 1e15;
    } // ~3% APY
    function withdrawTo(address, address, uint256) external {}
    function supply(address, uint256) external {}
}

contract MockMorpho {
    function idToMarketParams(
        bytes32
    ) external pure returns (IMorpho.MarketParams memory) {
        return
            IMorpho.MarketParams({
                loanToken: address(0),
                collateralToken: address(0),
                oracle: address(0),
                irm: address(0),
                lltv: 0
            });
    }

    function market(bytes32) external view returns (IMorpho.Market memory) {
        return
            IMorpho.Market({
                totalSupplyAssets: 1000 ether,
                totalSupplyShares: 1000e18,
                totalBorrowAssets: 500 ether,
                totalBorrowShares: 500e18,
                lastUpdate: uint128(block.timestamp),
                fee: 0
            });
    }
}
