# Fusion Prime - Cross-Chain DeFi Lending Protocol

![Tests](https://github.com/akoita/fusion-prime-core/actions/workflows/test.yml/badge.svg)
![Security](https://github.com/akoita/fusion-prime-core/actions/workflows/security.yml/badge.svg)

A sophisticated cross-chain DeFi lending protocol with comprehensive multi-layer security testing.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      LiquidityRouter                             │
│         Aggregates liquidity from multiple sources               │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  Local Vault  │    │ Cross-Chain   │    │   External    │
│   Adapter     │    │   Bridges     │    │  Protocols    │
└───────┬───────┘    └───────┬───────┘    └───────┬───────┘
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│CrossChainVault│    │Axelar / CCIP  │    │Aave/Compound  │
└───────────────┘    └───────────────┘    └───────────────┘
```

## 📁 Project Structure

```
contracts/
├── cross-chain/
│   ├── src/                    # Core contracts
│   │   ├── CrossChainVaultBase.sol
│   │   ├── CrossChainVault.sol
│   │   ├── LiquidityRouter.sol
│   │   ├── BridgeManager.sol
│   │   ├── adapters/           # Protocol adapters
│   │   ├── interfaces/
│   │   └── oracles/
│   ├── test/                   # Comprehensive tests
│   │   ├── *.t.sol             # Unit tests
│   │   ├── *.fuzz.t.sol        # Fuzz tests
│   │   ├── *.invariant.t.sol   # Invariant tests
│   │   └── *.symbolic.t.sol    # Symbolic tests
│   └── certora/                # Formal verification
├── docs/
│   ├── ARCHITECTURE.md
│   └── TESTING.md
└── .github/workflows/          # CI/CD
```

## 🧪 Testing Strategy

| Layer | Tool | Purpose |
|-------|------|---------|
| Unit | Foundry | Specific behavior |
| Fuzz | Foundry | Random inputs |
| Invariant | Foundry | Stateful properties |
| Symbolic | Halmos | Path verification |
| Formal | Certora | Mathematical proofs |
| Static | Slither/Aderyn | Vulnerability detection |

## 🚀 Quick Start

```bash
# Install dependencies
forge install

# Run all tests
cd contracts/cross-chain && forge test --summary

# Run specific test types
forge test --match-contract "Fuzz" -vv      # Fuzz tests
forge test --match-contract "Invariant" -vv # Invariant tests

# Static analysis
slither .

# Coverage
forge coverage --report summary
```

## 📊 Key Features

- **Multi-Source Liquidity**: Aggregates from local vault, cross-chain bridges, and external DeFi protocols
- **Variable & Stable Rates**: Dual interest rate modes with 30-day stable lock
- **Flash Loans**: 0.09% fee atomic borrowing
- **Cross-Chain**: Axelar and Chainlink CCIP integration
- **Compliance Ready**: ERC-735 identity verification support

## 📄 Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [Testing Strategy](docs/TESTING.md)

## 🔐 Security

- Reentrancy guards on all state-changing functions
- 24-hour timelock on unpause
- Multi-layer test coverage
- Formal verification specs

---

*Built with Foundry & Solidity ^0.8.30*
