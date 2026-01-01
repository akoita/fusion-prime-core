# Fusion Prime - DeFi Protocol Suite

![Unit Tests](https://github.com/akoita/fusion-prime-core/actions/workflows/test.yml/badge.svg)
![Security](https://github.com/akoita/fusion-prime-core/actions/workflows/security.yml/badge.svg)

A comprehensive DeFi protocol suite featuring cross-chain lending, identity verification, and escrow services.

## 📁 Project Structure

```
contracts/
├── src/
│   ├── lending/              # Cross-chain lending protocol
│   │   ├── CrossChainVaultBase.sol
│   │   ├── CrossChainVault.sol
│   │   ├── LiquidityRouter.sol
│   │   ├── BridgeManager.sol
│   │   ├── InterestRateModel.sol
│   │   └── VaultFactory.sol
│   │
│   ├── escrow/               # Escrow services
│   │   ├── Escrow.sol
│   │   └── EscrowFactory.sol
│   │
│   ├── identity/             # Identity verification (ERC-734/735)
│   │   ├── Identity.sol
│   │   ├── IdentityFactory.sol
│   │   ├── IdentityVerifier.sol
│   │   └── ClaimIssuerRegistry.sol
│   │
│   ├── adapters/             # Protocol adapters
│   ├── interfaces/           # Contract interfaces
│   ├── oracles/              # Price oracles
│   └── utils/                # Utilities
│
├── test/                     # Comprehensive test suite
│   ├── *.t.sol               # Unit tests
│   ├── *.fuzz.t.sol          # Fuzz tests
│   ├── *.invariant.t.sol     # Invariant tests
│   └── *.symbolic.t.sol      # Symbolic tests
│
├── certora/                  # Formal verification specs
└── scripts/                  # Utility scripts
```

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              FUSION PRIME                                │
├──────────────┬───────────────────────┬───────────────────────────────────┤
│   LENDING    │       IDENTITY        │              ESCROW               │
├──────────────┼───────────────────────┼───────────────────────────────────┤
│ Vault Base   │ ERC-734/735 Identity  │ Multi-party Escrow               │
│ Cross-Chain  │ Claim Verification    │ Factory Pattern                  │
│ Liquidity    │ Trusted Issuers       │                                  │
│ Bridge Mgmt  │                       │                                  │
└──────────────┴───────────────────────┴───────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────────────────┐
│                         SHARED INFRASTRUCTURE                            │
│   Adapters (Axelar, CCIP, Aave, Compound, Morpho) │ Oracles │ Utils     │
└──────────────────────────────────────────────────────────────────────────┘
```

## 🧪 Testing

```bash
# All tests
forge test --summary

# By domain
forge test --match-path "test/CrossChain*" -vv   # Lending
forge test --match-path "test/Escrow*" -vv       # Escrow
forge test --match-path "test/Identity*" -vv     # Identity

# By type
forge test --match-contract "Fuzz" -vv           # Fuzz tests
forge test --match-contract "Invariant" -vv      # Invariant tests
```

## 📄 Documentation

- [Architecture Overview](../docs/ARCHITECTURE.md)
- [Testing Strategy](../docs/TESTING.md)

---

*Built with Solidity ^0.8.30 & Foundry*
