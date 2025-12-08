# Cross-Chain Vault - Deployment & Development Guide

**Purpose**: Comprehensive guide for deploying and developing cross-chain vaults

**Status**: Active (V23 Production)

**Last Updated**: 2025-11-20

---

## Current Production System

### V23 Vaults (Custom MessageBridge)

**Sepolia Testnet**
- Address: `0x397c9aFDBB18803931154bbB6F9854fcbdaEeCff`
- Bridge: Custom MessageBridge (relayer-based)
- Explorer: [Etherscan](https://sepolia.etherscan.io/address/0x397c9aFDBB18803931154bbB6F9854fcbdaEeCff)

**Amoy Testnet**
- Address: `0xf0dba0090aaAEAe37dBe9Ce1c3a117b766b8A31d`
- Bridge: Custom MessageBridge (relayer-based)
- Explorer: [PolygonScan](https://amoy.polygonscan.com/address/0xf0dba0090aaAEAe37dBe9Ce1c3a117b766b8A31d)

---

## Quick Start

### Deploy New Vault Version

```bash
cd contracts/cross-chain

# Deploy to Sepolia (auto-withdraws from previous version)
forge script script/DeployVaultV26.s.sol:DeployVaultV26 \
  --rpc-url https://sepolia.infura.io/v3/YOUR_KEY \
  --broadcast

# Deploy to Amoy
forge script script/DeployVaultV26.s.sol:DeployVaultV26 \
  --rpc-url https://polygon-amoy.infura.io/v3/YOUR_KEY \
  --broadcast --legacy
```

The deployment script automatically:
1. Withdraws funds from previous vault
2. Deploys new vault
3. Logs all actions

### Configure Trusted Vaults

```bash
# Sepolia trusts Amoy
cast send <SEPOLIA_VAULT> "setTrustedVault(string,address)" \
  "polygon" <AMOY_VAULT> \
  --rpc-url $SEPOLIA_RPC --private-key $PRIVATE_KEY

# Amoy trusts Sepolia
cast send <AMOY_VAULT> "setTrustedVault(string,address)" \
  "ethereum" <SEPOLIA_VAULT> \
  --rpc-url $AMOY_RPC --private-key $PRIVATE_KEY --legacy
```

---

## Development Workflow

### Automatic Withdrawal (V26+)

Starting with V26, deployment scripts automatically withdraw testnet tokens from previous vaults:

```solidity
// DeployVaultV26.s.sol includes:
function withdrawFromPreviousVault(uint256 privateKey, address deployer) internal {
    // Checks balances
    // Withdraws collateral
    // Withdraws supplied funds
    // Continues deployment even if withdrawal fails
}
```

**Benefits**:
- Conserves testnet tokens
- One-command deployment
- Graceful failure handling

### Manual Withdrawal (Fallback)

If automatic withdrawal fails:

```bash
# Single vault
forge script script/EmergencyWithdrawAll.s.sol:EmergencyWithdrawAll \
  --rpc-url $RPC_URL \
  --broadcast \
  --sig "run(address)" <VAULT_ADDRESS>

# All vaults on a chain
./script/WithdrawFromAllVaults.sh sepolia
./script/WithdrawFromAllVaults.sh amoy
```

---

## Architecture

### V23 (Production)
- **Bridge**: Custom MessageBridge (relayer-based)
- **Features**: Supply/lend, interest rates, cross-chain collateral
- **Status**: ✅ Operational
- **Pros**: Reliable, no external dependencies, lower gas
- **Cons**: Requires relayer infrastructure

### V25 (Experimental)
- **Bridge**: Axelar Gateway + CCIP Router
- **Status**: ⏸️ Deferred (cross-chain messaging issues)
- **Files**: Kept for future reference
- **Decision**: Focus on core features with stable V23

---

## Interest Rate Model

```
Base Rate: 2% APY (minimum)
Utilization Rate = Total Borrowed / Total Supplied
Borrow APY = Base Rate + (Utilization Rate × 18%)
Supply APY = Borrow APY × Utilization Rate × 90%
```

**Example**:
- 50% utilization → 11% borrow APY → 4.95% supply APY
- 80% utilization → 16.4% borrow APY → 11.8% supply APY

---

## Testing

### View Functions
```bash
# Check supply APY
cast call <VAULT> "getSupplyAPY(string)(uint256)" "polygon" --rpc-url $RPC

# Check liquidity
cast call <VAULT> "chainLiquidity(string)(uint256)" "polygon" --rpc-url $RPC

# Check user balance
cast call <VAULT> "userCollateralByChain(address,string)(uint256)" \
  <USER> "polygon" --rpc-url $RPC
```

### Integration Tests
```bash
cd contracts/cross-chain
forge test -vvv
```

---

## Troubleshooting

### Deployment Fails
- **Check balance**: Ensure deployer has sufficient ETH/MATIC
- **Check RPC**: Verify RPC URL is correct and responsive
- **Check private key**: Ensure `PRIVATE_KEY` env var is set

### Withdrawal Fails
- **Cross-chain sync**: May take time for messages to propagate
- **Incompatible version**: Old vaults may have different function signatures
- **No funds**: Check balance before withdrawing

### Frontend Not Connecting
- **Check config**: Verify vault addresses in `chains.ts` and `useVaultV25.ts`
- **Restart dev server**: `npm run dev` to pick up changes
- **Clear cache**: Hard refresh browser (Ctrl+Shift+R)

---

## Version History

| Version | Date | Status | Notes |
|---------|------|--------|-------|
| V23 | 2025-11 | ✅ Production | Custom MessageBridge |
| V24 | 2025-11 | Deprecated | Chainlink oracles added |
| V25 | 2025-11 | ⏸️ Deferred | Axelar/CCIP (messaging issues) |
| V26 | Future | Planned | Auto-withdrawal deployment |

---

## Related Documentation

- [Sprint 10 Summary](/home/koita/dev/web3/fusion-prime/SPRINT_10_COMPLETION_SUMMARY.md)
- [Frontend Config](/home/koita/dev/web3/fusion-prime/frontend/risk-dashboard/src/config/chains.ts)
- [Auto-Withdrawal Guide](./AUTO_WITHDRAWAL_DEPLOYMENT.md)
- [Emergency Withdrawal](./EMERGENCY_WITHDRAWAL.md)

---

## Maintenance

### Before Each New Deployment

1. Run withdrawal script (automatic in V26+)
2. Update `PREVIOUS_VAULT` constants in next deployment script
3. Deploy to both chains
4. Configure trusted vaults
5. Update frontend config
6. Test basic operations

### Quarterly Review

- Archive old deployment docs (V16-V24)
- Update this guide with latest practices
- Review and consolidate troubleshooting
- Test all commands

---

**For detailed deployment history, see archived docs in `docs/archive/deployments/`**
