# Fusion Prime Core Testing Guide

## Overview
Fusion Prime maintains a multi-layered testing strategy to ensure the security and reliability of the protocol across all supported chains.

## Test Directory Structure
All tests are located in `contracts/test/`.

- **Unit Tests**: Test individual functions and components in isolation using mocks.
- **Integration Tests**: Test interactions between multiple contracts (e.g., Escrow + Identity).
- **Cross-Chain Tests**: Test bridge adapters and remote contract calls.
- **Fuzz Tests**: Use dynamic inputs to find edge cases.
- **Invariant Tests**: Verify global system properties across many operations.
- **Symbolic Execution**: Mathematical proof of correctness for critical logic.

## Running Tests

### 1. General Unit & Integration Tests
Run the standard suite using Foundry:
```bash
cd contracts
forge test
```

To run a specific test file:
```bash
forge test --match-path test/Identity.t.sol
```

### 2. Fuzz & Invariant Tests
```bash
# Fuzz tests
forge test --match-contract "Fuzz"

# Invariant tests
forge test --match-contract "Invariant"
```

### 3. Cross-Chain Tests
For detailed instructions on local multi-chain testing, see [CROSS_CHAIN_TESTING.md](./CROSS_CHAIN_TESTING.md).

Quick run:
```bash
./scripts/run-multichain-tests.sh
```

### 4. Symbolic Execution (Halmos)
Requires [Halmos](https://github.com/a16z/halmos) to be installed.
```bash
halmos --contract CrossChainVaultSymbolicTest
```

## Advanced Verification
We use advanced techniques for the `CrossChainVault` core:
- **Invariants**: Proving that total debt never exceeds total collateral value.
- **Properties**: Proving that user balances are updated correctly in all scenarios.

## Continuous Integration
All PRs must pass the full testing suite in GitHub Actions, including:
- Compilation & Size checks
- Standard Unit Tests
- Fuzz (256 runs) & Invariant (64 runs) Tests
- Multi-Chain Integration Tests
- Slither Static Analysis
