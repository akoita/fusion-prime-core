# Emergency Withdrawal Tools (DEV ONLY)

## ⚠️ WARNING: TESTNET DEVELOPMENT ONLY

These tools are **temporary utilities** for recovering testnet tokens during development. They should be **removed before mainnet deployment**.

---

## Purpose

During development, you may deploy 20+ versions of vaults for testing. Each deployment may have testnet tokens (ETH, MATIC) deposited for testing purposes. These tools help you:

1. **Recover testnet tokens** before deploying a new version
2. **Conserve limited testnet faucet tokens**
3. **Clean up old test deployments**

---

## Tools Provided

### 1. Single Vault Withdrawal: `EmergencyWithdrawAll.s.sol`

Withdraw all funds (collateral + supplied) from a **specific vault**.

**Usage:**
```bash
cd contracts/cross-chain

# Withdraw from Sepolia V25 Vault
forge script script/EmergencyWithdrawAll.s.sol:EmergencyWithdrawAll \
  --rpc-url https://sepolia.infura.io/v3/YOUR_KEY \
  --broadcast \
  --sig "run(address)" 0x477f54284367CF31B2B7f6BB2Ca4291D3f43a312

# Withdraw from Amoy V25 Vault
forge script script/EmergencyWithdrawAll.s.sol:EmergencyWithdrawAll \
  --rpc-url https://polygon-amoy.infura.io/v3/YOUR_KEY \
  --broadcast --legacy \
  --sig "run(address)" 0xbafd9d789f96d18cedd057899a4ba3273c9f6d0e
```

**What it does:**
- Checks your collateral balance in the vault
- Checks your supplied balance in the vault
- Withdraws both (if any) to your deployer address
- Handles errors gracefully (skips if no funds)

---

### 2. Bulk Withdrawal: `WithdrawFromAllVaults.sh`

Withdraw from **all known vault versions** on a chain with one command.

**Usage:**
```bash
cd contracts/cross-chain

# Withdraw from all Sepolia vaults
./script/WithdrawFromAllVaults.sh sepolia

# Withdraw from all Amoy vaults
./script/WithdrawFromAllVaults.sh amoy
```

**What it does:**
- Loops through all known vault addresses (V23, V24, V25, etc.)
- Attempts withdrawal from each
- Skips vaults with no funds or errors
- Provides a summary at the end

---

## Adding New Vault Versions

When you deploy a new vault version, add its address to `WithdrawFromAllVaults.sh`:

```bash
VAULTS=(
    # ... existing vaults ...

    # V26 Vaults (add your new deployment)
    "0xYourNewSepoliaVault" # Sepolia V26
    "0xYourNewAmoyVault"    # Amoy V26
)
```

---

## Before Mainnet Deployment

**CRITICAL:** Remove these files before mainnet:

```bash
rm contracts/cross-chain/script/EmergencyWithdrawAll.s.sol
rm contracts/cross-chain/script/WithdrawFromAllVaults.sh
rm contracts/cross-chain/EMERGENCY_WITHDRAWAL.md
```

Or add them to `.gitignore` to prevent accidental commits to production branches.

---

## Example Workflow

**Before deploying a new vault version:**

```bash
# 1. Withdraw from all old vaults
cd contracts/cross-chain
./script/WithdrawFromAllVaults.sh sepolia
./script/WithdrawFromAllVaults.sh amoy

# 2. Check your balance (should have recovered testnet tokens)
cast balance $DEPLOYER_ADDRESS --rpc-url $SEPOLIA_RPC
cast balance $DEPLOYER_ADDRESS --rpc-url $AMOY_RPC

# 3. Deploy new version
forge script script/DeployVaultV26.s.sol:DeployVaultV26 \
  --rpc-url $SEPOLIA_RPC \
  --broadcast

# 4. Update WithdrawFromAllVaults.sh with new addresses
# (for next time)
```

---

## Troubleshooting

**"Could not read collateral balance"**
- The vault version might be incompatible (different function signatures)
- The vault might be on a different chain
- You might have no deposits in that vault
- This is normal and the script will skip it

**"Withdrawal failed"**
- Cross-chain messaging might be failing (like with V25)
- Try withdrawing manually via the frontend
- Or wait for cross-chain sync to complete

**"No funds to withdraw"**
- You have no deposits in that vault
- The vault is on a different chain
- Funds were already withdrawn

---

## Notes

- These tools use the `PRIVATE_KEY` environment variable from `.env.dev`
- Withdrawals trigger cross-chain broadcasts (may take time to sync)
- Gas costs are minimal on testnets
- The script handles both collateral and supplied balances
