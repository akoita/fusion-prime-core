# Fusion Prime Core Architecture

## Overview
Fusion Prime is a multi-chain DeFi protocol that enables cross-chain liquidity provisioning, borrowing, and secure asset management. The system is designed with a domain-driven approach, separating lending, escrow, and identity management into distinct, interoperable modules.

## Core Components

### 1. Lending Module (`contracts/src/lending/`)
The lending module handles liquidity pools, interest rate models, and cross-chain borrowing.
- **CrossChainVault**: The primary entry point for users to deposit collateral and borrow assets. It supports local and remote liquidity.
- **LiquidityRouter**: Orchestrates liquidity discovery across multiple chains and bridge adapters.
- **InterestRateModel**: Dynamically calculates borrowing costs based on pool utilization.

### 2. Identity Module (`contracts/src/identity/`)
A decentralized identity system implementing ERC-734 and ERC-735.
- **Identity**: A smart contract-based account that manages cryptographic keys and identity claims.
- **IdentityFactory**: Facilitates the deployment and management of identity contracts.
- **ClaimIssuerRegistry**: A registry for trusted entities that can issue verified claims (e.g., KYC/AML).

### 3. Escrow Module (`contracts/src/escrow/`)
A secure system for conditional asset transfers.
- **Escrow**: Handles the locking and releasing of assets between payers and payees.
- **EscrowWithIdentity**: An advanced escrow that integrates with the Identity module to enforce compliance requirements (e.g., KYC-only transfers).

### 4. Bridge & Connectivity (`contracts/src/adapters/` & `contracts/src/base/`)
Infrastructure for cross-chain message passing and asset bridging.
- **AxelarAdapter**: Integration with the Axelar network for remote contract calls and token transfers.
- **CCIPAdapter**: Integration with Chainlink CCIP.
- **BridgeManager**: Manages multiple bridge adapters to provide redundancy and flexibility.

## Security Architecture

### Compliance & Verification
The `IdentityVerifier` library provides a non-invasive way for any contract to verify user claims without directly interacting with complex identity logic. This allows "Opt-in Compliance" where specific vaults or escrows can mandate certain credentials.

### Risk Management
- **Collateralization**: All borrowing is over-collateralized by verified price feeds.
- **Pause Mechanisms**: Critical contracts include emergency stop functionality managed by the protocol governance.
- **Reentrancy Protection**: Standard guards are implemented across all state-changing external functions.

## Technical Stack
- **Languages**: Solidity ^0.8.20
- **Framework**: Foundry
- **Libraries**: OpenZeppelin (Access Control, Pausable, ReentrancyGuard, SafeERC20)
