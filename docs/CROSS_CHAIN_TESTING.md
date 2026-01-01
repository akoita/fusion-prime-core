# Cross-Chain Integration Testing

This document describes how to test cross-chain functionality using local Anvil networks.

## Overview

The protocol supports cross-chain operations via Axelar and CCIP bridges. For local testing, we deploy to multiple Anvil instances simulating different chains.

## Local Multi-Chain Setup

### 1. Start Multiple Anvil Instances

```bash
# Terminal 1 - Chain A (simulating Ethereum)
anvil --port 31337 --chain-id 31337

# Terminal 2 - Chain B (simulating Polygon)
anvil --port 31338 --chain-id 31338

# Terminal 3 - Chain C (simulating Arbitrum)
anvil --port 31339 --chain-id 31339
```

### 2. Deploy Contracts to Each Chain

```bash
# Deploy to Chain A
PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
forge script script/DeployMultiChainLocal.s.sol:DeployMultiChainLocal \
  --rpc-url http://127.0.0.1:31337 \
  --broadcast

# Deploy to Chain B
PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
forge script script/DeployMultiChainLocal.s.sol:DeployMultiChainLocal \
  --rpc-url http://127.0.0.1:31338 \
  --broadcast

# Deploy to Chain C
PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
forge script script/DeployMultiChainLocal.s.sol:DeployMultiChainLocal \
  --rpc-url http://127.0.0.1:31339 \
  --broadcast
```

### 3. Configure Bridge Connections

After deployment, note the contract addresses and configure cross-chain connections:

```solidity
// On Chain A, register Chain B's vault
bridgeManager.registerRemoteVault("chain-b", chainBVaultAddress);

// On Chain B, register Chain A's vault
bridgeManager.registerRemoteVault("chain-a", chainAVaultAddress);
```

## Test Scenarios

### Cross-Chain Deposit
1. User deposits on Chain A
2. Liquidity is available on Chain A
3. User can borrow on Chain A using collateral

### Cross-Chain Borrow (Advanced)
1. User has collateral on Chain A
2. User borrows on Chain B using cross-chain liquidity
3. BridgeManager routes the request via Axelar/CCIP
4. Funds are transferred and borrowed on Chain B

### Cross-Chain Liquidation
1. Position becomes undercollateralized on Chain A
2. Liquidator on Chain B can trigger liquidation
3. Collateral is seized and transferred

## Running Integration Tests

### Unit Tests (Mock-Based)
```bash
# These use MockAxelarGateway and MockCCIPRouter
forge test --match-contract "AxelarAdapter|CCIPAdapter|BridgeManager" -vvv
```

### Local Multi-Chain Tests
```bash
# Start Anvil instances first
./scripts/run-multichain-tests.sh
```

## CI/CD Integration

The GitHub Actions workflow includes cross-chain tests:

```yaml
cross-chain-tests:
  name: Cross-Chain Integration Tests
  runs-on: ubuntu-latest
  steps:
    - name: Run Bridge Adapter Tests
      run: forge test --match-contract "AxelarAdapter|CCIPAdapter|BridgeManager" -vvv
    
    - name: Run CrossChainVault Tests
      run: forge test --match-contract "CrossChainVault" -vvv
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Chain A (Ethereum)                       │
│  ┌─────────────────┐    ┌─────────────────┐                    │
│  │ CrossChainVault │◄───│  BridgeManager  │                    │
│  └─────────────────┘    └────────┬────────┘                    │
└──────────────────────────────────┼──────────────────────────────┘
                                   │ Axelar/CCIP
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Chain B (Polygon)                        │
│  ┌─────────────────┐    ┌─────────────────┐                    │
│  │ CrossChainVault │◄───│  BridgeManager  │                    │
│  └─────────────────┘    └─────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
```

## Mock Contracts

For unit testing without live bridges:

- `MockAxelarGateway.sol` - Simulates Axelar message passing
- `MockAxelarGasService.sol` - Simulates gas payment
- `MockCCIPRouter.sol` - Simulates Chainlink CCIP

These mocks allow testing cross-chain logic without actual network connections.
