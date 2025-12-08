# V20 Deposit Failure Fix

## Problem

Deposit is failing on V20 vault (`0xb0e352b60264C926f7B19F0fC5A1eeE499163c19` on Amoy).

## Possible Causes

### 1. Trusted Vaults Not Configured (Most Likely)

V20 requires trusted vaults to be set on both chains before deposits work.

### 2. Minimum Gas Amount

V20 enforces `MIN_GAS_AMOUNT = 0.01 ether`. You're sending `0.01 ETH` which should be sufficient, but make sure:
- `gasAmount >= 0.01 ether` (10000000000000000 wei)
- `msg.value > gasAmount` (you need to send deposit amount + gas)

## Quick Fix

### Step 1: Configure Trusted Vaults

Run the configuration script on **both chains**:

**On Sepolia:**
```bash
forge script contracts/cross-chain/script/ConfigureV20.s.sol:ConfigureV20 \
  --rpc-url $SEPOLIA_RPC_URL \
  --broadcast \
  -vvvv
```

**On Amoy:**
```bash
forge script contracts/cross-chain/script/ConfigureV20.s.sol:ConfigureV20 \
  --rpc-url $AMOY_RPC_URL \
  --broadcast \
  -vvvv
```

### Step 2: Verify Configuration

**Check trusted vault on Amoy:**
```bash
cast call 0xb0e352b60264C926f7B19F0fC5A1eeE499163c19 \
  "trustedVaults(string)" "ethereum" \
  --rpc-url $AMOY_RPC_URL
# Should return: 0x5820443E51ED666cDFe3d19f293f72CD61829C5d
```

**Check trusted vault on Sepolia:**
```bash
cast call 0x5820443E51ED666cDFe3d19f293f72CD61829C5d \
  "trustedVaults(string)" "polygon" \
  --rpc-url $SEPOLIA_RPC_URL
# Should return: 0xb0e352b60264C926f7B19F0fC5A1eeE499163c19
```

### Step 3: Verify Minimum Gas

Check the minimum gas requirement:
```bash
cast call 0xb0e352b60264C926f7B19F0fC5A1eeE499163c19 \
  "MIN_GAS_AMOUNT()" \
  --rpc-url $AMOY_RPC_URL
# Should return: 10000000000000000 (0.01 ETH)
```

## V20 Vault Addresses

- **Sepolia**: `0x5820443E51ED666cDFe3d19f293f72CD61829C5d`
- **Amoy**: `0xb0e352b60264C926f7B19F0fC5A1eeE499163c19`

## Frontend Fix

Make sure your frontend is sending:
- `gasAmount`: At least `0.01 ETH` (10000000000000000 wei)
- `value`: `depositAmount + gasAmount` (must be greater than gasAmount)

Example:
```typescript
const gasAmountWei = parseEther("0.01"); // Minimum required
const depositAmountWei = parseEther("0.1"); // Your deposit
const totalValue = depositAmountWei + gasAmountWei;

writeContract({
  functionName: 'depositCollateral',
  args: [userAddress, gasAmountWei],
  value: totalValue, // Must be > gasAmountWei
});
```

## Debugging

If deposit still fails after configuration:

1. **Check error message**: The contract should revert with a specific error. Check the transaction receipt for the actual revert reason.

2. **Check BridgeManager**: Ensure protocol preferences are set:
   ```bash
   # Get BridgeManager address
   cast call 0xb0e352b60264C926f7B19F0fC5A1eeE499163c19 \
     "bridgeManager()" \
     --rpc-url $AMOY_RPC_URL

   # Check preferred protocol
   cast call <BRIDGE_MANAGER> \
     "preferredProtocol(string)" "ethereum" \
     --rpc-url $AMOY_RPC_URL
   ```

3. **Check supported chains**: Verify the vault supports the destination chain:
   ```bash
   cast call 0xb0e352b60264C926f7B19F0fC5A1eeE499163c19 \
     "supportedChains(string)" "ethereum" \
     --rpc-url $AMOY_RPC_URL
   ```

## Related Files

- Configuration script: `contracts/cross-chain/script/ConfigureV20.s.sol`
- V20 deployment: `contracts/cross-chain/DEPLOYMENT_V20.md`
- Safety features: `contracts/cross-chain/V20_SAFETY_FEATURES.md`
