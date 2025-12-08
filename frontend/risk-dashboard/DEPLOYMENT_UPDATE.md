# Frontend Deployment Update Guide

## Quick Update After V16 Deployment

After deploying V16 contracts, update the frontend configuration:

### File to Update
`src/config/chains.ts`

### Update Template

Replace the addresses in the `CONTRACTS` mapping:

```typescript
export const CONTRACTS = {
  [sepolia.id]: {
    EscrowFactory: '0x311E63dfcEfe7f2c202715ef0DF01CDA82f58914' as const,
    CrossChainVault: '<SEPOLIA_VAULT_ADDRESS>' as const,      // ← Update
    BridgeManager: '<SEPOLIA_BRIDGE_MANAGER_ADDRESS>' as const, // ← Update
    CCIPAdapter: '<SEPOLIA_CCIP_ADAPTER_ADDRESS>' as const,   // ← Update
  },
  [polygonAmoy.id]: {
    CrossChainVault: '<AMOY_VAULT_ADDRESS>' as const,          // ← Update
    BridgeManager: '<AMOY_BRIDGE_MANAGER_ADDRESS>' as const,  // ← Update
    CCIPAdapter: '<AMOY_CCIP_ADAPTER_ADDRESS>' as const,      // ← Update
  },
} as const;
```

### Getting Addresses from Deployment

After running the deployment script, you'll see output like:

```
====================================
V16 Deployment Complete!
====================================
Chain ID: 11155111

Deployed Contracts:
  BridgeManager: 0x...
  CCIPAdapter: 0x...
  CrossChainVault: 0x...
```

Copy these addresses and update `chains.ts`.

### Verification

After updating:

1. **Restart dev server** (if running):
   ```bash
   npm run dev
   ```

2. **Clear browser cache** and hard refresh (Ctrl+Shift+R)

3. **Test connection**:
   - Switch to Sepolia network
   - Verify contract addresses load correctly
   - Switch to Polygon Amoy
   - Verify contract addresses load correctly

### Related Files

- Contract deployment: `contracts/cross-chain/script/DeployVaultV16.s.sol`
- Deployment guide: `contracts/cross-chain/DEPLOYMENT_V16.md`
- Frontend config: `src/config/chains.ts`
