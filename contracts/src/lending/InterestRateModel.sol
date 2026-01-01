// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title InterestRateModel
 * @notice Calculates variable and stable interest rates based on utilization
 * @dev Supports both variable and stable rate modes like Aave
 */
contract InterestRateModel is Ownable {
    // Rate mode enum
    enum RateMode {
        VARIABLE,
        STABLE
    }

    // Rate parameters (in basis points, 10000 = 100%)
    uint256 public constant BASIS_POINTS = 10000;

    // Base rates (annualized)
    uint256 public baseVariableRate = 200; // 2% base variable rate
    uint256 public variableRateSlope1 = 400; // 4% slope below optimal
    uint256 public variableRateSlope2 = 7500; // 75% slope above optimal

    // Optimal utilization target
    uint256 public optimalUtilization = 8000; // 80%

    // Stable rate premium over variable
    uint256 public stableRatePremium = 1000; // 10% premium

    // Maximum stable rate
    uint256 public maxStableRate = 5000; // 50% max

    // Events
    event RateParametersUpdated(
        uint256 baseVariableRate,
        uint256 variableRateSlope1,
        uint256 variableRateSlope2,
        uint256 optimalUtilization
    );
    event StableRateParametersUpdated(uint256 stableRatePremium, uint256 maxStableRate);

    constructor() Ownable(msg.sender) {}

    /**
     * @notice Calculate the variable borrow rate based on utilization
     * @param totalDeposits Total deposits in the pool
     * @param totalBorrowed Total borrowed from the pool
     * @return rate Variable rate in basis points (annualized)
     */
    function getVariableRate(uint256 totalDeposits, uint256 totalBorrowed) public view returns (uint256 rate) {
        if (totalDeposits == 0) return baseVariableRate;

        uint256 utilization = (totalBorrowed * BASIS_POINTS) / totalDeposits;

        if (utilization <= optimalUtilization) {
            // Below optimal: linear increase
            rate = baseVariableRate + (utilization * variableRateSlope1) / optimalUtilization;
        } else {
            // Above optimal: steeper increase
            uint256 excessUtilization = utilization - optimalUtilization;
            uint256 maxExcess = BASIS_POINTS - optimalUtilization;
            rate = baseVariableRate + variableRateSlope1 + (excessUtilization * variableRateSlope2) / maxExcess;
        }
    }

    /**
     * @notice Calculate the stable borrow rate
     * @param totalDeposits Total deposits in the pool
     * @param totalBorrowed Total borrowed from the pool
     * @return rate Stable rate in basis points (annualized)
     */
    function getStableRate(uint256 totalDeposits, uint256 totalBorrowed) public view returns (uint256 rate) {
        uint256 variableRate = getVariableRate(totalDeposits, totalBorrowed);

        // Stable rate = variable rate + premium
        rate = variableRate + (variableRate * stableRatePremium) / BASIS_POINTS;

        // Cap at max stable rate
        if (rate > maxStableRate) {
            rate = maxStableRate;
        }
    }

    /**
     * @notice Calculate the supply rate (what lenders earn)
     * @param totalDeposits Total deposits in the pool
     * @param totalBorrowed Total borrowed from the pool
     * @param reserveFactor Reserve factor in basis points
     * @return rate Supply rate in basis points (annualized)
     */
    function getSupplyRate(uint256 totalDeposits, uint256 totalBorrowed, uint256 reserveFactor)
        public
        view
        returns (uint256 rate)
    {
        if (totalDeposits == 0) return 0;

        uint256 utilization = (totalBorrowed * BASIS_POINTS) / totalDeposits;
        uint256 borrowRate = getVariableRate(totalDeposits, totalBorrowed);

        // Supply rate = borrow rate * utilization * (1 - reserve factor)
        rate = (borrowRate * utilization * (BASIS_POINTS - reserveFactor)) / (BASIS_POINTS * BASIS_POINTS);
    }

    /**
     * @notice Get utilization rate
     * @param totalDeposits Total deposits in the pool
     * @param totalBorrowed Total borrowed from the pool
     * @return utilization Utilization in basis points
     */
    function getUtilization(uint256 totalDeposits, uint256 totalBorrowed) public pure returns (uint256 utilization) {
        if (totalDeposits == 0) return 0;
        utilization = (totalBorrowed * BASIS_POINTS) / totalDeposits;
    }

    /**
     * @notice Check if stable rate needs rebalancing
     * @dev Rebalance if current variable rate is 20% lower than user's stable rate
     * @param userStableRate The user's locked stable rate
     * @param totalDeposits Total deposits in the pool
     * @param totalBorrowed Total borrowed from the pool
     * @return needsRebalance True if rebalancing is recommended
     */
    function shouldRebalanceStableRate(uint256 userStableRate, uint256 totalDeposits, uint256 totalBorrowed)
        public
        view
        returns (bool needsRebalance)
    {
        uint256 currentStableRate = getStableRate(totalDeposits, totalBorrowed);

        // Rebalance if user's rate is 20% higher than current
        if (userStableRate > (currentStableRate * 120) / 100) {
            return true;
        }

        // Rebalance if user's rate is 20% lower than current (user benefits too much)
        if (userStableRate < (currentStableRate * 80) / 100) {
            return true;
        }

        return false;
    }

    // ========== ADMIN FUNCTIONS ==========

    /**
     * @notice Update rate parameters (governance only)
     */
    function setRateParameters(
        uint256 _baseVariableRate,
        uint256 _variableRateSlope1,
        uint256 _variableRateSlope2,
        uint256 _optimalUtilization
    ) external onlyOwner {
        require(_optimalUtilization <= BASIS_POINTS, "Invalid optimal utilization");
        require(_baseVariableRate <= BASIS_POINTS, "Invalid base rate");

        baseVariableRate = _baseVariableRate;
        variableRateSlope1 = _variableRateSlope1;
        variableRateSlope2 = _variableRateSlope2;
        optimalUtilization = _optimalUtilization;

        emit RateParametersUpdated(_baseVariableRate, _variableRateSlope1, _variableRateSlope2, _optimalUtilization);
    }

    /**
     * @notice Update stable rate parameters (governance only)
     */
    function setStableRateParameters(uint256 _stableRatePremium, uint256 _maxStableRate) external onlyOwner {
        require(_maxStableRate <= BASIS_POINTS, "Invalid max stable rate");

        stableRatePremium = _stableRatePremium;
        maxStableRate = _maxStableRate;

        emit StableRateParametersUpdated(_stableRatePremium, _maxStableRate);
    }
}
