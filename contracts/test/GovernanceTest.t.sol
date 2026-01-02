// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "governance/FusionPrimeToken.sol";
import "governance/TokenVesting.sol";
import "governance/Governance.sol";
import "governance/FeeDistributor.sol";

contract GovernanceTest is Test {
    FusionPrimeToken public token;
    TokenVesting public vestingTeam;
    TokenVesting public vestingInvestors;
    TokenVesting public vestingAdvisors;
    Governance public governance;
    FeeDistributor public feeDistributor;

    address public owner = address(this);
    address public communityPool = address(0x1);
    address public treasury = address(0x2);
    address public voter1 = address(0x3);
    address public voter2 = address(0x4);
    address public voter3 = address(0x5);

    function setUp() public {
        // For testing, we'll use mock addresses for vesting and deploy token directly
        // Then create separate vesting contracts with the token

        // Use deterministic addresses for vesting contracts
        address vestingTeamAddr = address(0x100);
        address vestingInvestorsAddr = address(0x101);
        address vestingAdvisorsAddr = address(0x102);

        // Deploy FP token with placeholder vesting addresses
        token = new FusionPrimeToken(
            communityPool,
            vestingTeamAddr,
            vestingInvestorsAddr,
            treasury,
            vestingAdvisorsAddr
        );

        // Deploy actual vesting contracts for testing
        vestingTeam = new TokenVesting(address(token));
        vestingInvestors = new TokenVesting(address(token));
        vestingAdvisors = new TokenVesting(address(token));

        // Deploy governance
        governance = new Governance(address(token), address(0));

        // Deploy fee distributor
        feeDistributor = new FeeDistributor(address(token));

        // Setup voting power for test accounts
        // Transfer from community pool
        vm.prank(communityPool);
        token.transfer(voter1, 1_000_000 * 1e18); // 1M tokens (enough to propose)

        vm.prank(communityPool);
        token.transfer(voter2, 500_000 * 1e18);

        vm.prank(communityPool);
        token.transfer(voter3, 5_000_000 * 1e18); // 5M tokens (quorum)

        // Delegate voting power
        vm.prank(voter1);
        token.delegate(voter1);

        vm.prank(voter2);
        token.delegate(voter2);

        vm.prank(voter3);
        token.delegate(voter3);

        // Move forward 1 block for voting power to activate
        vm.roll(block.number + 1);
    }

    // ========== TOKEN TESTS ==========

    function testTokenDistribution() public view {
        // Token was distributed to placeholder vesting addresses (0x100, 0x101, 0x102)
        assertEq(token.balanceOf(communityPool), 40_000_000 * 1e18 - 6_500_000 * 1e18); // Minus transfers
        assertEq(token.balanceOf(address(0x100)), 25_000_000 * 1e18); // Team vesting placeholder
        assertEq(token.balanceOf(address(0x101)), 20_000_000 * 1e18); // Investor vesting placeholder
        assertEq(token.balanceOf(treasury), 10_000_000 * 1e18);
        assertEq(token.balanceOf(address(0x102)), 5_000_000 * 1e18); // Advisor vesting placeholder
    }

    function testTotalSupply() public view {
        assertEq(token.totalSupply(), 100_000_000 * 1e18);
    }

    function testVotingPowerDelegation() public view {
        assertEq(token.getVotes(voter1), 1_000_000 * 1e18);
        assertEq(token.getVotes(voter2), 500_000 * 1e18);
        assertEq(token.getVotes(voter3), 5_000_000 * 1e18);
    }

    // ========== PROPOSAL TESTS ==========

    function testCreateProposal() public {
        address[] memory targets = new address[](1);
        targets[0] = address(token);

        uint256[] memory values = new uint256[](1);
        values[0] = 0;

        bytes[] memory calldatas = new bytes[](1);
        calldatas[0] = abi.encodeWithSignature("transfer(address,uint256)", voter1, 100);

        vm.prank(voter1);
        uint256 proposalId = governance.propose(targets, values, calldatas, "Transfer 100 tokens");

        assertEq(proposalId, 1);

        (address proposer, string memory description,,,,,,) = governance.getProposal(proposalId);
        assertEq(proposer, voter1);
        assertEq(description, "Transfer 100 tokens");
    }

    function testCannotProposeWithoutEnoughVotingPower() public {
        address lowVoter = address(0x999);
        vm.prank(communityPool);
        token.transfer(lowVoter, 10_000 * 1e18); // Only 10K tokens (need 100K)

        vm.prank(lowVoter);
        token.delegate(lowVoter);
        vm.roll(block.number + 1);

        address[] memory targets = new address[](1);
        targets[0] = address(token);

        uint256[] memory values = new uint256[](1);
        values[0] = 0;

        bytes[] memory calldatas = new bytes[](1);
        calldatas[0] = "";

        vm.prank(lowVoter);
        vm.expectRevert(Governance.InsufficientVotingPower.selector);
        governance.propose(targets, values, calldatas, "Test");
    }

    // ========== VOTING TESTS ==========

    function testVoteOnProposal() public {
        // Create proposal
        uint256 proposalId = _createProposal();

        // Fast forward past voting delay (both time and blocks)
        vm.warp(block.timestamp + 1 days + 1);
        vm.roll(block.number + 1); // Roll block so snapshot is in the past

        // Vote
        vm.prank(voter1);
        governance.castVote(proposalId, 1); // For

        vm.prank(voter2);
        governance.castVote(proposalId, 0); // Against

        (,,,, uint256 forVotes, uint256 againstVotes,,) = governance.getProposal(proposalId);
        assertEq(forVotes, 1_000_000 * 1e18);
        assertEq(againstVotes, 500_000 * 1e18);
    }

    function testCannotVoteBeforeVotingStarts() public {
        uint256 proposalId = _createProposal();

        vm.prank(voter1);
        vm.expectRevert(Governance.ProposalNotActive.selector);
        governance.castVote(proposalId, 1);
    }

    function testCannotVoteTwice() public {
        uint256 proposalId = _createProposal();
        vm.warp(block.timestamp + 1 days + 1);
        vm.roll(block.number + 1);

        vm.prank(voter1);
        governance.castVote(proposalId, 1);

        vm.prank(voter1);
        vm.expectRevert(Governance.AlreadyVoted.selector);
        governance.castVote(proposalId, 1);
    }

    // ========== EXECUTION TESTS ==========

    function testQueueAndExecuteProposal() public {
        uint256 proposalId = _createProposal();

        // Vote (advance both time and blocks)
        vm.warp(block.timestamp + 1 days + 1);
        vm.roll(block.number + 1);

        vm.prank(voter3);
        governance.castVote(proposalId, 1); // 5M votes (enough for quorum)

        // End voting
        vm.warp(block.timestamp + 3 days + 1);

        // Check succeeded
        assertEq(uint256(governance.state(proposalId)), uint256(Governance.ProposalState.Succeeded));

        // Queue
        governance.queue(proposalId);
        assertEq(uint256(governance.state(proposalId)), uint256(Governance.ProposalState.Queued));

        // Wait for timelock
        vm.warp(block.timestamp + 2 days + 1);

        // Execute
        governance.execute(proposalId);
        assertEq(uint256(governance.state(proposalId)), uint256(Governance.ProposalState.Executed));
    }

    function testProposalDefeatedWithoutQuorum() public {
        uint256 proposalId = _createProposal();

        // Vote with voter1 only (1M, not enough for 4M quorum)
        vm.warp(block.timestamp + 1 days + 1);
        vm.roll(block.number + 1);

        vm.prank(voter1);
        governance.castVote(proposalId, 1);

        // End voting
        vm.warp(block.timestamp + 3 days + 1);

        // Check defeated (not enough votes for quorum)
        assertEq(uint256(governance.state(proposalId)), uint256(Governance.ProposalState.Defeated));
    }

    // ========== FEE DISTRIBUTOR TESTS ==========

    function testStakeAndEarnRewards() public {
        // Add ETH as reward token
        feeDistributor.addRewardToken(address(0));

        // Stake tokens
        vm.startPrank(voter1);
        token.approve(address(feeDistributor), 100_000 * 1e18);
        feeDistributor.stake(100_000 * 1e18);
        vm.stopPrank();

        // Distribute rewards
        feeDistributor.distributeETHRevenue{value: 1 ether}();

        // Check pending rewards
        uint256 pending = feeDistributor.pendingReward(voter1, address(0));
        assertEq(pending, 1 ether);

        // Claim rewards
        uint256 balanceBefore = voter1.balance;
        vm.prank(voter1);
        feeDistributor.claimRewards();
        uint256 balanceAfter = voter1.balance;

        assertEq(balanceAfter - balanceBefore, 1 ether);
    }

    function testMultipleStakersShareRewards() public {
        feeDistributor.addRewardToken(address(0));

        // Stake from voter1 (100K)
        vm.startPrank(voter1);
        token.approve(address(feeDistributor), 100_000 * 1e18);
        feeDistributor.stake(100_000 * 1e18);
        vm.stopPrank();

        // Stake from voter2 (100K)
        vm.startPrank(voter2);
        token.approve(address(feeDistributor), 100_000 * 1e18);
        feeDistributor.stake(100_000 * 1e18);
        vm.stopPrank();

        // Distribute 1 ETH
        feeDistributor.distributeETHRevenue{value: 1 ether}();

        // Each should get 0.5 ETH
        uint256 pending1 = feeDistributor.pendingReward(voter1, address(0));
        uint256 pending2 = feeDistributor.pendingReward(voter2, address(0));

        assertEq(pending1, 0.5 ether);
        assertEq(pending2, 0.5 ether);
    }

    function testUnstake() public {
        feeDistributor.addRewardToken(address(0));

        vm.startPrank(voter1);
        token.approve(address(feeDistributor), 100_000 * 1e18);
        feeDistributor.stake(100_000 * 1e18);

        uint256 balanceBefore = token.balanceOf(voter1);
        feeDistributor.unstake(50_000 * 1e18);
        uint256 balanceAfter = token.balanceOf(voter1);

        assertEq(balanceAfter - balanceBefore, 50_000 * 1e18);
        assertEq(feeDistributor.stakedAmount(voter1), 50_000 * 1e18);
        vm.stopPrank();
    }

    // ========== HELPER FUNCTIONS ==========

    function _createProposal() internal returns (uint256) {
        address[] memory targets = new address[](1);
        targets[0] = address(governance); // Just a dummy target

        uint256[] memory values = new uint256[](1);
        values[0] = 0;

        bytes[] memory calldatas = new bytes[](1);
        calldatas[0] = abi.encodeWithSignature("setTimelock(address)", address(0x999));

        vm.prank(voter1);
        return governance.propose(targets, values, calldatas, "Test Proposal");
    }

    // Receive ETH
    receive() external payable {}
}
