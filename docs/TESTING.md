# Testing Strategy

Comprehensive multi-layer testing approach for smart contract security.

## Testing Pyramid

```
         ┌───────────────────┐
         │ Formal Verification│  ← Mathematical proofs
         │     (Certora)      │
         ├───────────────────┤
         │ Symbolic Execution │  ← All paths within bounds
         │     (Halmos)       │
         ├───────────────────┤
         │ Invariant Testing  │  ← Stateful properties
         │    (Foundry)       │
         ├───────────────────┤
         │   Fuzz Testing     │  ← Random inputs (256+ runs)
         │    (Foundry)       │
         ├───────────────────┤
         │   Unit Testing     │  ← Specific behaviors
         │    (Foundry)       │
         └───────────────────┘
```

## Test Files

| File | Type | Tests | Coverage |
|------|------|-------|----------|
| `CrossChainVaultBase.t.sol` | Unit | 38 | Core operations |
| `CrossChainVaultBase.fuzz.t.sol` | Fuzz | 8 | Random inputs |
| `CrossChainVaultBase.invariant.t.sol` | Invariant | 5 | Protocol properties |
| `CrossChainVaultBase.symbolic.t.sol` | Symbolic | 6 | Path verification |
| `certora/specs/*.spec` | Formal | 10 | Mathematical proofs |

## Running Tests

### All Tests
```bash
forge test --summary
```

### By Category
```bash
# Unit tests
forge test --match-contract "Test$" -vv

# Fuzz tests (256 runs default)
forge test --match-contract "Fuzz" -vv

# Invariant tests
forge test --match-contract "Invariant" -vvv

# Extended fuzz (more runs)
forge test --fuzz-runs 1000 -vv
```

### Symbolic Execution (Halmos)
```bash
pip install halmos
halmos --contract CrossChainVaultSymbolicTest
```

### Formal Verification (Certora)
```bash
pip install certora-cli
certoraRun certora/conf/vault.conf
```

### Static Analysis
```bash
# Slither
pip install slither-analyzer
slither .

# Aderyn
cargo install aderyn
aderyn .
```

## Key Invariants Tested

1. **Solvency**: `totalBorrowed <= totalDeposited`
2. **Collateralization**: Healthy positions have `healthFactor >= 100`
3. **Reserves**: Protocol reserves are non-decreasing (except withdrawals)
4. **Access Control**: Only owner can call admin functions

## Fuzz Test Properties

- Deposit/withdraw maintains correct balances
- Borrow respects collateral limits
- Repay reduces debt correctly
- Interest accrues over time
- Health factor decreases with borrowing

## Coverage Target

Goal: **>85% line coverage** on core contracts

```bash
forge coverage --report summary
```
