# V16 Deployment Guide

## Overview

V16 fixes the critical CCIP sender address decoding bug that was causing cross-chain messages to fail execution on the destination chain.

## Key Fix

**Problem**: CCIP encodes sender addresses using `abi.encodePacked(address)`, which creates a 20-byte array. The previous code used `abi.decode()`, which expects 32-byte padded ABI-encoded data, causing a revert.

**Solution**: Use assembly to correctly extract the 20-byte address from calldata:

```solidity
address sender;
assembly {
    // Copy 20 bytes from calldata to memory at offset 12 (to right-align in 32-byte word)
    calldatacopy(12, message.sender.offset, 20)
    // Load the 32-byte word (address is in rightmost 20 bytes)
    sender := mload(0)
}
```

## Deployment Instructions

### Prerequisites

1. Set environment variable:
   ```bash
   export DEPLOYER_PRIVATE_KEY=<your_private_key>
   ```

2. Ensure you have sufficient testnet ETH/MATIC on both chains

### Step 1: Deploy on Sepolia

```bash
forge script contracts/cross-chain/script/DeployVaultV16.s.sol:DeployVaultV16 \
  --rpc-url $SEPOLIA_RPC_URL \
  --broadcast \
  --verify \
  -vvvv
```

**Expected Output:**
- BridgeManager: `<address>`
- CCIPAdapter: `<address>`
- CrossChainVault: `<address>`

### Step 2: Deploy on Polygon Amoy

```bash
forge script contracts/cross-chain/script/DeployVaultV16.s.sol:DeployVaultV16 \
  --rpc-url $AMOY_RPC_URL \
  --broadcast \
  --verify \
  -vvvv
```

**Expected Output:**
- BridgeManager: `<address>`
- CCIPAdapter: `<address>`
- CrossChainVault: `<address>`

### Step 3: Configure Trusted Vaults

After deploying on both chains, set the trusted vault addresses:

**On Sepolia:**
```bash
cast send <SEPOLIA_VAULT_ADDRESS> \
  "setTrustedVault(string,address)" \
  "polygon" <AMOY_VAULT_ADDRESS> \
  --rpc-url $SEPOLIA_RPC_URL \
  --private-key $DEPLOYER_PRIVATE_KEY
```

**On Amoy:**
```bash
cast send <AMOY_VAULT_ADDRESS> \
  "setTrustedVault(string,address)" \
  "ethereum" <SEPOLIA_VAULT_ADDRESS> \
  --rpc-url $AMOY_RPC_URL \
  --private-key $DEPLOYER_PRIVATE_KEY
```

### Step 4: Update Frontend Configuration

Update `frontend/risk-dashboard/src/config/chains.ts`:

```typescript
export const CONTRACTS = {
  // Sepolia Testnet (11155111)
  [sepolia.id]: {
    EscrowFactory: '0x311E63dfcEfe7f2c202715ef0DF01CDA82f58914' as const,
    // CCIP V16 deployment - Fixed sender address decoding
    CrossChainVault: '<SEPOLIA_VAULT_ADDRESS>' as const,
    BridgeManager: '<SEPOLIA_BRIDGE_MANAGER_ADDRESS>' as const,
    CCIPAdapter: '<SEPOLIA_CCIP_ADAPTER_ADDRESS>' as const,
  },
  // Polygon Amoy Testnet (80002)
  [polygonAmoy.id]: {
    // CCIP V16 deployment - Fixed sender address decoding
    CrossChainVault: '<AMOY_VAULT_ADDRESS>' as const,
    BridgeManager: '<AMOY_BRIDGE_MANAGER_ADDRESS>' as const,
    CCIPAdapter: '<AMOY_CCIP_ADAPTER_ADDRESS>' as const,
  },
} as const;
```

### Step 5: Verify Deployment

1. **Check CCIP Explorer**: Verify messages are being sent successfully
2. **Test Deposit**: Make a deposit on Sepolia and verify it syncs to Amoy
3. **Check Vault Balance**: Verify `getTotalCollateral()` updates on both chains

## CCIP Configuration

### Router Addresses (for sending)
- **Sepolia**: `0x0BF3dE8c5D3e8A2B34D2BEeB17ABfCeBaf363A59`
- **Amoy**: `0x9C32fCB86BF0f4a1A8921a9Fe46de3198bb884B2`

### OffRamp Addresses (for receiving)
- **Sepolia**: `0x0BF3dE8c5D3e8A2B34D2BEeB17ABfCeBaf363A59` (same as Router)
- **Amoy**: `0x7Ad494C173f5845c6B4028a06cDcC6d3108bc960` (different!)

### Chain Selectors
- **Sepolia**: `16015286601757825753`
- **Amoy**: `16281711391670634445`

## Testing

After deployment, test with:

```bash
# Deposit on Sepolia
cast send <SEPOLIA_VAULT_ADDRESS> \
  "depositCollateral(address,uint256)" \
  <USER_ADDRESS> <GAS_AMOUNT> \
  --value <DEPOSIT_AMOUNT> \
  --rpc-url $SEPOLIA_RPC_URL \
  --private-key $USER_PRIVATE_KEY

# Check balance on Amoy (should sync automatically)
cast call <AMOY_VAULT_ADDRESS> \
  "getTotalCollateral(address)" \
  <USER_ADDRESS> \
  --rpc-url $AMOY_RPC_URL
```

## Troubleshooting

### Messages Still Failing

1. **Check OffRamp Address**: Ensure vault is configured with correct OffRamp (not Router)
2. **Verify Trusted Vaults**: Both chains must have each other's vault address configured
3. **Check Gas Limits**: Ensure sufficient gas is provided (200k configured in adapter)
4. **Verify Chain Selectors**: Ensure correct selectors are mapped in vault

### Frontend Not Updating

1. **Clear Browser Cache**: Hard refresh (Ctrl+Shift+R)
2. **Check Network**: Ensure connected to correct chain
3. **Verify Addresses**: Double-check addresses in `chains.ts` match deployed contracts

## Previous Versions

- **V15**: Fixed Router/OffRamp address separation but still had sender decoding bug
- **V14**: Attempted gas limit fix but still failed
- **V11-V13**: Router address authentication failures

## References

- [CCIP Explorer](https://ccip.chain.link/)
- [CCIP Documentation](https://docs.chain.link/ccip)
- Issue Report: See terminal selection lines 879-1025
