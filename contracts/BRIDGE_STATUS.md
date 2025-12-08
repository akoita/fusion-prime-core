# Cross-Chain Bridge Status & Configuration Issues

## Current Status (As of Nov 5, 2025)

### Working Routes ✅
- **Sepolia → Polygon Amoy**: Uses Axelar, **WORKS** ✅
  - Gas: 0.02 ETH (~$0.05)
  - Transaction time: 3-5 minutes
  - Example: Transfers from Sepolia successfully deliver to Amoy

### Broken Routes ❌
- **Polygon Amoy → Sepolia**: **DOES NOT WORK** ❌
  - Both Axelar and CCIP have configuration issues
  - All transactions revert on-chain
  - See detailed analysis below

---

## Root Cause Analysis

### Issue #1: Axelar Chain Name Mismatch

**Problem**: Axelar adapters deployed with wrong chain names

**Deployed Configuration**:
```solidity
// What we deployed:
supportedChains = ["ethereum", "polygon", "arbitrum"]
```

**Required Configuration**:
```solidity
// What Axelar Gateway requires (testnet):
supportedChains = ["ethereum-sepolia", "polygon-sepolia", "arbitrum-sepolia"]
```

**Impact**:
- Axelar Gateway doesn't recognize "ethereum" as a valid destination
- Transaction reverts when calling `gateway.callContract("ethereum", ...)`
- Silent revert with no error message

**Source**: https://github.com/axelarnetwork/axelar-contract-deployments/blob/main/axelar-chains-config/info/testnet.json

**Verification**:
```bash
# Check deployed chain names (WRONG):
cast call 0x6e48D179CD80979c8eDf65A5d783B501A0313159 "supportedChains(uint256)(string)" 0 --rpc-url https://rpc-amoy.polygon.technology
# Returns: "ethereum" ❌

# Axelar Gateway expects: "ethereum-sepolia" ✅
```

---

### Issue #2: CCIP Chain Selector Mismatch

**Problem**: CCIP adapters deployed with incorrect chain selectors

**Deployed Configuration (Sepolia)**:
```solidity
// Polygon Amoy selector in Sepolia CCIPAdapter:
chainNameToSelector["polygon"] = 12532609583862916517  // ❌ WRONG
```

**Correct Configuration**:
```solidity
// Official Chainlink CCIP selector for Polygon Amoy:
chainNameToSelector["polygon"] = 16281711391670634445  // ✅ CORRECT
```

**Deployed Configuration (Amoy)** - Partially Correct:
```solidity
// Ethereum Sepolia selector in Amoy CCIPAdapter:
chainNameToSelector["ethereum"] = 16015286601757825753  // ✅ CORRECT!
```

**Impact**:
- Sepolia → Amoy via CCIP: Fails (wrong Amoy selector)
- Amoy → Sepolia via CCIP: Still fails despite correct selector
  - Likely requires LINK tokens for CCIP fees
  - CCIPAdapter doesn't handle LINK token approval/transfer
  - CCIP Router getFee() reverts

**Source**: https://docs.chain.link/ccip/directory/testnet/chain/polygon-testnet-amoy

**Verification**:
```bash
# Check Amoy selector (CORRECT):
cast call 0xe15A30f1eF8c1De56F19b7Cef61cC3776119451C "chainNameToSelector(string)(uint64)" "ethereum" --rpc-url https://rpc-amoy.polygon.technology
# Returns: 16015286601757825753 ✅

# But transactions still fail - CCIP needs LINK tokens
```

---

## Why Sepolia → Amoy Works

**Current Configuration**:
- BridgeManager on Sepolia: `preferredProtocol["polygon"] = "axelar"`
- Axelar on Sepolia: Has "polygon" in supported chains
- Axelar Gateway: **Appears to accept "polygon" as alias for "polygon-sepolia"** OR has fallback logic

**Theory**: Axelar Gateway might have:
1. Backwards compatibility for simplified chain names
2. Internal mapping from "polygon" → "polygon-sepolia"
3. Or we got lucky with the specific direction

**Needs Investigation**: Why does Sepolia → Amoy work with "polygon" but Amoy → Sepolia fails with "ethereum"?

---

## Failed Transaction Examples

### Axelar Failure (Amoy → Sepolia)
```
Transaction: 0xb41eaafa5e3a5dde82ec0be9b9a4dbe4f93fe07c686b93c9ed7c152431bea72a
Status: Reverted (0)
Error: Silent revert in Axelar Gateway
Cause: Gateway doesn't recognize "ethereum" as valid chain

Contract Call:
  BridgeManager.sendMessage("ethereum", ...) →
  AxelarAdapter.sendMessage("ethereum", ...) →
  AxelarGateway.callContract("ethereum", ...) → ❌ REVERT
```

### CCIP Failure (Amoy → Sepolia)
```
Transaction: 0xe75eb7af8fe0571e12d1edf382be312122a3bff00c7a89facb0049740c75abd8
Status: Reverted (0)
Error: Silent revert in CCIP Router
Cause: Missing LINK token approval or insufficient LINK balance

Contract Call:
  BridgeManager.sendMessage("ethereum", ...) →
  CCIPAdapter.sendMessage("ethereum", ...) →
  CCIPRouter.getFee(...) → ❌ REVERT (needs LINK)
```

---

## Solutions & Workarounds

### Temporary Workaround (Current)
**Status**: Implemented ✅

Only support one direction:
- ✅ **Sepolia → Amoy**: Use Axelar (working)
- ❌ **Amoy → Sepolia**: Disabled in UI or show warning

**Implementation**:
```typescript
// In frontend, detect direction and warn user
if (sourceChainId === polygonAmoy.id && destChainId === sepolia.id) {
  showWarning("Transfers from Amoy to Sepolia are temporarily disabled due to bridge configuration issues. Please transfer from Sepolia to Amoy instead.");
}
```

---

### Permanent Fix #1: Redeploy Axelar Adapters
**Status**: Script created ✅ (`FixAxelarChainNames.s.sol`)

**Steps**:
1. Deploy new AxelarAdapter with correct chain names:
   ```solidity
   chainNames = ["ethereum-sepolia", "polygon-sepolia", "arbitrum-sepolia"]
   ```

2. Problem: BridgeManager doesn't allow re-registering protocols
   ```solidity
   function registerAdapter(IBridgeAdapter adapter) external {
       string memory protocolName = adapter.getProtocolName();
       require(address(adapters[protocolName]) == address(0), "Already registered");
       // ❌ Can't update existing "axelar" adapter
   }
   ```

3. Workaround Options:
   - Deploy new BridgeManager (loses all configuration)
   - Add `updateAdapter()` function to BridgeManager (requires upgrade)
   - Use different protocol name like "axelar-v2" (confusing)

**Script**: `contracts/script/FixAxelarChainNames.s.sol`

---

### Permanent Fix #2: Redeploy CCIP Adapters
**Status**: Script created ✅ (`FixCCIPSelector.s.sol`)

**Steps**:
1. Deploy new CCIPAdapter on Sepolia with correct Amoy selector:
   ```solidity
   chainSelectors[polygonAmoy] = 16281711391670634445  // Correct
   ```

2. Deploy new CCIPAdapter on Amoy with LINK token handling:
   ```solidity
   // Need to add LINK token approval logic
   // CCIP requires LINK for cross-chain fees
   IERC20(linkToken).approve(address(router), feeAmount);
   router.ccipSend{value: msg.value}(...);
   ```

3. Same registration problem as Axelar

**Script**: `contracts/script/FixCCIPSelector.s.sol`

---

### Permanent Fix #3: Deploy New BridgeManager (Recommended)
**Status**: Not implemented

**Approach**:
1. Deploy fresh BridgeManager contracts on both chains
2. Deploy new Axelar adapters with correct chain names
3. Deploy new CCIP adapters with correct selectors + LINK handling
4. Update frontend to use new BridgeManager addresses
5. Test thoroughly on testnet before mainnet

**Advantages**:
- Clean slate with correct configuration
- No legacy issues
- Can add proper access control and upgrade functionality

**Implementation Time**: 2-4 hours

---

## Testing Checklist

### Before Deployment
- [ ] Verify Axelar chain names match official config
- [ ] Verify CCIP chain selectors match Chainlink docs
- [ ] Test CCIP with LINK token handling
- [ ] Test both directions: Sepolia ⇄ Amoy
- [ ] Test gas estimation accuracy
- [ ] Verify transaction receipts show success

### After Deployment
- [ ] Test small amount transfer (0.001 ETH)
- [ ] Verify cross-chain message delivered
- [ ] Check gas costs are reasonable (~0.01-0.05)
- [ ] Test error handling (insufficient balance, wrong network, etc.)
- [ ] Monitor for 24 hours to catch edge cases

---

## Deployment History

### Initial Deployment (Oct 2024)
- Deployed with simplified chain names ("ethereum", "polygon")
- Incorrect CCIP selectors based on old documentation
- No LINK token handling in CCIP adapter

### Fix Attempts (Nov 5, 2025)
1. **Commit f8c30be**: Switched Sepolia → Amoy to Axelar
   - Result: ✅ Works

2. **Commit 8c0d5b4, 140487b**: Fixed chain name mapping in frontend
   - Result: ❌ Contract-level issue remains

3. **Commit 241d6f6**: Fixed gas amount (0.02 instead of 0.000000066)
   - Result: ✅ Gas now sufficient, but other issues remain

4. **Commit 4a7d2ee**: Switched Amoy → Sepolia to CCIP
   - Result: ❌ CCIP has LINK token requirement

5. **Commit ac43dd9**: Fixed frontend to detect reverted transactions
   - Result: ✅ UI now shows errors properly

### Current State (Commit ac43dd9)
- Sepolia → Amoy: ✅ Working via Axelar
- Amoy → Sepolia: ❌ Not working (both protocols broken)
- Frontend: ✅ Properly detects and shows errors

---

## Recommendations

### For Demo/Testing (Now)
1. **Only demonstrate Sepolia → Amoy transfers** ✅
2. Add UI warning for unsupported direction
3. Document limitation in pitch materials
4. Emphasize bidirectional support coming soon

### For Production (Before Mainnet)
1. **Deploy new BridgeManager** with correct configuration
2. Add comprehensive integration tests
3. Implement monitoring and alerting
4. Have rollback plan ready
5. Start with small transaction limits

### For Future Improvements
1. Add adapter upgrade functionality to BridgeManager
2. Implement multi-protocol fallback (try Axelar if CCIP fails)
3. Add better error messages from adapters
4. Monitor cross-chain message delivery success rates
5. Consider using Chainlink CCIP Lane Status service

---

## Contact & References

- **Axelar Docs**: https://docs.axelar.dev/
- **CCIP Docs**: https://docs.chain.link/ccip
- **Axelar Config**: https://github.com/axelarnetwork/axelar-contract-deployments
- **CCIP Directory**: https://docs.chain.link/ccip/directory/testnet

---

**Last Updated**: November 6, 2025
**Status**: New BridgeManager V2 deployed on both chains with correct configuration. Ready for testing.
**Next Action**: Test bidirectional transfers to verify fixes

## V2 Deployment (November 6, 2025)

Successfully deployed new BridgeManager infrastructure with corrected configuration:

**Sepolia (Chain ID: 11155111)**:
- BridgeManager: 0xB5ac8CFf9899a9cB2007f082436b204203D67112
- AxelarAdapter: 0x0bC90be49066FcBb6eDec4C9E039b03a3F3B8F35
- CCIPAdapter: 0xcA1cF99910755231F4fdc0153e85558cb048E357

**Polygon Amoy (Chain ID: 80002)**:
- BridgeManager: 0xE47E64C6837EFfd1675FBE3ab16334ec8E8C96F4
- AxelarAdapter: 0x4894EaE1e5BBf64C571701FA6aCFBDD68b43930e
- CCIPAdapter: 0xeFd7c5F535Ea635A329FDAD0AC7598873305dF93

**Configuration**:
- Axelar chain names: "ethereum-sepolia", "polygon-sepolia", "arbitrum-sepolia" (CORRECT)
- CCIP selectors: Sepolia (16015286601757825753), Amoy (16281711391670634445) (CORRECT)
- Preferred protocol: Axelar for all testnet routes
- Frontend updated with new contract addresses and chain names
