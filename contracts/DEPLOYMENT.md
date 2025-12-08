# Fusion Prime Contract Deployment Guide

> **📖 Looking for environment-specific deployment steps?** See **[../DEPLOYMENT.md](../DEPLOYMENT.md)** for complete local, test, and production deployment workflows.

This guide covers **smart contract deployment details** using **Foundry** across multiple chains.

## Features

- ✅ **EscrowFactory Pattern**: Factory deploys individual escrow instances
- ✅ **CREATE2 Support**: Deterministic escrow addresses
- ✅ **Multichain Ready**: Deploy to multiple EVM chains
- ✅ **Automatic Verification**: Contracts verified on block explorers
- ✅ **Deployment Artifacts**: JSON outputs for backend integration

## Prerequisites

### 1. Install Foundry

```bash
# Install/update Foundry
curl -L https://foundry.paradigm.xyz | bash
foundryup

# Verify installation
forge --version
```

### 2. Install Dependencies

```bash
cd contracts
forge install
```

### 3. Configure Environment

```bash
# Copy example environment file
cp env.example .env

# Edit .env with your values
nano .env
```

**Required Variables:**
- `PRIVATE_KEY`: Deployer wallet private key
- `SEPOLIA_RPC_URL`: Ethereum Sepolia RPC endpoint
- `AMOY_RPC_URL`: Polygon Amoy RPC endpoint
- `ETHERSCAN_API_KEY`: Etherscan API key for verification

## Architecture

### Contracts

**EscrowFactory**
- Factory contract for deploying individual Escrow instances
- Each escrow is an immutable, standalone contract
- Supports both CREATE and CREATE2 deployment
- Tracks all deployed escrows via events and mappings

**Escrow** (deployed by factory)
- Timelocks for automated releases
- Multi-signature approval system (1-3 approvers)
- Emergency refund mechanism
- Optional arbiter for dispute resolution
- Immutable logic (no upgrades)

### Deployment Flow

```
┌─────────────────────────────────┐
│      EscrowFactory              │
│  (Deployed once per chain)      │
└────────────┬────────────────────┘
             │
             │ createEscrow()
             ▼
  ┌─────────────────────────┐
  │   Escrow Instance #1    │
  │   (payer, payee, etc)   │
  └─────────────────────────┘
             │
             │ createEscrow()
             ▼
  ┌─────────────────────────┐
  │   Escrow Instance #2    │
  │   (payer, payee, etc)   │
  └─────────────────────────┘
```

## Deployment Commands

### Single Chain Deployment

#### Deploy to Sepolia

```bash
forge script script/DeployMultichain.s.sol:DeployMultichain \
  --rpc-url sepolia \
  --broadcast \
  --verify \
  -vvvv
```

#### Deploy to Polygon Amoy

```bash
forge script script/DeployMultichain.s.sol:DeployMultichain \
  --rpc-url amoy \
  --broadcast \
  --verify \
  -vvvv
```

#### Deploy to Local Anvil (Development)

```bash
# Start Anvil in a separate terminal
anvil

# Deploy
forge script script/DeployMultichain.s.sol:DeployMultichain \
  --rpc-url http://localhost:8545 \
  --broadcast \
  -vvv
```

### Verify Deployment

```bash
# Check factory deployment
cast code <FACTORY_ADDRESS> --rpc-url <RPC_URL>

# Get escrow count
cast call <FACTORY_ADDRESS> "getEscrowCount()(uint256)" --rpc-url <RPC_URL>

# Create test escrow
cast send <FACTORY_ADDRESS> \
  "createEscrow(address,uint256,uint8,address)" \
  <PAYEE_ADDRESS> \
  86400 \
  2 \
  0x0000000000000000000000000000000000000000 \
  --value 0.01ether \
  --private-key <PRIVATE_KEY> \
  --rpc-url <RPC_URL>
```

## Verification on Etherscan

If automatic verification fails:

```bash
# Verify EscrowFactory
forge verify-contract \
  --chain sepolia \
  --etherscan-api-key $ETHERSCAN_API_KEY \
  <FACTORY_ADDRESS> \
  src/EscrowFactory.sol:EscrowFactory

# Verify individual Escrow instance
forge verify-contract \
  --chain sepolia \
  --etherscan-api-key $ETHERSCAN_API_KEY \
  --constructor-args $(cast abi-encode "constructor(address,address,uint256,uint8,address)" <PAYER> <PAYEE> <DELAY> <APPROVALS> <ARBITER>) \
  <ESCROW_ADDRESS> \
  src/Escrow.sol:Escrow
```

## Deployment Artifacts

After successful deployment, artifacts are saved to:

```
deployments/
├── <chainId>-<chainName>.json
└── ...
```

**Example JSON:**
```json
{
  "chainId": 11155111,
  "chainName": "sepolia",
  "escrowFactory": "0x0F146104422a920E90627f130891bc948298d6F8",
  "timestamp": 1729353215
}
```

## Backend Integration

### Listening for New Escrows

Monitor the `EscrowDeployed` event from EscrowFactory:

```solidity
event EscrowDeployed(
    address indexed escrow,
    address indexed payer,
    address indexed payee,
    uint256 amount,
    uint256 releaseDelay,
    uint8 approvalsRequired
);
```

### Listening for Escrow Events

Each escrow instance emits:

```solidity
event EscrowCreated(address indexed payer, address indexed payee, uint256 amount, uint256 releaseTime, uint8 approvalsRequired);
event Approved(address indexed approver);
event EscrowReleased(address indexed payee, uint256 amount, uint256 releasedAt);
event EscrowRefunded(address indexed payer, uint256 amount, uint256 refundedAt);
event ArbiterChanged(address indexed oldArbiter, address indexed newArbiter);
```

## Multichain Configuration

Edit `multichain-config.toml` to customize deployment across chains:

```toml
[chains.sepolia]
chain_id = 11155111
rpc_url_env = "SEPOLIA_RPC_URL"
explorer_url = "https://sepolia.etherscan.io"
explorer_api_key_env = "ETHERSCAN_API_KEY"

[chains.amoy]
chain_id = 80002
rpc_url_env = "AMOY_RPC_URL"
explorer_url = "https://www.oklink.com/amoy"
explorer_api_key_env = "ETHERSCAN_API_KEY"
```

## Testing Deployments

```bash
# Run all tests
forge test

# Run tests with gas reporting
forge test --gas-report

# Test factory deployment
forge test --match-contract EscrowFactoryTest -vvv

# Fork testing against live deployment
forge test --fork-url <RPC_URL>
```

## Security Considerations

1. **Immutable Escrows**: Each escrow instance cannot be upgraded, ensuring funds safety
2. **Factory Simplicity**: Factory has minimal logic, reducing attack surface
3. **No Admin Keys**: Escrows are controlled only by payers, payees, and arbiters
4. **Timelock Protection**: Funds cannot be released before the specified time
5. **Emergency Refunds**: Payers can recover funds after 30 days past release time

## Troubleshooting

**Issue**: Verification fails
```bash
# Try manual verification with --watch flag
forge verify-contract --watch \
  --chain sepolia \
  <ADDRESS> \
  src/EscrowFactory.sol:EscrowFactory
```

**Issue**: Gas estimation fails
```bash
# Check RPC connection
cast chain-id --rpc-url <RPC_URL>

# Check balance
cast balance <DEPLOYER_ADDRESS> --rpc-url <RPC_URL>
```

**Issue**: Deployment reverts
```bash
# Run simulation without broadcast
forge script script/DeployMultichain.s.sol:DeployMultichain \
  --rpc-url <RPC_URL> \
  -vvvv
```

## Deployed Contracts

### Identity System (Sepolia Testnet)
**Deployment Date:** 2025-11-04

| Contract | Address | Purpose |
|----------|---------|---------|
| ClaimIssuerRegistry | `0xc88BCD77b2839fDf5499e91b3618eb7049F6CE21` | Manages trusted claim issuers |
| IdentityFactory | `0x59A97ebb44C7ebd23f5755A0C46F946d177319Ca` | Factory for deploying user identities |

**Documentation:** See [identity/DEPLOYMENT.md](identity/DEPLOYMENT.md) for detailed information

**Features:**
- ERC-734 Key Management - Multi-key identity system
- ERC-735 Claim Holder - On-chain verification claims
- KYC/AML claim issuance via trusted issuers
- Integration with Persona KYC and Compliance Service

### Escrow System (Sepolia Testnet)

| Contract | Address | Purpose |
|----------|---------|---------|
| EscrowFactory | `0x311E63dfcEfe7f2c202715ef0DF01CDA82f58914` | Factory for deploying escrows |

## Next Steps

1. ✅ Deploy EscrowFactory to testnets (Sepolia, Amoy) - **COMPLETE**
2. ✅ Deploy Cross-Chain contracts to testnets (Sepolia, Amoy) - **COMPLETE**
3. ✅ Deploy Identity System to Sepolia - **COMPLETE** (2025-11-04)
4. Verify contracts on block explorers
5. Test identity creation and claim issuance
6. Test escrow creation via cast/ethers.js
7. Test cross-chain settlement flows
8. Integrate contract addresses into backend services
9. Set up event monitoring for EscrowDeployed and CrossChainMessageSent
10. Plan mainnet deployment with multi-sig deployer

## Support

For issues or questions:
- Check `contracts/test/` for usage examples
- Review `contracts/src/` for contract source code
- See parent QUICKSTART.md for full stack setup
