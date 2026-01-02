// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IVotes} from "@openzeppelin/contracts/governance/utils/IVotes.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title Governance
 * @notice On-chain governance for Fusion Prime protocol
 * @dev Allows FP token holders to propose and vote on protocol changes
 *
 * Governance Parameters:
 * - Voting Period: 3 days
 * - Voting Delay: 1 day
 * - Quorum: 4% of total supply (4M FP)
 * - Proposal Threshold: 0.1% of total supply (100K FP)
 * - Timelock Delay: 2 days
 */
contract Governance is ReentrancyGuard {
    // ========== STATE ==========

    // Governance token
    IVotes public immutable token;

    // Timelock for execution
    address public timelock;

    // Proposal counter
    uint256 public proposalCount;

    // Proposal struct
    struct Proposal {
        uint256 id;
        address proposer;
        string description;
        address[] targets;
        uint256[] values;
        bytes[] calldatas;
        uint256 startTime;           // Voting starts (timestamp)
        uint256 endTime;             // Voting ends (timestamp)
        uint256 snapshotBlock;       // Block number for vote snapshot
        uint256 forVotes;
        uint256 againstVotes;
        uint256 abstainVotes;
        bool executed;
        bool canceled;
        mapping(address => Receipt) receipts;
    }

    // Vote receipt
    struct Receipt {
        bool hasVoted;
        uint8 support; // 0 = Against, 1 = For, 2 = Abstain
        uint256 votes;
    }

    // Proposal state enum
    enum ProposalState {
        Pending,
        Active,
        Canceled,
        Defeated,
        Succeeded,
        Queued,
        Expired,
        Executed
    }

    // Proposals mapping
    mapping(uint256 => Proposal) public proposals;

    // Queued proposals (for timelock)
    mapping(uint256 => bool) public queuedProposals;
    mapping(uint256 => uint256) public proposalEta; // execution time

    // ========== CONSTANTS ==========

    uint256 public constant VOTING_DELAY = 1 days; // Time before voting starts
    uint256 public constant VOTING_PERIOD = 3 days; // Voting duration
    uint256 public constant QUORUM = 4_000_000 * 1e18; // 4% of 100M
    uint256 public constant PROPOSAL_THRESHOLD = 100_000 * 1e18; // 0.1% to propose
    uint256 public constant TIMELOCK_DELAY = 2 days; // Execution delay

    // ========== EVENTS ==========

    event ProposalCreated(
        uint256 indexed proposalId,
        address indexed proposer,
        address[] targets,
        uint256[] values,
        bytes[] calldatas,
        string description,
        uint256 startTime,
        uint256 endTime,
        uint256 snapshotBlock
    );
    event VoteCast(
        address indexed voter, uint256 indexed proposalId, uint8 support, uint256 votes, string reason
    );
    event ProposalQueued(uint256 indexed proposalId, uint256 eta);
    event ProposalExecuted(uint256 indexed proposalId);
    event ProposalCanceled(uint256 indexed proposalId);
    event TimelockSet(address indexed oldTimelock, address indexed newTimelock);

    // ========== ERRORS ==========

    error InvalidProposal();
    error ProposalNotActive();
    error ProposalNotSucceeded();
    error ProposalNotQueued();
    error ProposalAlreadyQueued();
    error ProposalAlreadyExecuted();
    error TimelockNotReached();
    error InsufficientVotingPower();
    error AlreadyVoted();
    error InvalidVoteType();
    error ArrayLengthMismatch();
    error EmptyProposal();
    error OnlyProposer();

    // ========== CONSTRUCTOR ==========

    constructor(address _token, address _timelock) {
        require(_token != address(0), "Invalid token");
        token = IVotes(_token);
        timelock = _timelock;
    }

    // ========== PROPOSAL FUNCTIONS ==========

    /**
     * @notice Create a new proposal
     * @param targets Contract addresses to call
     * @param values ETH values to send
     * @param calldatas Function call data
     * @param description Proposal description
     * @return proposalId The new proposal ID
     */
    function propose(
        address[] memory targets,
        uint256[] memory values,
        bytes[] memory calldatas,
        string memory description
    ) external returns (uint256) {
        if (targets.length != values.length || targets.length != calldatas.length) {
            revert ArrayLengthMismatch();
        }
        if (targets.length == 0) revert EmptyProposal();

        // Check proposer has enough voting power
        uint256 votingPower = token.getVotes(msg.sender);
        if (votingPower < PROPOSAL_THRESHOLD) revert InsufficientVotingPower();

        proposalCount++;
        uint256 proposalId = proposalCount;

        Proposal storage proposal = proposals[proposalId];
        proposal.id = proposalId;
        proposal.proposer = msg.sender;
        proposal.description = description;
        proposal.targets = targets;
        proposal.values = values;
        proposal.calldatas = calldatas;
        proposal.startTime = block.timestamp + VOTING_DELAY;
        proposal.endTime = block.timestamp + VOTING_DELAY + VOTING_PERIOD;
        proposal.snapshotBlock = block.number; // Snapshot current block for voting power

        emit ProposalCreated(
            proposalId, msg.sender, targets, values, calldatas, description, proposal.startTime, proposal.endTime, proposal.snapshotBlock
        );

        return proposalId;
    }

    /**
     * @notice Cancel a proposal (only proposer, before execution)
     * @param proposalId The proposal to cancel
     */
    function cancel(uint256 proposalId) external {
        Proposal storage proposal = proposals[proposalId];
        if (proposal.id == 0) revert InvalidProposal();
        if (msg.sender != proposal.proposer) revert OnlyProposer();
        if (proposal.executed) revert ProposalAlreadyExecuted();

        proposal.canceled = true;
        emit ProposalCanceled(proposalId);
    }

    // ========== VOTING FUNCTIONS ==========

    /**
     * @notice Cast a vote on a proposal
     * @param proposalId The proposal to vote on
     * @param support Vote type: 0 = Against, 1 = For, 2 = Abstain
     */
    function castVote(uint256 proposalId, uint8 support) external {
        _castVote(proposalId, msg.sender, support, "");
    }

    /**
     * @notice Cast a vote with reason
     * @param proposalId The proposal to vote on
     * @param support Vote type: 0 = Against, 1 = For, 2 = Abstain
     * @param reason Vote reason
     */
    function castVoteWithReason(uint256 proposalId, uint8 support, string calldata reason) external {
        _castVote(proposalId, msg.sender, support, reason);
    }

    function _castVote(uint256 proposalId, address voter, uint8 support, string memory reason) internal {
        Proposal storage proposal = proposals[proposalId];

        if (state(proposalId) != ProposalState.Active) revert ProposalNotActive();
        if (support > 2) revert InvalidVoteType();

        Receipt storage receipt = proposal.receipts[voter];
        if (receipt.hasVoted) revert AlreadyVoted();

        // Get voting power at proposal snapshot block
        uint256 votes = token.getPastVotes(voter, proposal.snapshotBlock);

        receipt.hasVoted = true;
        receipt.support = support;
        receipt.votes = votes;

        if (support == 0) {
            proposal.againstVotes += votes;
        } else if (support == 1) {
            proposal.forVotes += votes;
        } else {
            proposal.abstainVotes += votes;
        }

        emit VoteCast(voter, proposalId, support, votes, reason);
    }

    // ========== EXECUTION FUNCTIONS ==========

    /**
     * @notice Queue a successful proposal for execution
     * @param proposalId The proposal to queue
     */
    function queue(uint256 proposalId) external {
        if (state(proposalId) != ProposalState.Succeeded) revert ProposalNotSucceeded();
        if (queuedProposals[proposalId]) revert ProposalAlreadyQueued();

        uint256 eta = block.timestamp + TIMELOCK_DELAY;
        queuedProposals[proposalId] = true;
        proposalEta[proposalId] = eta;

        emit ProposalQueued(proposalId, eta);
    }

    /**
     * @notice Execute a queued proposal
     * @param proposalId The proposal to execute
     */
    function execute(uint256 proposalId) external nonReentrant {
        if (state(proposalId) != ProposalState.Queued) revert ProposalNotQueued();
        if (block.timestamp < proposalEta[proposalId]) revert TimelockNotReached();

        Proposal storage proposal = proposals[proposalId];
        proposal.executed = true;

        // Execute all calls
        for (uint256 i = 0; i < proposal.targets.length; i++) {
            (bool success,) = proposal.targets[i].call{value: proposal.values[i]}(proposal.calldatas[i]);
            require(success, "Execution failed");
        }

        emit ProposalExecuted(proposalId);
    }

    // ========== VIEW FUNCTIONS ==========

    /**
     * @notice Get the state of a proposal
     * @param proposalId The proposal ID
     * @return ProposalState enum value
     */
    function state(uint256 proposalId) public view returns (ProposalState) {
        Proposal storage proposal = proposals[proposalId];

        if (proposal.id == 0) revert InvalidProposal();
        if (proposal.canceled) return ProposalState.Canceled;
        if (proposal.executed) return ProposalState.Executed;

        if (block.timestamp < proposal.startTime) {
            return ProposalState.Pending;
        }

        if (block.timestamp <= proposal.endTime) {
            return ProposalState.Active;
        }

        // Voting ended - check results
        if (proposal.forVotes <= proposal.againstVotes || proposal.forVotes < QUORUM) {
            return ProposalState.Defeated;
        }

        if (queuedProposals[proposalId]) {
            if (block.timestamp >= proposalEta[proposalId] + 14 days) {
                return ProposalState.Expired;
            }
            return ProposalState.Queued;
        }

        return ProposalState.Succeeded;
    }

    /**
     * @notice Get proposal details
     */
    function getProposal(uint256 proposalId)
        external
        view
        returns (
            address proposer,
            string memory description,
            uint256 startTime,
            uint256 endTime,
            uint256 forVotes,
            uint256 againstVotes,
            uint256 abstainVotes,
            ProposalState currentState
        )
    {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.description,
            proposal.startTime,
            proposal.endTime,
            proposal.forVotes,
            proposal.againstVotes,
            proposal.abstainVotes,
            state(proposalId)
        );
    }

    /**
     * @notice Get proposal actions
     */
    function getActions(uint256 proposalId)
        external
        view
        returns (address[] memory targets, uint256[] memory values, bytes[] memory calldatas)
    {
        Proposal storage proposal = proposals[proposalId];
        return (proposal.targets, proposal.values, proposal.calldatas);
    }

    /**
     * @notice Get vote receipt for a voter
     */
    function getReceipt(uint256 proposalId, address voter)
        external
        view
        returns (bool hasVoted, uint8 support, uint256 votes)
    {
        Receipt storage receipt = proposals[proposalId].receipts[voter];
        return (receipt.hasVoted, receipt.support, receipt.votes);
    }

    /**
     * @notice Check if quorum has been reached
     */
    function quorumReached(uint256 proposalId) external view returns (bool) {
        return proposals[proposalId].forVotes >= QUORUM;
    }

    // ========== ADMIN FUNCTIONS ==========

    /**
     * @notice Set timelock address (can only be called by timelock itself)
     */
    function setTimelock(address newTimelock) external {
        require(msg.sender == timelock || timelock == address(0), "Only timelock");
        emit TimelockSet(timelock, newTimelock);
        timelock = newTimelock;
    }

    /**
     * @notice Receive ETH for proposal execution
     */
    receive() external payable {}
}
