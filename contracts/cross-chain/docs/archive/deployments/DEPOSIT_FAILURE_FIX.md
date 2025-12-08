# Deposit Failure Fix

## Problem

Deposit is failing with "Internal JSON-RPC error" because **trusted vaults are not configured**.

When you call `depositCollateral`, the vault tries to broadcast the update to other chains. This requires:
1. ✅ Trusted vault address configured for destination chain
2. ✅ Preferred protocol set in BridgeManager
3. ✅ Adapter registered with BridgeManager

## Root Cause

The `_sendCrossChainMessage` function checks:
```solidity
address destinationVault = trustedVaults[destinationChain];
require(destinationVault != address(0), "Destination vault not configured");
```

If the trusted vault is not set, the transaction reverts.

## Solution

Run the configuration script on **both chains**:

### Step 1: Configure Sepolia Vault

```bash
forge script contracts/cross-chain/script/ConfigureV17.s.sol:ConfigureV17 \
  --rpc-url $SEPOLIA_RPC_URL \
  --broadcast \
  -vvvv
```

This will set:
- Sepolia vault trusts Amoy vault (`0x13Ff68C3B5b5CC5a75AdCA73a7CFB31D85575698`) for "polygon" chain

### Step 2: Configure Amoy Vault

```bash
forge script contracts/cross-chain/script/ConfigureV17.s.sol:ConfigureV17 \
  --rpc-url $AMOY_RPC_URL \
  --broadcast \
  -vvvv
```

This will set:
- Amoy vault trusts Sepolia vault (`0x0fCa84656d0522546303f5338B0fBa62c00A0227`) for "ethereum" chain

### Step 3: Verify Configuration

Check the configuration:

```bash
# On Sepolia - check trusted vault
cast call 0x0fCa84656d0522546303f5338B0fBa62c00A0227 \
  "trustedVaults(string)" "polygon" \
  --rpc-url $SEPOLIA_RPC_URL
# Should return: 0x13Ff68C3B5b5CC5a75AdCA73a7CFB31D85575698

# On Amoy - check trusted vault
cast call 0x13Ff68C3B5b5CC5a75AdCA73a7CFB31D85575698 \
  "trustedVaults(string)" "ethereum" \
  --rpc-url $AMOY_RPC_URL
# Should return: 0x0fCa84656d0522546303f5338B0fBa62c00A0227
```

### Step 4: Verify Protocol Preference

Also check that the preferred protocol is set:

```bash
# Get BridgeManager address from vault
cast call 0x0fCa84656d0522546303f5338B0fBa62c00A0227 \
  "bridgeManager()" \
  --rpc-url $SEPOLIA_RPC_URL

# Check preferred protocol (replace <BRIDGE_MANAGER> with address above)
cast call <BRIDGE_MANAGER> \
  "preferredProtocol(string)" "polygon" \
  --rpc-url $SEPOLIA_RPC_URL
# Should return: "ccip"
```

## Alternative: Quick Diagnostic

Run the diagnostic script to check current configuration:

```bash
# On Sepolia
forge script contracts/cross-chain/script/CheckVaultConfig.s.sol:CheckVaultConfig \
  --rpc-url $SEPOLIA_RPC_URL

# On Amoy
forge script contracts/cross-chain/script/CheckVaultConfig.s.sol:CheckVaultConfig \
  --rpc-url $AMOY_RPC_URL
```

## After Configuration

Once trusted vaults are configured, deposits should work. The vault will:
1. Accept your deposit
2. Update local balance
3. Broadcast update to other chains via CCIP/Axelar
4. Other chains will sync the balance automatically

## V17 Vault Addresses

- **Sepolia**: `0x0fCa84656d0522546303f5338B0fBa62c00A0227`
- **Amoy**: `0x13Ff68C3B5b5CC5a75AdCA73a7CFB31D85575698`

## Related Files

- Configuration script: `contracts/cross-chain/script/ConfigureV17.s.sol`
- Diagnostic script: `contracts/cross-chain/script/CheckVaultConfig.s.sol`
- Vault contract: `contracts/cross-chain/src/CrossChainVault.sol` (line 410)
