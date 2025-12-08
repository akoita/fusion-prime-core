# Cross-Chain Messaging Fixes (V17)

## Critical Bugs Fixed

### 1. CCIP Receiver Encoding Bug (CRITICAL)

**Problem**: CCIPAdapter was using `abi.encode(destination)` which creates a 32-byte array, but CCIP expects `abi.encodePacked(destination)` which creates a 20-byte array.

**Impact**: Messages were being sent with incorrectly encoded receiver addresses, causing CCIP to fail to route messages to the destination vault.

**Fix**: Changed in `CCIPAdapter.sol`:
```solidity
// BEFORE (WRONG):
receiver: abi.encode(destination),  // 32 bytes - WRONG!

// AFTER (CORRECT):
receiver: abi.encodePacked(destination),  // 20 bytes - CORRECT!
```

**Files Changed**:
- `contracts/cross-chain/src/adapters/CCIPAdapter.sol` (lines 91, 119)

### 2. Missing Preferred Protocol Configuration

**Problem**: V16 deployment script registered the CCIP adapter but didn't set it as the preferred protocol for the destination chain.

**Impact**: BridgeManager might not know which adapter to use, or might fail to find an adapter, causing message sending to fail.

**Fix**: Added protocol preference setting in deployment script:
```solidity
bridgeManager.setPreferredProtocol(destinationChainName, "ccip");
```

**Files Changed**:
- `contracts/cross-chain/script/DeployVaultV16.s.sol` (added step 3b)

### 3. CCIP Sender Decoding (Already Fixed in V16)

**Status**: Already fixed in V16 - uses assembly to correctly decode 20-byte packed addresses.

## Root Cause Analysis

The cross-chain messaging failures were caused by **multiple encoding mismatches**:

1. **Receiver Encoding**: CCIP expects 20-byte packed addresses, but we were sending 32-byte encoded addresses
2. **Sender Decoding**: CCIP sends 20-byte packed addresses, but we were trying to decode as 32-byte (fixed in V16)
3. **Protocol Selection**: BridgeManager wasn't configured to use CCIP, so it might fail to route messages

## Testing Checklist

After deploying V17 (with these fixes):

### CCIP Testing
- [ ] Deploy V17 on Sepolia
- [ ] Deploy V17 on Polygon Amoy
- [ ] Set trusted vaults on both chains
- [ ] Verify preferred protocol is set to "ccip" for destination chain
- [ ] Test deposit on Sepolia → verify syncs to Amoy
- [ ] Test deposit on Amoy → verify syncs to Sepolia
- [ ] Check CCIP Explorer for successful message delivery

### Axelar Testing (if using)
- [ ] Verify Axelar adapter is registered
- [ ] Set preferred protocol to "axelar" if needed
- [ ] Test deposit with Axelar
- [ ] Verify chain name translation works ("polygon" → "polygon-sepolia")

## Deployment Steps

1. **Deploy V17 contracts** (same as V16, but with fixes):
   ```bash
   forge script contracts/cross-chain/script/DeployVaultV16.s.sol:DeployVaultV16 \
     --rpc-url $SEPOLIA_RPC_URL --broadcast --verify

   forge script contracts/cross-chain/script/DeployVaultV16.s.sol:DeployVaultV16 \
     --rpc-url $AMOY_RPC_URL --broadcast --verify
   ```

2. **Verify protocol preferences**:
   ```bash
   # Check on Sepolia
   cast call <BRIDGE_MANAGER> "preferredProtocol(string)" "polygon" --rpc-url $SEPOLIA_RPC_URL
   # Should return: "ccip"

   # Check on Amoy
   cast call <BRIDGE_MANAGER> "preferredProtocol(string)" "ethereum" --rpc-url $AMOY_RPC_URL
   # Should return: "ccip"
   ```

3. **Set trusted vaults** (if not done automatically):
   ```bash
   # On Sepolia
   cast send <SEPOLIA_VAULT> "setTrustedVault(string,address)" \
     "polygon" <AMOY_VAULT> --rpc-url $SEPOLIA_RPC_URL --private-key $KEY

   # On Amoy
   cast send <AMOY_VAULT> "setTrustedVault(string,address)" \
     "ethereum" <SEPOLIA_VAULT> --rpc-url $AMOY_RPC_URL --private-key $KEY
   ```

## Expected Behavior After Fix

1. **Message Sending**: Messages should be sent successfully via CCIP
2. **Message Delivery**: CCIP should route messages to the correct vault address
3. **Message Execution**: Vault should receive and process messages correctly
4. **Balance Sync**: Vault balances should update on destination chain

## Debugging Tips

If messages still fail:

1. **Check CCIP Explorer**: Verify message was sent and check execution status
2. **Verify Receiver Encoding**: Check that receiver is 20 bytes (not 32)
3. **Check Protocol Preference**: Ensure BridgeManager knows to use CCIP
4. **Verify Trusted Vaults**: Ensure both chains have each other's vault addresses
5. **Check Gas**: Ensure sufficient gas is provided (200k configured)

## Related Issues

- V16: Fixed sender decoding (20-byte packed addresses)
- V15: Fixed Router/OffRamp address separation
- V11-V14: Various router address issues

## Files Modified

- `contracts/cross-chain/src/adapters/CCIPAdapter.sol`
- `contracts/cross-chain/script/DeployVaultV16.s.sol`
