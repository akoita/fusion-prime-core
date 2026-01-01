# Cross-Chain DeFi Lending Protocol Architecture

A sophisticated cross-chain lending protocol built on EVM-compatible blockchains with multi-layer security testing.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend DApp                             │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                      LiquidityRouter                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │LocalAdapter │  │BridgeAdapter│  │ ExternalProtocolAdapters│  │
│  └──────┬──────┘  └──────┬──────┘  └────────────┬────────────┘  │
└─────────┼────────────────┼──────────────────────┼───────────────┘
          │                │                      │
┌─────────▼────────┐ ┌─────▼─────┐  ┌─────────────▼─────────────┐
│CrossChainVault   │ │BridgeManager│ │ Aave/Compound/Morpho     │
│   ┌──────────┐   │ │  ┌──────┐  │ │       Adapters           │
│   │VaultBase │   │ │  │Axelar│  │ └───────────────────────────┘
│   └──────────┘   │ │  │CCIP  │  │
│   ┌──────────┐   │ │  └──────┘  │
│   │Interest  │   │ └────────────┘
│   │RateModel │   │
│   └──────────┘   │
│   ┌──────────┐   │
│   │PriceOracle│  │
│   └──────────┘   │
└──────────────────┘
```

## Core Contracts

### CrossChainVaultBase
The foundational vault contract implementing:
- **Deposit/Withdraw**: Native ETH and ERC20 token collateral
- **Borrow/Repay**: Variable and stable interest rate modes
- **Liquidation**: 50% close factor with 5% liquidation bonus
- **Flash Loans**: 0.09% fee, atomic execution
- **Interest Accrual**: Per-second compounding with reserve factor

### CrossChainVault
Extends VaultBase with compliance features:
- **KYC/AML Integration**: ERC-735 identity claims
- **Compliance Modes**: Permissionless or whitelist
- **Trusted Issuers**: Multi-issuer claim verification

### LiquidityRouter
Aggregates liquidity from multiple sources:
- **Local Vault**: Direct borrowing
- **Cross-Chain**: Axelar/CCIP bridged liquidity
- **External Protocols**: Aave V3, Compound V3, Morpho

### BridgeManager
Unified cross-chain messaging interface:
- **Multi-Protocol**: Axelar, Chainlink CCIP
- **Route Optimization**: Preferred protocol per chain
- **Gas Estimation**: Cross-chain fee calculation

## Key Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| Liquidation Threshold | 80% | Health factor trigger |
| Liquidation Bonus | 5% | Incentive for liquidators |
| Close Factor | 50% | Max liquidatable per tx |
| Reserve Factor | 10% | Protocol fee on interest |
| Flash Loan Fee | 0.09% | Atomic borrow cost |
| Stable Rate Lock | 30 days | Min stable period |
| Unpause Timelock | 24 hours | Security delay |

## Security Model

### Multi-Layer Testing
1. **Unit Tests**: Specific behavior verification
2. **Fuzz Tests**: Random input discovery
3. **Invariant Tests**: Stateful property verification
4. **Symbolic Tests**: Bounded path exploration (Halmos)
5. **Formal Verification**: Mathematical proofs (Certora)
6. **Static Analysis**: Vulnerability detection (Slither/Aderyn)

### Access Control
- Owner-only admin functions
- Timelock on unpause
- Reentrancy guards on all state-changing functions

### Invariants
- `totalBorrowed <= totalDeposited` (Solvency)
- `healthFactor >= 100` for healthy positions
- `reserves >= 0` always
