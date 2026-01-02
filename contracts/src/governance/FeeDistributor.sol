// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title FeeDistributor
 * @notice Distributes protocol revenue to FP token stakers
 * @dev Implements a MasterChef-style reward distribution
 *
 * Users stake FP tokens to earn a share of protocol revenue.
 * Revenue can be distributed in multiple tokens (ETH, USDC, etc.)
 */
contract FeeDistributor is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    // ========== STATE ==========

    // FP token for staking
    IERC20 public immutable fpToken;

    // Reward token info
    struct RewardToken {
        uint256 accRewardPerShare; // Accumulated rewards per share (scaled by 1e12)
        uint256 lastRewardTime; // Last time rewards were distributed
        uint256 rewardRate; // Rewards per second (for streaming)
        uint256 totalDistributed; // Total rewards distributed
    }

    // User staking info
    struct UserInfo {
        uint256 amount; // Staked FP tokens
        mapping(address => uint256) rewardDebt; // Reward debt per token
    }

    // Supported reward tokens
    address[] public rewardTokens;
    mapping(address => RewardToken) public rewardTokenInfo;
    mapping(address => bool) public isRewardToken;

    // User info
    mapping(address => UserInfo) public userInfo;

    // Total staked
    uint256 public totalStaked;

    // Precision factor
    uint256 private constant PRECISION = 1e12;

    // ========== EVENTS ==========

    event Staked(address indexed user, uint256 amount);
    event Unstaked(address indexed user, uint256 amount);
    event RewardsClaimed(address indexed user, address indexed token, uint256 amount);
    event RevenueDistributed(address indexed token, uint256 amount);
    event RewardTokenAdded(address indexed token);
    event RewardTokenRemoved(address indexed token);

    // ========== ERRORS ==========

    error InsufficientBalance();
    error InvalidAmount();
    error TokenAlreadyAdded();
    error TokenNotSupported();
    error TransferFailed();

    // ========== CONSTRUCTOR ==========

    constructor(address _fpToken) Ownable(msg.sender) {
        require(_fpToken != address(0), "Invalid FP token");
        fpToken = IERC20(_fpToken);
    }

    // ========== STAKING FUNCTIONS ==========

    /**
     * @notice Stake FP tokens to earn rewards
     * @param amount Amount of FP tokens to stake
     */
    function stake(uint256 amount) external nonReentrant {
        if (amount == 0) revert InvalidAmount();

        _updateRewards(msg.sender);

        fpToken.safeTransferFrom(msg.sender, address(this), amount);

        UserInfo storage user = userInfo[msg.sender];
        user.amount += amount;
        totalStaked += amount;

        // Update reward debt for all tokens
        for (uint256 i = 0; i < rewardTokens.length; i++) {
            address token = rewardTokens[i];
            user.rewardDebt[token] = (user.amount * rewardTokenInfo[token].accRewardPerShare) / PRECISION;
        }

        emit Staked(msg.sender, amount);
    }

    /**
     * @notice Unstake FP tokens
     * @param amount Amount of FP tokens to unstake
     */
    function unstake(uint256 amount) external nonReentrant {
        UserInfo storage user = userInfo[msg.sender];
        if (amount == 0) revert InvalidAmount();
        if (user.amount < amount) revert InsufficientBalance();

        _updateRewards(msg.sender);

        // Claim pending rewards first
        _claimAllRewards(msg.sender);

        user.amount -= amount;
        totalStaked -= amount;

        // Update reward debt for all tokens
        for (uint256 i = 0; i < rewardTokens.length; i++) {
            address token = rewardTokens[i];
            user.rewardDebt[token] = (user.amount * rewardTokenInfo[token].accRewardPerShare) / PRECISION;
        }

        fpToken.safeTransfer(msg.sender, amount);

        emit Unstaked(msg.sender, amount);
    }

    /**
     * @notice Claim all pending rewards
     */
    function claimRewards() external nonReentrant {
        _updateRewards(msg.sender);
        _claimAllRewards(msg.sender);
    }

    /**
     * @notice Claim rewards for a specific token
     * @param token Reward token address
     */
    function claimReward(address token) external nonReentrant {
        if (!isRewardToken[token]) revert TokenNotSupported();

        _updateReward(token);
        _claimReward(msg.sender, token);
    }

    // ========== REVENUE DISTRIBUTION ==========

    /**
     * @notice Distribute protocol revenue to stakers
     * @param token Reward token address
     * @param amount Amount to distribute
     */
    function distributeRevenue(address token, uint256 amount) external nonReentrant {
        if (!isRewardToken[token]) revert TokenNotSupported();
        if (amount == 0) revert InvalidAmount();

        // Transfer tokens from sender
        IERC20(token).safeTransferFrom(msg.sender, address(this), amount);

        _distributeReward(token, amount);
    }

    /**
     * @notice Distribute ETH revenue to stakers
     */
    function distributeETHRevenue() external payable nonReentrant {
        if (!isRewardToken[address(0)]) revert TokenNotSupported();
        if (msg.value == 0) revert InvalidAmount();

        _distributeReward(address(0), msg.value);
    }

    function _distributeReward(address token, uint256 amount) internal {
        if (totalStaked == 0) {
            // If no stakers, send to owner (treasury)
            if (token == address(0)) {
                (bool success,) = owner().call{value: amount}("");
                if (!success) revert TransferFailed();
            } else {
                IERC20(token).safeTransfer(owner(), amount);
            }
            return;
        }

        RewardToken storage rewardInfo = rewardTokenInfo[token];
        rewardInfo.accRewardPerShare += (amount * PRECISION) / totalStaked;
        rewardInfo.totalDistributed += amount;
        rewardInfo.lastRewardTime = block.timestamp;

        emit RevenueDistributed(token, amount);
    }

    // ========== INTERNAL FUNCTIONS ==========

    function _updateRewards(address account) internal {
        for (uint256 i = 0; i < rewardTokens.length; i++) {
            _updateReward(rewardTokens[i]);
        }
    }

    function _updateReward(address token) internal {
        // For instant distribution, nothing to update
        // Could add streaming rewards here if needed
    }

    function _claimAllRewards(address account) internal {
        for (uint256 i = 0; i < rewardTokens.length; i++) {
            _claimReward(account, rewardTokens[i]);
        }
    }

    function _claimReward(address account, address token) internal {
        UserInfo storage user = userInfo[account];
        RewardToken storage rewardInfo = rewardTokenInfo[token];

        uint256 accReward = (user.amount * rewardInfo.accRewardPerShare) / PRECISION;
        uint256 pending = accReward - user.rewardDebt[token];

        if (pending > 0) {
            user.rewardDebt[token] = accReward;

            if (token == address(0)) {
                (bool success,) = account.call{value: pending}("");
                if (!success) revert TransferFailed();
            } else {
                IERC20(token).safeTransfer(account, pending);
            }

            emit RewardsClaimed(account, token, pending);
        }
    }

    // ========== VIEW FUNCTIONS ==========

    /**
     * @notice Get pending rewards for a user
     * @param account User address
     * @param token Reward token address
     * @return Pending reward amount
     */
    function pendingReward(address account, address token) external view returns (uint256) {
        UserInfo storage user = userInfo[account];
        RewardToken storage rewardInfo = rewardTokenInfo[token];

        uint256 accReward = (user.amount * rewardInfo.accRewardPerShare) / PRECISION;
        return accReward - user.rewardDebt[token];
    }

    /**
     * @notice Get all pending rewards for a user
     * @param account User address
     * @return tokens Array of reward token addresses
     * @return amounts Array of pending reward amounts
     */
    function pendingRewards(address account)
        external
        view
        returns (address[] memory tokens, uint256[] memory amounts)
    {
        tokens = rewardTokens;
        amounts = new uint256[](rewardTokens.length);

        UserInfo storage user = userInfo[account];

        for (uint256 i = 0; i < rewardTokens.length; i++) {
            address token = rewardTokens[i];
            RewardToken storage rewardInfo = rewardTokenInfo[token];
            uint256 accReward = (user.amount * rewardInfo.accRewardPerShare) / PRECISION;
            amounts[i] = accReward - user.rewardDebt[token];
        }
    }

    /**
     * @notice Get user staked amount
     */
    function stakedAmount(address account) external view returns (uint256) {
        return userInfo[account].amount;
    }

    /**
     * @notice Get all supported reward tokens
     */
    function getRewardTokens() external view returns (address[] memory) {
        return rewardTokens;
    }

    // ========== ADMIN FUNCTIONS ==========

    /**
     * @notice Add a reward token
     * @param token Token address (address(0) for ETH)
     */
    function addRewardToken(address token) external onlyOwner {
        if (isRewardToken[token]) revert TokenAlreadyAdded();

        isRewardToken[token] = true;
        rewardTokens.push(token);
        rewardTokenInfo[token] = RewardToken({
            accRewardPerShare: 0,
            lastRewardTime: block.timestamp,
            rewardRate: 0,
            totalDistributed: 0
        });

        emit RewardTokenAdded(token);
    }

    /**
     * @notice Remove a reward token
     * @param token Token address
     */
    function removeRewardToken(address token) external onlyOwner {
        if (!isRewardToken[token]) revert TokenNotSupported();

        isRewardToken[token] = false;

        // Remove from array
        for (uint256 i = 0; i < rewardTokens.length; i++) {
            if (rewardTokens[i] == token) {
                rewardTokens[i] = rewardTokens[rewardTokens.length - 1];
                rewardTokens.pop();
                break;
            }
        }

        emit RewardTokenRemoved(token);
    }

    /**
     * @notice Receive ETH
     */
    receive() external payable {}
}
