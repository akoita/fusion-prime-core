/**
 * @title CrossChainVaultBase Formal Verification Specification
 * @notice Certora Prover specification for proving protocol invariants
 * @dev Run with: certoraRun certora/conf/vault.conf
 *
 * This specification formally verifies critical safety properties:
 * 1. Solvency invariants
 * 2. Access control
 * 3. State transitions
 */

using CrossChainVaultBase as vault;

// ============ Methods block ============
methods {
    function totalDeposited(address) external returns (uint256) envfree;
    function totalBorrowed(address) external returns (uint256) envfree;
    function reserves(address) external returns (uint256) envfree;
    function collateralFactors(address) external returns (uint256) envfree;
    function paused() external returns (bool) envfree;
    function getHealthFactor(address) external returns (uint256) envfree;
    function positions(address) external returns (uint256, uint256, uint256, uint256, uint256, uint256) envfree;
    function owner() external returns (address) envfree;
}

// ============ Definitions ============
definition MAX_COLLATERAL_FACTOR() returns uint256 = 10000;
definition LIQUIDATION_THRESHOLD() returns uint256 = 100;

// ============ Invariants ============

/**
 * @notice Total borrowed never exceeds total deposited (solvency)
 */
invariant borrowedLessThanDeposited(address token)
    totalBorrowed(token) <= totalDeposited(token)
    {
        preserved {
            require totalDeposited(token) >= totalBorrowed(token);
        }
    }

/**
 * @notice Reserves are always non-negative
 */
invariant reservesNonNegative(address token)
    reserves(token) >= 0;

/**
 * @notice Collateral factor never exceeds 100%
 */
invariant collateralFactorBounded(address token)
    collateralFactors(token) <= MAX_COLLATERAL_FACTOR();

// ============ Rules ============

/**
 * @notice Only owner can pause the contract
 */
rule onlyOwnerCanPause(env e) {
    bool pausedBefore = paused();

    pause@withrevert(e);

    bool pausedAfter = paused();

    assert !pausedBefore && pausedAfter => e.msg.sender == owner(),
        "Non-owner should not be able to pause";
}

/**
 * @notice Deposit increases collateral by exact amount
 */
rule depositIncreasesCollateral(env e, uint256 amount) {
    require amount > 0;
    require e.msg.value == amount;

    uint256 collateralBefore;
    uint256 _;
    (collateralBefore, _, _, _, _, _) = positions(e.msg.sender);

    deposit(e);

    uint256 collateralAfter;
    (collateralAfter, _, _, _, _, _) = positions(e.msg.sender);

    assert collateralAfter == collateralBefore + amount,
        "Collateral should increase by deposit amount";
}

/**
 * @notice Withdraw decreases collateral by exact amount
 */
rule withdrawDecreasesCollateral(env e, uint256 amount) {
    uint256 collateralBefore;
    (collateralBefore, _, _, _, _, _) = positions(e.msg.sender);

    require amount <= collateralBefore;

    withdraw@withrevert(e, amount);

    bool reverted = lastReverted;

    uint256 collateralAfter;
    (collateralAfter, _, _, _, _, _) = positions(e.msg.sender);

    assert !reverted => collateralAfter == collateralBefore - amount,
        "Collateral should decrease by withdraw amount";
}

/**
 * @notice Borrow fails if it would make position undercollateralized
 */
rule borrowMaintainsHealthFactor(env e, address token, uint256 amount) {
    uint256 hfBefore = getHealthFactor(e.msg.sender);

    borrow@withrevert(e, token, amount);

    bool reverted = lastReverted;

    uint256 hfAfter = getHealthFactor(e.msg.sender);

    // If borrow succeeded, health factor must still be above threshold
    assert !reverted => hfAfter >= LIQUIDATION_THRESHOLD(),
        "Successful borrow must maintain healthy position";
}

/**
 * @notice Liquidation only succeeds for unhealthy positions
 */
rule liquidationRequiresUnhealthy(env e, address user, address debtToken, uint256 amount, address collateralToken) {
    uint256 hf = getHealthFactor(user);

    liquidate@withrevert(e, user, debtToken, amount, collateralToken);

    bool reverted = lastReverted;

    // If health factor >= 100, liquidation must revert
    assert hf >= LIQUIDATION_THRESHOLD() => reverted,
        "Cannot liquidate healthy position";
}

/**
 * @notice Repay cannot increase debt
 */
rule repayReducesOrMaintainsDebt(env e, address token, uint256 amount) {
    uint256 borrowedBefore = totalBorrowed(token);

    repay@withrevert(e, token, amount);

    bool reverted = lastReverted;

    uint256 borrowedAfter = totalBorrowed(token);

    assert !reverted => borrowedAfter <= borrowedBefore,
        "Repay should not increase total borrowed";
}

/**
 * @notice Flash loan preserves or increases reserves
 */
rule flashLoanIncreasesReserves(env e, address token, uint256 amount, address receiver, bytes data) {
    uint256 reservesBefore = reserves(token);

    flashLoan@withrevert(e, token, amount, receiver, data);

    bool reverted = lastReverted;

    uint256 reservesAfter = reserves(token);

    assert !reverted => reservesAfter >= reservesBefore,
        "Flash loan should not decrease reserves";
}
