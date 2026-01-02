// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title TokenVesting
 * @notice Manages token vesting schedules for team, investors, and advisors
 * @dev Supports cliff periods and linear vesting
 *
 * Vesting Schedules:
 * - Team: 4-year vesting, 1-year cliff
 * - Investors: 3-year vesting, no cliff
 * - Advisors: 2-year vesting, no cliff
 */
contract TokenVesting is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    // Vesting schedule struct
    struct VestingSchedule {
        uint256 totalAmount; // Total tokens to vest
        uint256 startTime; // Vesting start timestamp
        uint256 cliffDuration; // Cliff period in seconds
        uint256 vestingDuration; // Total vesting duration in seconds
        uint256 claimed; // Amount already claimed
        bool revocable; // Can schedule be revoked
        bool revoked; // Has schedule been revoked
    }

    // Token being vested
    IERC20 public immutable token;

    // Vesting schedules per beneficiary
    mapping(address => VestingSchedule) public schedules;

    // List of beneficiaries
    address[] public beneficiaries;

    // Events
    event VestingScheduleCreated(
        address indexed beneficiary,
        uint256 totalAmount,
        uint256 startTime,
        uint256 cliffDuration,
        uint256 vestingDuration
    );
    event TokensClaimed(address indexed beneficiary, uint256 amount);
    event VestingRevoked(address indexed beneficiary, uint256 unvestedAmount);

    // Errors
    error ScheduleAlreadyExists();
    error ScheduleNotFound();
    error NothingToClaim();
    error NotRevocable();
    error AlreadyRevoked();
    error InvalidDuration();
    error InvalidAmount();

    constructor(address _token) Ownable(msg.sender) {
        require(_token != address(0), "Invalid token");
        token = IERC20(_token);
    }

    /**
     * @notice Create a vesting schedule for a beneficiary
     * @param beneficiary Address of the beneficiary
     * @param totalAmount Total tokens to vest
     * @param startTime Vesting start timestamp (can be in the past)
     * @param cliffDuration Cliff period in seconds (0 for no cliff)
     * @param vestingDuration Total vesting duration in seconds
     * @param revocable Whether the schedule can be revoked
     */
    function createVestingSchedule(
        address beneficiary,
        uint256 totalAmount,
        uint256 startTime,
        uint256 cliffDuration,
        uint256 vestingDuration,
        bool revocable
    ) external onlyOwner {
        if (schedules[beneficiary].totalAmount > 0) revert ScheduleAlreadyExists();
        if (totalAmount == 0) revert InvalidAmount();
        if (vestingDuration == 0) revert InvalidDuration();
        if (cliffDuration > vestingDuration) revert InvalidDuration();

        schedules[beneficiary] = VestingSchedule({
            totalAmount: totalAmount,
            startTime: startTime,
            cliffDuration: cliffDuration,
            vestingDuration: vestingDuration,
            claimed: 0,
            revocable: revocable,
            revoked: false
        });

        beneficiaries.push(beneficiary);

        emit VestingScheduleCreated(beneficiary, totalAmount, startTime, cliffDuration, vestingDuration);
    }

    /**
     * @notice Claim vested tokens
     */
    function claim() external nonReentrant {
        VestingSchedule storage schedule = schedules[msg.sender];
        if (schedule.totalAmount == 0) revert ScheduleNotFound();

        uint256 vested = vestedAmount(msg.sender);
        uint256 claimable = vested - schedule.claimed;

        if (claimable == 0) revert NothingToClaim();

        schedule.claimed += claimable;
        token.safeTransfer(msg.sender, claimable);

        emit TokensClaimed(msg.sender, claimable);
    }

    /**
     * @notice Revoke a vesting schedule (returns unvested tokens to owner)
     * @param beneficiary Address of the beneficiary
     */
    function revoke(address beneficiary) external onlyOwner {
        VestingSchedule storage schedule = schedules[beneficiary];
        if (schedule.totalAmount == 0) revert ScheduleNotFound();
        if (!schedule.revocable) revert NotRevocable();
        if (schedule.revoked) revert AlreadyRevoked();

        uint256 vested = vestedAmount(beneficiary);
        uint256 unvested = schedule.totalAmount - vested;

        schedule.revoked = true;
        schedule.totalAmount = vested; // Cap at vested amount

        if (unvested > 0) {
            token.safeTransfer(owner(), unvested);
        }

        emit VestingRevoked(beneficiary, unvested);
    }

    // ========== VIEW FUNCTIONS ==========

    /**
     * @notice Calculate vested amount for a beneficiary
     * @param beneficiary Address of the beneficiary
     * @return Total vested amount (may exceed claimed)
     */
    function vestedAmount(address beneficiary) public view returns (uint256) {
        VestingSchedule storage schedule = schedules[beneficiary];

        if (schedule.totalAmount == 0) return 0;
        if (schedule.revoked) return schedule.totalAmount; // Return capped amount

        uint256 currentTime = block.timestamp;

        // Before cliff
        if (currentTime < schedule.startTime + schedule.cliffDuration) {
            return 0;
        }

        // After vesting complete
        if (currentTime >= schedule.startTime + schedule.vestingDuration) {
            return schedule.totalAmount;
        }

        // During vesting (linear)
        uint256 elapsed = currentTime - schedule.startTime;
        return (schedule.totalAmount * elapsed) / schedule.vestingDuration;
    }

    /**
     * @notice Get claimable amount for a beneficiary
     * @param beneficiary Address of the beneficiary
     * @return Claimable amount
     */
    function claimableAmount(address beneficiary) external view returns (uint256) {
        VestingSchedule storage schedule = schedules[beneficiary];
        return vestedAmount(beneficiary) - schedule.claimed;
    }

    /**
     * @notice Get vesting schedule details
     * @param beneficiary Address of the beneficiary
     */
    function getSchedule(address beneficiary)
        external
        view
        returns (
            uint256 totalAmount,
            uint256 startTime,
            uint256 cliffDuration,
            uint256 vestingDuration,
            uint256 claimed,
            uint256 vested,
            uint256 claimable,
            bool revocable,
            bool revoked
        )
    {
        VestingSchedule storage schedule = schedules[beneficiary];
        uint256 vestedAmt = vestedAmount(beneficiary);

        return (
            schedule.totalAmount,
            schedule.startTime,
            schedule.cliffDuration,
            schedule.vestingDuration,
            schedule.claimed,
            vestedAmt,
            vestedAmt - schedule.claimed,
            schedule.revocable,
            schedule.revoked
        );
    }

    /**
     * @notice Get all beneficiaries
     */
    function getBeneficiaries() external view returns (address[] memory) {
        return beneficiaries;
    }

    /**
     * @notice Get beneficiary count
     */
    function beneficiaryCount() external view returns (uint256) {
        return beneficiaries.length;
    }
}
