// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import "forge-std/Test.sol";
import "lending/LiquidityRouter.sol";
import "adapters/LocalVaultAdapter.sol";
import "adapters/MessageBridgeLiquidityAdapter.sol";
import "lending/CrossChainVault.sol";
import "interfaces/ILiquiditySource.sol";

/**
 * @title LiquidityRouterTest
 * @notice Tests for opt-in cross-chain liquidity routing
 */
contract LiquidityRouterTest is Test {
    // Contracts
    LiquidityRouter public router;
    LocalVaultAdapter public localAdapter;
    MessageBridgeLiquidityAdapter public bridgeAdapter;
    CrossChainVault public vault;

    // Test addresses
    address public owner = address(this);
    address public user1 = address(0x1);
    address public user2 = address(0x2);

    // Chain IDs for multi-chain testing
    uint256 public constant CHAIN_A = 31337;
    uint256 public constant CHAIN_B = 31338;
    uint256 public constant CHAIN_C = 31339;

    function setUp() public {
        // Deploy a mock vault (simplified for testing)
        // In real tests, we'd deploy the full CrossChainVault
        vault = CrossChainVault(payable(address(new MockVault())));

        // Deploy LiquidityRouter
        router = new LiquidityRouter(address(vault));

        // Deploy LocalVaultAdapter
        localAdapter = new LocalVaultAdapter(address(vault));

        // Deploy MessageBridgeLiquidityAdapter (mock bridge for now)
        bridgeAdapter = new MessageBridgeLiquidityAdapter(
            address(new MockBridge())
        );

        // Register adapters in router
        router.registerLiquiditySource(
            ILiquiditySource.SourceType.LOCAL_VAULT,
            address(localAdapter)
        );

        // Register bridge adapter for remote chains
        router.registerBridgeAdapter(CHAIN_B, address(bridgeAdapter));
        router.registerBridgeAdapter(CHAIN_C, address(bridgeAdapter));

        // Setup mock remote vaults in bridge adapter
        bridgeAdapter.registerRemoteVault(CHAIN_B, address(0xB));
        bridgeAdapter.registerRemoteVault(CHAIN_C, address(0xC));

        // Set simulated liquidity on remote chains
        bridgeAdapter.setSimulatedLiquidity(CHAIN_B, address(0), 100 ether); // 100 ETH on Chain B
        bridgeAdapter.setSimulatedLiquidity(CHAIN_C, address(0), 50 ether); // 50 ETH on Chain C

        // Fund the local vault with some ETH
        vm.deal(address(vault), 20 ether);

        // Fund test users
        vm.deal(user1, 10 ether);
        vm.deal(user2, 10 ether);
    }

    // ============ User Preference Tests ============

    function test_DefaultPreferencesAreConservative() public {
        LiquidityRouter.UserPreferences memory prefs = router.getPreferences(
            user1
        );

        // Default: all opt-in features disabled
        assertFalse(prefs.enableCrossChain);
        assertFalse(prefs.enableExternalProtocols);
        assertEq(prefs.maxBridgeFeeBps, 50); // 0.5%
        assertEq(prefs.maxWaitTimeSeconds, 900); // 15 min
        assertEq(prefs.maxExternalAPYBps, 500); // 5%
    }

    function test_UserCanUpdatePreferences() public {
        vm.prank(user1);
        router.updatePreferences(
            true, // enableCrossChain
            true, // enableExternalProtocols
            100, // maxBridgeFeeBps (1%)
            1800, // maxWaitTimeSeconds (30 min)
            1000 // maxExternalAPYBps (10%)
        );

        LiquidityRouter.UserPreferences memory prefs = router.getPreferences(
            user1
        );

        assertTrue(prefs.enableCrossChain);
        assertTrue(prefs.enableExternalProtocols);
        assertEq(prefs.maxBridgeFeeBps, 100);
        assertEq(prefs.maxWaitTimeSeconds, 1800);
        assertEq(prefs.maxExternalAPYBps, 1000);
    }

    // ============ Quote Tests ============

    function test_GetQuotes_OnlyLocalByDefault() public {
        // User with default preferences (cross-chain disabled)
        vm.prank(user1);
        ILiquiditySource.LiquidityQuote[] memory quotes = router.getQuotes(
            address(0), // ETH
            10 ether
        );

        // Router returns fixed 6-slot array for all source types
        // Check the first quote (local vault) is valid
        assertEq(
            uint(quotes[0].sourceType),
            uint(ILiquiditySource.SourceType.LOCAL_VAULT)
        );
        assertGt(quotes[0].availableAmount, 0); // Local vault has liquidity
        assertEq(quotes[0].feeBps, 0); // No fees for local
        assertEq(quotes[0].estimatedTime, 0); // Instant
    }

    function test_GetQuotes_IncludesCrossChainWhenEnabled() public {
        // Enable cross-chain for user1
        vm.prank(user1);
        router.updatePreferences(true, false, 100, 1800, 500);

        vm.prank(user1);
        ILiquiditySource.LiquidityQuote[] memory quotes = router.getQuotes(
            address(0), // ETH
            10 ether
        );

        // Router returns fixed 6-slot array for all source types
        // Check local vault (index 0) is valid
        assertEq(
            uint(quotes[0].sourceType),
            uint(ILiquiditySource.SourceType.LOCAL_VAULT)
        );
        assertGt(quotes[0].availableAmount, 0);

        // Check cross-chain bridge (index 1) has liquidity
        assertEq(
            uint(quotes[1].sourceType),
            uint(ILiquiditySource.SourceType.CROSS_CHAIN_BRIDGE)
        );
        assertGt(quotes[1].availableAmount, 0); // Has cross-chain liquidity

        // Cross-chain should have fees and wait time
        assertGt(quotes[1].feeBps, 0);
        assertGt(quotes[1].estimatedTime, 0);
    }

    // ============ Borrow Plan Tests ============

    function test_GenerateBorrowPlan_LocalOnlyFitsRequest() public {
        // Request 10 ETH, local vault has 20 ETH
        ILiquiditySource.SourceType[]
            memory sources = new ILiquiditySource.SourceType[](1);
        sources[0] = ILiquiditySource.SourceType.LOCAL_VAULT;

        LiquidityRouter.BorrowRequest memory request = LiquidityRouter
            .BorrowRequest({
                token: address(0),
                amount: 10 ether,
                enabledSources: sources,
                maxTotalFeeBps: 100
            });

        LiquidityRouter.BorrowPlan memory plan = router.generateBorrowPlan(
            request
        );

        assertTrue(plan.isValid);
        assertEq(plan.steps.length, 1);
        assertEq(plan.steps[0].amount, 10 ether);
        assertEq(plan.totalFee, 0); // No fees for local
        assertEq(plan.maxWaitTime, 0); // Instant
    }

    function test_GenerateBorrowPlan_NeedsMultipleSources() public {
        // Request 30 ETH, local has 20, need cross-chain for rest
        ILiquiditySource.SourceType[]
            memory sources = new ILiquiditySource.SourceType[](2);
        sources[0] = ILiquiditySource.SourceType.LOCAL_VAULT;
        sources[1] = ILiquiditySource.SourceType.CROSS_CHAIN_BRIDGE;

        LiquidityRouter.BorrowRequest memory request = LiquidityRouter
            .BorrowRequest({
                token: address(0),
                amount: 30 ether,
                enabledSources: sources,
                maxTotalFeeBps: 100
            });

        LiquidityRouter.BorrowPlan memory plan = router.generateBorrowPlan(
            request
        );

        assertTrue(plan.isValid);
        assertEq(plan.steps.length, 2);

        // First step: local (20 ETH)
        assertEq(
            uint(plan.steps[0].sourceType),
            uint(ILiquiditySource.SourceType.LOCAL_VAULT)
        );
        assertEq(plan.steps[0].amount, 20 ether);

        // Second step: cross-chain (10 ETH)
        assertEq(
            uint(plan.steps[1].sourceType),
            uint(ILiquiditySource.SourceType.CROSS_CHAIN_BRIDGE)
        );
        assertEq(plan.steps[1].amount, 10 ether);

        // Should have some fee from cross-chain portion
        assertGt(plan.totalFee, 0);
        // Should have wait time from cross-chain
        assertGt(plan.maxWaitTime, 0);
    }

    function test_GenerateBorrowPlan_InsufficientLiquidity() public {
        // Request 200 ETH, total available is 170 ETH (20 local + 100 Chain B + 50 Chain C)
        ILiquiditySource.SourceType[]
            memory sources = new ILiquiditySource.SourceType[](2);
        sources[0] = ILiquiditySource.SourceType.LOCAL_VAULT;
        sources[1] = ILiquiditySource.SourceType.CROSS_CHAIN_BRIDGE;

        LiquidityRouter.BorrowRequest memory request = LiquidityRouter
            .BorrowRequest({
                token: address(0),
                amount: 200 ether,
                enabledSources: sources,
                maxTotalFeeBps: 100
            });

        LiquidityRouter.BorrowPlan memory plan = router.generateBorrowPlan(
            request
        );

        // Plan should be invalid due to insufficient liquidity
        assertFalse(plan.isValid);
    }

    // ============ Bridge Adapter Tests ============

    function test_BridgeAdapter_EstimatesFee() public {
        (uint256 fee, uint256 feeBps) = bridgeAdapter
            .estimateLiquidityBridgeFee(
                CHAIN_B,
                CHAIN_A,
                address(0), // ETH
                100 ether
            );

        // Default is 0.1% (10 bps)
        assertEq(feeBps, 10);
        assertEq(fee, 0.1 ether); // 0.1% of 100 ETH
    }

    function test_BridgeAdapter_EstimatesTime() public {
        uint256 time = bridgeAdapter.estimateBridgeTime(CHAIN_B, CHAIN_A);

        // Default is 10 seconds for local testing
        assertEq(time, 10);
    }

    function test_BridgeAdapter_TracksRemoteLiquidity() public {
        uint256 liquidityB = bridgeAdapter.getRemoteLiquidity(
            CHAIN_B,
            address(0)
        );
        uint256 liquidityC = bridgeAdapter.getRemoteLiquidity(
            CHAIN_C,
            address(0)
        );

        assertEq(liquidityB, 100 ether);
        assertEq(liquidityC, 50 ether);
    }

    function test_BridgeAdapter_InitiatesTransfer() public {
        bytes32 requestId = bridgeAdapter.initiateLiquidityTransfer(
            CHAIN_B,
            address(0),
            10 ether,
            user1
        );

        // Should have a valid request ID
        assertTrue(requestId != bytes32(0));

        // Simulated liquidity should decrease
        uint256 remaining = bridgeAdapter.getRemoteLiquidity(
            CHAIN_B,
            address(0)
        );
        assertEq(remaining, 90 ether);

        // Request should be pending
        ILiquidityBridgeAdapter.LiquidityTransferRequest
            memory req = bridgeAdapter.getLiquidityTransferRequest(requestId);
        assertEq(
            uint(req.status),
            uint(ILiquidityBridgeAdapter.LiquidityTransferStatus.PENDING)
        );
        assertEq(req.user, user1);
        assertEq(req.amount, 10 ether);
    }

    function test_BridgeAdapter_CompletesTransfer() public {
        bytes32 requestId = bridgeAdapter.initiateLiquidityTransfer(
            CHAIN_B,
            address(0),
            10 ether,
            user1
        );

        // Complete the transfer
        bridgeAdapter.onLiquidityTransferComplete(requestId, true);

        ILiquidityBridgeAdapter.LiquidityTransferRequest
            memory req = bridgeAdapter.getLiquidityTransferRequest(requestId);
        assertEq(
            uint(req.status),
            uint(ILiquidityBridgeAdapter.LiquidityTransferStatus.COMPLETED)
        );
    }

    function test_BridgeAdapter_FailedTransferRestoresLiquidity() public {
        bytes32 requestId = bridgeAdapter.initiateLiquidityTransfer(
            CHAIN_B,
            address(0),
            10 ether,
            user1
        );

        // Fail the transfer
        bridgeAdapter.onLiquidityTransferComplete(requestId, false);

        // Liquidity should be restored
        uint256 remaining = bridgeAdapter.getRemoteLiquidity(
            CHAIN_B,
            address(0)
        );
        assertEq(remaining, 100 ether);

        ILiquidityBridgeAdapter.LiquidityTransferRequest
            memory req = bridgeAdapter.getLiquidityTransferRequest(requestId);
        assertEq(
            uint(req.status),
            uint(ILiquidityBridgeAdapter.LiquidityTransferStatus.FAILED)
        );
    }
}

// ============ Mock Contracts ============

contract MockVault {
    // Minimal mock vault for testing
    mapping(address => bool) public supportedTokens;
    mapping(address => uint256) public totalBorrowed;
    uint256 public totalETHBorrowed;

    constructor() {
        supportedTokens[address(0)] = true; // ETH
    }

    function getAvailableETH() external view returns (uint256) {
        return address(this).balance - totalETHBorrowed;
    }

    function borrowETH(uint256 amount) external {
        require(address(this).balance >= amount, "Insufficient ETH");
        totalETHBorrowed += amount;
        payable(msg.sender).transfer(amount);
    }

    function borrow(address token, uint256 amount) external {
        totalBorrowed[token] += amount;
        // Would transfer token in real implementation
    }

    receive() external payable {}
}

contract MockBridge {
    // Minimal mock bridge for testing
    function sendMessage(
        string memory,
        string memory,
        bytes memory,
        address
    ) external payable returns (bytes32) {
        return keccak256(abi.encodePacked(block.timestamp, msg.sender));
    }

    function estimateGas(
        string memory,
        bytes memory
    ) external pure returns (uint256) {
        return 100000;
    }

    function getProtocolName() external pure returns (string memory) {
        return "mock";
    }

    function isChainSupported(string memory) external pure returns (bool) {
        return true;
    }

    function getSupportedChains() external pure returns (string[] memory) {
        string[] memory chains = new string[](2);
        chains[0] = "chain-b";
        chains[1] = "chain-c";
        return chains;
    }
}
