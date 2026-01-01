# Fusion Prime - DeFi Protocol Suite

![Unit Tests](https://github.com/akoita/fusion-prime-core/actions/workflows/test.yml/badge.svg)
![Security](https://github.com/akoita/fusion-prime-core/actions/workflows/security.yml/badge.svg)

A comprehensive DeFi protocol suite featuring cross-chain lending, identity verification, and escrow services.

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              FUSION PRIME                                │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐  │
│  │  CROSS-CHAIN    │  │    IDENTITY     │  │        ESCROW           │  │
│  │    LENDING      │  │   VERIFICATION  │  │       SERVICES          │  │
│  ├─────────────────┤  ├─────────────────┤  ├─────────────────────────┤  │
│  │ CrossChainVault │  │ Identity        │  │ Escrow                  │  │
│  │ LiquidityRouter │  │ IdentityFactory │  │ EscrowFactory           │  │
│  │ BridgeManager   │  │ ClaimRegistry   │  │                         │  │
│  │ InterestRate    │  │ IdentityVerifier│  │                         │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────┘  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                         ADAPTERS                                  │   │
│  │  Axelar │ CCIP │ Aave V3 │ Compound V3 │ Morpho │ Local Vault    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
contracts/
├── CrossChainVaultBase.sol   # Core lending vault
├── CrossChainVault.sol       # Compliance layer
├── LiquidityRouter.sol       # Multi-source aggregation
├── BridgeManager.sol         # Cross-chain messaging
├── InterestRateModel.sol     # Rate calculations
├── Identity.sol              # ERC-734/735 identity
├── IdentityFactory.sol       # Identity deployment
├── Escrow.sol                # Escrow contracts
├── EscrowFactory.sol         # Escrow deployment
├── adapters/                 # Protocol adapters
├── interfaces/               # Contract interfaces
├── oracles/                  # Price oracles
├── test/                     # Comprehensive tests
├── certora/                  # Formal verification
└── scripts/                  # Utility scripts
```

## 🧪 Testing Strategy

### Multi-Layer Security Testing

| Layer | Tool | Purpose | CI Job |
|-------|------|---------|--------|
| Unit | Foundry | Specific behavior | `unit-tests` |
| Fuzz | Foundry | Random inputs (256 runs) | `fuzz-tests` |
| Invariant | Foundry | Stateful properties | `invariant-tests` |
| Cross-Chain | Foundry | Bridge integration | `cross-chain-tests` |
| Symbolic | Halmos | Path verification | `security` |
| Static | Slither/Aderyn | Vulnerability detection | `security` |
| Formal | Certora | Mathematical proofs | Local |

### Running Tests

```bash
# All tests
forge test --summary

# Specific categories
forge test --match-contract "Fuzz" -vv        # Fuzz tests
forge test --match-contract "Invariant" -vv   # Invariant tests
forge test --match-contract "CrossChain" -vv  # Cross-chain tests
forge test --match-contract "Escrow" -vv      # Escrow tests
forge test --match-contract "Identity" -vv    # Identity tests

# Deep fuzzing (1000 runs)
FOUNDRY_PROFILE=deep forge test --match-contract "Fuzz"

# Coverage
forge coverage --report summary
```

## 🔐 Security Features

- **Reentrancy Guards**: All state-changing functions
- **Access Control**: Owner-only admin functions
- **Timelocks**: 24-hour unpause delay
- **Multi-Layer Testing**: Unit → Fuzz → Invariant → Symbolic → Formal

## 📊 Key Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| Liquidation Threshold | 80% | Health factor trigger |
| Liquidation Bonus | 5% | Liquidator incentive |
| Close Factor | 50% | Max liquidatable per tx |
| Reserve Factor | 10% | Protocol fee |
| Flash Loan Fee | 0.09% | Atomic borrow cost |

## 📄 Documentation

- [Architecture Overview](../docs/ARCHITECTURE.md)
- [Testing Strategy](../docs/TESTING.md)

---

*Built with Solidity ^0.8.30 & Foundry*
