# Sprint 08: Automatic Cross-Chain Sync & Message Tracking

**Duration**: 1 week (November 20-26, 2025)
**Status**: 📋 **PLANNED**
**Goal**: Fix automatic cross-chain broadcasting and add message tracking UI

**Last Updated**: 2025-11-06

---

## Context

**Current Issue**: When users deposit/withdraw/borrow/repay, the vault tries to broadcast state updates to all other chains automatically, but the transaction fails due to a gas payment issue.

**Problem** (contracts/cross-chain/src/CrossChainVault.sol:260):
```solidity
function _sendCrossChainMessage(string memory destinationChain, bytes memory payload) internal {
    bridgeManager.sendMessage{value: msg.value}(...);
    // ❌ msg.value was already consumed by deposit() function
}
```

**Current Workaround**: Users manually trigger sync via CrossChainTransfer page

**Sprint Objective**: Make automatic broadcasting work, eliminating manual sync requirement

---

## Strategic Value

Automatic synchronization is critical for user experience:
- **Without Auto-Sync**: User deposits on Sepolia, must manually sync to see balance on Amoy
- **With Auto-Sync**: User deposits on Sepolia, Amoy balance updates automatically in 1-2 minutes

This completes the "seamless cross-chain" promise.

---

## Objectives

### 1. Fix Gas Payment Mechanism ✅
**Goal**: Enable vault to pay for cross-chain message broadcasts

**Problem Analysis**:
```solidity
// depositCollateral() is payable and receives msg.value
function depositCollateral(address user) external payable {
    require(msg.value > 0, "Amount must be greater than 0");

    // msg.value used here for collateral
    collateralBalances[user][thisChainName] += msg.value;
    totalCollateral[user] += msg.value;

    // Tries to use msg.value again for gas - FAILS!
    _broadcastCollateralUpdate(user, thisChainName, msg.value, true);
}
```

**Solution Options**:

**Option A: User Sends Extra Gas** (Recommended)
```solidity
function depositCollateral(address user, uint256 gasAmount) external payable {
    require(msg.value > gasAmount, "Must send collateral + gas");

    uint256 collateralAmount = msg.value - gasAmount;
    collateralBalances[user][thisChainName] += collateralAmount;
    totalCollateral[user] += collateralAmount;

    _broadcastCollateralUpdate(user, thisChainName, collateralAmount, true, gasAmount);
}

function _broadcastCollateralUpdate(..., uint256 gasAmount) internal {
    uint256 gasPerChain = gasAmount / (allSupportedChains.length - 1);
    for (uint256 i = 0; i < allSupportedChains.length; i++) {
        if (keccak256(bytes(allSupportedChains[i])) != keccak256(bytes(thisChainName))) {
            _sendCrossChainMessage(allSupportedChains[i], payload, gasPerChain);
        }
    }
}
```

**Option B: Vault Pre-Funding**
- Admin pre-funds vault with gas tokens
- Vault uses internal balance for broadcasts
- More complex, requires monitoring and refilling

**Option C: Lazy Sync**
- Don't broadcast automatically
- Broadcast only when user explicitly requests sync
- Simplest but defeats "automatic" goal

**Decision**: **Option A** - User pays, simple and transparent

**Estimated Time**: 6 hours (3h contracts, 2h frontend, 1h testing)

---

### 2. Update Smart Contracts
**Goal**: Modify vault functions to accept separate gas payment

**Files to Update**:

**contracts/cross-chain/src/CrossChainVault.sol**:
```solidity
// Update function signatures to accept gas amount
function depositCollateral(address user, uint256 gasAmount) external payable {
    require(msg.value > gasAmount, "Insufficient payment");
    uint256 collateralAmount = msg.value - gasAmount;
    // ... rest of logic
}

function withdrawCollateral(uint256 amount, uint256 gasAmount) external payable {
    require(msg.value >= gasAmount, "Insufficient gas payment");
    // ... withdrawal logic
    _broadcastCollateralUpdate(msg.sender, thisChainName, amount, false, gasAmount);
}

function borrow(uint256 amount, uint256 gasAmount) external payable {
    require(msg.value >= gasAmount, "Insufficient gas payment");
    // ... borrow logic
}

function repay(uint256 amount, uint256 gasAmount) external payable {
    require(msg.value >= amount + gasAmount, "Insufficient payment");
    // ... repay logic
}

// Helper to estimate gas needed
function estimateCrossChainGas() public view returns (uint256) {
    uint256 numChains = allSupportedChains.length - 1;
    uint256 gasPerMessage = 0.02 ether; // Axelar testnet estimate
    return numChains * gasPerMessage;
}
```

**Testing**: Deploy to testnet and verify broadcasts work

**Estimated Time**: 4 hours

---

### 3. Update Frontend Hooks
**Goal**: Update deposit/withdraw/borrow/repay hooks to include gas payment

**Files to Update**:

**frontend/risk-dashboard/src/hooks/contracts/useVault.ts**:
```typescript
export function useDepositToVault(chainId: number = sepolia.id) {
  const vaultAddress = CONTRACTS[chainId]?.CrossChainVault as Address;

  const deposit = async (userAddress: Address, amount: string) => {
    // Get gas estimate from contract
    const gasEstimate = await readContract({
      address: vaultAddress,
      abi: VAULT_ABI,
      functionName: 'estimateCrossChainGas',
      chainId,
    });

    const collateralAmount = parseEther(amount);
    const totalValue = collateralAmount + gasEstimate;

    writeContract({
      address: vaultAddress,
      abi: VAULT_ABI,
      functionName: 'depositCollateral',
      args: [userAddress, gasEstimate],
      value: totalValue, // collateral + gas
      chainId,
    });
  };

  return { deposit, ... };
}

// Similar updates for withdraw, borrow, repay
```

**Add Gas Display in UI**:
```typescript
// In VaultDashboard.tsx
const gasEstimate = useReadContract({
  address: vaultAddress,
  abi: VAULT_ABI,
  functionName: 'estimateCrossChainGas',
  chainId,
});

// Show in form
<p className="text-sm text-gray-500">
  Cross-chain sync fee: {formatEther(gasEstimate || 0n)} ETH
</p>
```

**Estimated Time**: 4 hours

---

### 4. Message Tracking UI
**Goal**: Show users when their cross-chain messages are pending/complete

**New Component**: `frontend/risk-dashboard/src/components/vault/MessageTracker.tsx`

```typescript
interface CrossChainMessage {
  messageId: string;
  sourceChain: string;
  destChain: string;
  user: Address;
  action: 'deposit' | 'withdraw' | 'borrow' | 'repay';
  amount: bigint;
  status: 'pending' | 'confirmed' | 'failed';
  timestamp: number;
  txHash?: string;
}

export function MessageTracker({ userAddress }: { userAddress: Address }) {
  const [messages, setMessages] = useState<CrossChainMessage[]>([]);

  // Listen for CrossChainMessageSent events
  useWatchContractEvent({
    address: vaultAddress,
    abi: VAULT_ABI,
    eventName: 'CrossChainMessageSent',
    onLogs(logs) {
      // Add to messages list
    },
  });

  return (
    <div className="bg-white rounded-lg border p-4">
      <h3 className="font-semibold mb-4">Cross-Chain Messages</h3>
      {messages.length === 0 ? (
        <p className="text-gray-500 text-sm">No pending messages</p>
      ) : (
        <ul className="space-y-2">
          {messages.map(msg => (
            <li key={msg.messageId} className="flex items-center justify-between">
              <div>
                <span className="font-medium">{msg.action}</span>
                <span className="text-sm text-gray-600 ml-2">
                  {msg.sourceChain} → {msg.destChain}
                </span>
              </div>
              <MessageStatus status={msg.status} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

**Add to VaultDashboard**:
```typescript
// In VaultDashboard.tsx, add below stats cards
<MessageTracker userAddress={address} />
```

**Estimated Time**: 6 hours

---

### 5. Testing & Validation
**Goal**: Verify automatic sync works end-to-end

**Test Scenarios**:

**Test 1: Deposit with Auto-Sync**
- [ ] Deposit 0.1 ETH on Sepolia
- [ ] Pay gas fee (e.g., 0.02 ETH extra)
- [ ] Verify deposit transaction succeeds
- [ ] Wait 1-2 minutes
- [ ] Check Amoy vault shows updated balance
- [ ] Verify CrossChainMessageReceived event on Amoy

**Test 2: Withdraw with Auto-Sync**
- [ ] Withdraw 0.05 ETH on Sepolia
- [ ] Pay gas fee
- [ ] Verify withdrawal succeeds
- [ ] Check Amoy vault shows reduced balance

**Test 3: Borrow with Auto-Sync**
- [ ] Borrow 0.03 ETH on Sepolia
- [ ] Pay gas fee
- [ ] Verify borrow succeeds
- [ ] Check Amoy vault shows increased borrowed amount

**Test 4: Message Tracking UI**
- [ ] Perform deposit
- [ ] Verify message appears in tracker as "pending"
- [ ] Wait for confirmation
- [ ] Verify status changes to "confirmed"

**Test 5: Gas Estimation Accuracy**
- [ ] Call `estimateCrossChainGas()`
- [ ] Verify amount is reasonable (~0.02 ETH per chain)
- [ ] Test with insufficient gas → should fail gracefully

**Test 6: Multiple Chain Broadcasting**
- [ ] When 3 chains are supported (Sepolia, Amoy, Arbitrum)
- [ ] Verify message sent to all 2 other chains
- [ ] Verify gas split correctly

**Estimated Time**: 4 hours

---

## Week Plan

### Days 1-2 (Nov 20-21): Contract Updates
- [ ] Update CrossChainVault with gas parameter
- [ ] Add `estimateCrossChainGas()` function
- [ ] Update all vault functions (deposit, withdraw, borrow, repay)
- [ ] Write unit tests for new gas logic
- [ ] Deploy to Sepolia testnet
- [ ] Deploy to Amoy testnet

### Days 3-4 (Nov 22-23): Frontend Updates
- [ ] Update deposit hook with gas payment
- [ ] Update withdraw hook with gas payment
- [ ] Update borrow/repay hooks (if Sprint 07 complete)
- [ ] Add gas estimate display in UI
- [ ] Test all forms with new gas payment

### Day 5 (Nov 24): Message Tracking
- [ ] Create MessageTracker component
- [ ] Listen for CrossChainMessageSent events
- [ ] Add message status polling (check if confirmed)
- [ ] Integrate into VaultDashboard
- [ ] Style and polish UI

### Days 6-7 (Nov 25-26): Testing & Polish
- [ ] Run all 6 test scenarios
- [ ] Fix any bugs discovered
- [ ] Document gas requirements
- [ ] Update user-facing documentation
- [ ] Create demo video showing auto-sync

---

## Success Criteria

| Criteria | Target | Measurement |
|----------|--------|-------------|
| Automatic sync works | 100% | Deposits auto-sync to other chains |
| Gas estimation accurate | ±10% | Estimated vs actual gas used |
| Message tracking visible | 100% | Users see pending messages |
| Sync completion time | <3 min | Time from tx to confirmation |
| No failed broadcasts | >95% success | Broadcast success rate |
| UI shows gas cost | Yes | Gas fee displayed before tx |

---

## Non-Goals (Explicitly Deferred)

- ❌ Gasless transactions (meta-transactions)
- ❌ Gas refunds for failed syncs
- ❌ Optimizing gas cost (batching multiple messages)
- ❌ Retry mechanism for failed messages (separate feature)
- ❌ Historical message archive (only show recent)

**Rationale**: Focus on making basic auto-sync work. Optimizations can be Sprint 11.

---

## Risk Management

### Risk: Gas Estimates Too Low
**Mitigation**: Add 20% buffer to estimates, test with real transactions

### Risk: Axelar Fee Changes
**Mitigation**: Make gas estimate dynamic, don't hardcode values

### Risk: Broadcast Fails Silently
**Mitigation**: Emit events on success/failure, show in UI

### Risk: User Confused by Gas Fee
**Mitigation**: Clear explanation in UI: "Fee to sync across chains"

---

## Dependencies

**Required** (from Sprint 07):
- ✅ Deposit/withdraw working (already complete)
- 🟡 Borrow/repay working (Sprint 07 in progress)

**Blockers**: None - can proceed independently

---

## Documentation Updates

**Files to Update**:
- [ ] `CROSSCHAIN_VAULT_SPEC.md` - Update "Cross-Chain Sync Issues" section
- [ ] `contracts/cross-chain/README.md` - Document gas payment mechanism
- [ ] `frontend/risk-dashboard/README.md` - Add auto-sync usage guide
- [ ] `IMPLEMENTATION_ROADMAP.md` - Mark Phase 2 as complete

---

## Metrics

**Sprint Velocity Target**:
- **Story Points**: 24 hours estimated work
- **Features Delivered**: 3 (gas payment, auto-sync, message tracking)
- **Contract Changes**: 1 contract updated, 4 functions modified
- **Frontend Changes**: 4 hooks updated, 1 new component

**Quality Metrics**:
- **Test Coverage**: 6 test scenarios
- **Success Rate**: >95% of broadcasts succeed
- **User Experience**: < 3 min sync time

---

## Retrospective Questions

1. Does the gas payment mechanism feel intuitive to users?
2. Are gas estimates accurate enough?
3. Is the message tracker useful or just noise?
4. Should we batch multiple operations to save gas?
5. Do we need retry mechanism for failed broadcasts?

---

## Links & References

- **Smart Contract**: `contracts/cross-chain/src/CrossChainVault.sol:260` (gas payment issue)
- **Frontend Hooks**: `frontend/risk-dashboard/src/hooks/contracts/useVault.ts`
- **Roadmap**: `/IMPLEMENTATION_ROADMAP.md` Phase 2 (lines 166-195)
- **Spec**: `/CROSSCHAIN_VAULT_SPEC.md` (Cross-Chain Sync Issues section)

---

**Document Version**: 1.0
**Status**: 📋 Planned (starts after Sprint 07 completion)
**Predecessor**: Sprint 07 (Borrowing/Lending UI)
**Successor**: Sprint 09 (Risk Management & Safety)
