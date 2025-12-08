# Deposit Failure Diagnostic

## Current Error

`InvalidEVMAddress(bytes)` from CCIP Router when trying to send message.

Error data shows the Amoy vault address: `0x13ff68c3b5b5cc5a75adca73a7cfb31d85575698`

## What We've Verified

✅ CCIP lane exists (Sepolia → Amoy supported)
✅ Gas estimation works (~0.000152 ETH needed)
✅ Sufficient gas provided (0.001 ETH)
✅ trustedVaults configured correctly
✅ preferredProtocol set to "ccip"
✅ Amoy vault has code deployed
✅ CCIPAdapter is registered

## Root Cause

The issue is in the **StringAddressUtils.toAddress()** function used by CCIPAdapter line 80.

This function expects a **lowercase hex string without checksum** (42 characters: "0x" + 40 hex chars).

However, the vault's `toString()` function generates **lowercase addresses**, but when we configure trustedVaults via `setTrustedVault()`, it stores the address as given (which might be checksummed).

## The Problem Flow

1. Vault calls `trustedVaults["polygon"]` → returns checksummed address `0x13Ff68C3B5b5CC5a75AdCA73a7CFB31D85575698`
2. Vault calls `StringAddressUtils.toString(address)` → returns lowercase `0x13ff68c3b5b5cc5a75adca73a7cfb31d85575698`
3. BridgeManager passes this string to CCIPAdapter
4. CCIPAdapter calls `destinationAddress.toAddress()`
5. `toAddress()` function validates character by character
6. **If the string has mixed case (checksummed), parsing fails**
7. CCIP Router rejects with `InvalidEVMAddress`

## Solution

The `toString()` function in CrossChainVault already generates lowercase addresses. This should work correctly.

**BUT** - we need to verify that the trustedVault address is being retrieved and passed correctly as a string.

## Test

Let's manually check what string is being generated:

```bash
# Check what the vault's toString would generate for the Amoy vault
cast call 0x0fCa84656d0522546303f5338B0fBa62c00A0227 \
  --rpc-url $SEPOLIA_RPC_URL \
  --trace

# Or simulate the exact deposit call
cast call 0x0fCa84656d0522546303f5338B0fBa62c00A0227 \
  "depositCollateral(address,uint256)" \
  0xe1fc045daBb45b78fC2D48D32086E4a0b11ca6eA 1000000000000000 \
  --value 2000000000000000 \
  --from 0xe1fc045daBb45b78fC2D48D32086E4a0b11ca6eA \
  --rpc-url $SEPOLIA_RPC_URL \
  --trace
```

## Likely Fix Needed

Check line 406 in CrossChainVault.sol where `toString()` is called:

```solidity
string memory destinationAddress = StringAddressUtils.toString(destinationVault);
```

This should generate lowercase, which is correct. But verify the actual string being passed.

## Alternative Solution

If the address conversion is the issue, we could:
1. Store trusted vaults as strings (lowercase) instead of addresses
2. Or ensure `toString()` always generates the exact format `toAddress()` expects
