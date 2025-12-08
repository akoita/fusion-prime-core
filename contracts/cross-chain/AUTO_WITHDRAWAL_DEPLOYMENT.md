# Automatic Withdrawal in Deployment Scripts

## Overview

Starting with **V26**, all deployment scripts automatically withdraw funds from the previous vault version before deploying the new version. This eliminates the need for manual withdrawal steps.

---

## How It Works

### 1. **Integrated Withdrawal**
Each `DeployVaultVXX.s.sol` script now includes a `withdrawFromPreviousVault()` function that:
- Checks if a previous vault exists
- Reads your collateral and supplied balances
- Attempts to withdraw both
- Continues with deployment even if withdrawal fails

### 2. **Automatic Execution**
When you run the deployment script:
```bash
forge script script/DeployVaultV26.s.sol:DeployVaultV26 \
  --rpc-url $RPC_URL \
  --broadcast
```

The script automatically:
1. ✅ Withdraws from V25 vault
2. ✅ Deploys V26 vault
3. ✅ Logs all actions

---

## Deployment Workflow

### Standard Deployment (V26+)

```bash
cd contracts/cross-chain

# Deploy to Sepolia (auto-withdraws from V25)
forge script script/DeployVaultV26.s.sol:DeployVaultV26 \
  --rpc-url https://sepolia.infura.io/v3/YOUR_KEY \
  --broadcast

# Deploy to Amoy (auto-withdraws from V25)
forge script script/DeployVaultV26.s.sol:DeployVaultV26 \
  --rpc-url https://polygon-amoy.infura.io/v3/YOUR_KEY \
  --broadcast --legacy
```

**That's it!** No manual withdrawal needed.

---

## Creating V27, V28, etc.

When creating the next version:

1. **Copy the previous deployment script:**
   ```bash
   cp script/DeployVaultV26.s.sol script/DeployVaultV27.s.sol
   ```

2. **Update the contract name and constants:**
   ```solidity
   contract DeployVaultV27 is Script {  // Change V26 -> V27

       // Update previous vault addresses to V26
       address constant SEPOLIA_PREVIOUS_VAULT = 0xYourV26SepoliaAddress;
       address constant AMOY_PREVIOUS_VAULT = 0xYourV26AmoyAddress;

       // ... rest stays the same
   }
   ```

3. **Deploy:**
   ```bash
   forge script script/DeployVaultV27.s.sol:DeployVaultV27 \
     --rpc-url $RPC_URL \
     --broadcast
   ```

---

## Example Output

```
=== CrossChainVault V26 Deployment ===
Deployer: 0xe1fc045daBb45b78fC2D48D32086E4a0b11ca6eA
Chain ID: 80002

=== Withdrawing from Previous Vault ===
Previous Vault: 0xbafd9d789f96d18cedd057899a4ba3273c9f6d0e
Collateral Balance: 100000000000000000
Supplied Balance: 0
Withdrawing collateral...
Collateral withdrawn successfully
Withdrawal attempt complete

=== Deploying New Vault ===
Network: Polygon Amoy
BridgeManager: 0xEEcd2114162D577c4668B8e92a6FB34d0eA6A149
Axelar Gateway: 0x2A723E9BBD44C27A0F0FC13f46C41Ab59EDdd6E8
CCIP Router: 0x9C32fCB86BF0f4a1A8921a9Fe46de3198bb884B2
Vault deployed at: 0xNewV26Address

=== Deployment Complete ===
New Vault Address: 0xNewV26Address

Next steps:
1. Update frontend config with new vault address
2. Configure trusted vaults (setTrustedVault)
3. Update PREVIOUS_VAULT constants in DeployVaultV27.s.sol
```

---

## Handling Failures

The script is designed to be **resilient**:

- ✅ If previous vault doesn't exist → Skips withdrawal, continues deployment
- ✅ If no funds to withdraw → Skips withdrawal, continues deployment
- ✅ If withdrawal fails (cross-chain issue) → Logs error, continues deployment
- ✅ If vault version incompatible → Logs error, continues deployment

**Deployment always proceeds**, even if withdrawal fails.

---

## Manual Withdrawal (Fallback)

If automatic withdrawal fails, you can still use the standalone tools:

```bash
# Single vault
forge script script/EmergencyWithdrawAll.s.sol:EmergencyWithdrawAll \
  --rpc-url $RPC_URL \
  --broadcast \
  --sig "run(address)" <VAULT_ADDRESS>

# All vaults
./script/WithdrawFromAllVaults.sh sepolia
```

---

## Benefits

1. **Streamlined Workflow** - One command does everything
2. **No Forgotten Withdrawals** - Automatic, can't forget
3. **Testnet Token Conservation** - Recovers tokens before each deployment
4. **Resilient** - Continues even if withdrawal fails
5. **Clear Logging** - See exactly what happened

---

## Migration from V25 to V26

If you're currently on V25 and want to adopt this pattern:

1. **Use DeployVaultV26.s.sol** for your next deployment
2. It will automatically withdraw from V25
3. For future versions (V27+), just copy and update the script

---

## Notes

- The script uses `try/catch` to handle incompatible vault versions gracefully
- Withdrawal uses 0.01 ETH gas amount (adjust if needed)
- Cross-chain withdrawals may take time to sync
- The script only withdraws from the **immediate previous version** (not all historical versions)
