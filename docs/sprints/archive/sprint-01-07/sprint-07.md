# Sprint 07: Cross-Chain Lending Protocol - Borrowing/Lending UI

**Duration**: 2 weeks (November 6-19, 2025)
**Status**: 🟢 **IN PROGRESS**
**Goal**: Complete the cross-chain lending protocol with borrowing/lending functionality

**Last Updated**: 2025-11-06

---

## Context

Sprint 05 delivered the CrossChainVault smart contracts with full borrowing/lending capabilities and a vault dashboard showing deposits/withdrawals. However, the borrowing and lending features are not exposed in the UI.

**Current State**:
- ✅ Smart contracts COMPLETE (deposit, withdraw, borrow, repay functions exist)
- ✅ Vault dashboard shows collateral and credit line
- ❌ No UI for borrowing
- ❌ No UI for repaying loans
- ❌ No health factor visualization
- ❌ No borrowed amounts displayed

**Sprint Objective**: Make the existing borrow/repay contract functions accessible via the frontend.

---

## Strategic Value

This sprint completes our **core value proposition**:
> "Deposit collateral on ANY chain, borrow against your TOTAL collateral across ALL chains"

**Competitive Advantage**: Cross-chain capital efficiency
- User deposits 1 ETH on Sepolia
- User borrows 0.5 MATIC on Amoy (using Sepolia ETH as collateral)
- All state automatically synced across chains

---

## Objectives

### 1. Add Borrowing Hooks ✅
**Goal**: Create React hooks for borrow/repay operations

**Tasks**:
- [ ] Create `useBorrowFromVault(chainId)` hook
- [ ] Create `useRepayToVault(chainId)` hook
- [ ] Add `borrowBalances` read hook per chain
- [ ] Update `useVaultData()` to include borrowed amounts
- [ ] Test all hooks with wallet connection

**Files to Create/Update**:
- `frontend/risk-dashboard/src/hooks/contracts/useVault.ts:230` (add new hooks)

**ABI Required**:
```typescript
// Add to VAULT_ABI
{
  inputs: [{ name: 'amount', type: 'uint256' }],
  name: 'borrow',
  outputs: [],
  stateMutability: 'nonpayable',
  type: 'function',
},
{
  inputs: [{ name: 'amount', type: 'uint256' }],
  name: 'repay',
  outputs: [],
  stateMutability: 'payable',
  type: 'function',
},
{
  inputs: [{ name: 'user', type: 'address' }, { name: 'chain', type: 'string' }],
  name: 'borrowBalances',
  outputs: [{ name: '', type: 'uint256' }],
  stateMutability: 'view',
  type: 'function',
}
```

**Estimated Time**: 4 hours

---

### 2. Update Vault Dashboard UI
**Goal**: Add borrow/repay functionality to existing dashboard

**Tasks**:
- [ ] Add "Borrowed" stat cards (Total, Sepolia, Amoy)
- [ ] Add "Borrow" tab alongside Deposit/Withdraw
- [ ] Add "Repay" tab
- [ ] Add borrowing capacity calculator
- [ ] Display available-to-borrow amount
- [ ] Show health factor gauge

**UI Components** (frontend/risk-dashboard/src/pages/cross-chain/VaultDashboard.tsx):

**New Stat Cards** (add to line 119):
```typescript
// Total Borrowed
<StaggerItem>
  <div className="bg-white border-2 border-red-200 rounded-lg p-6">
    <div className="flex items-center justify-between mb-2">
      <span className="text-sm font-medium text-gray-600">Total Borrowed</span>
      <TrendingDown className="h-5 w-5 text-red-600" />
    </div>
    <div className="text-2xl font-bold text-gray-900">
      {vaultData.isLoading ? (
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      ) : (
        `${Number(formatEther(vaultData.totalBorrowed || 0n)).toFixed(4)} ETH`
      )}
    </div>
  </div>
</StaggerItem>
```

**New Tabs** (update line 196):
```typescript
const tabs = ['deposit', 'withdraw', 'borrow', 'repay'] as const;
type TabType = typeof tabs[number];
const [activeTab, setActiveTab] = useState<TabType>('deposit');
```

**Borrow Form**:
```typescript
{activeTab === 'borrow' && (
  <form onSubmit={handleBorrow} className="space-y-4">
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Amount to Borrow
      </label>
      <input
        type="number"
        step="0.001"
        value={borrowAmount}
        onChange={(e) => setBorrowAmount(e.target.value)}
        placeholder="0.0"
        className="w-full px-4 py-3 border border-gray-300 rounded-lg"
      />
      <p className="text-sm text-gray-500 mt-2">
        Available to borrow: {Number(formatEther(vaultData.creditLine || 0n)).toFixed(4)} ETH
      </p>
    </div>
    <button
      type="submit"
      disabled={!borrowAmount || isBorrowing}
      className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg"
    >
      {isBorrowing ? 'Borrowing...' : 'Borrow from Vault'}
    </button>
  </form>
)}
```

**Repay Form**:
```typescript
{activeTab === 'repay' && (
  <form onSubmit={handleRepay} className="space-y-4">
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Amount to Repay
      </label>
      <input
        type="number"
        step="0.001"
        value={repayAmount}
        onChange={(e) => setRepayAmount(e.target.value)}
        placeholder="0.0"
        className="w-full px-4 py-3 border border-gray-300 rounded-lg"
      />
      <p className="text-sm text-gray-500 mt-2">
        Outstanding debt: {Number(formatEther(vaultData.totalBorrowed || 0n)).toFixed(4)} ETH
      </p>
    </div>
    <button
      type="submit"
      disabled={!repayAmount || isRepaying}
      className="w-full px-6 py-3 bg-green-600 text-white rounded-lg"
    >
      {isRepaying ? 'Repaying...' : 'Repay Loan'}
    </button>
  </form>
)}
```

**Estimated Time**: 8 hours

---

### 3. Health Factor Visualization
**Goal**: Show position health with color-coded indicators

**Tasks**:
- [ ] Calculate health factor: `totalCollateral / totalBorrowed`
- [ ] Display circular gauge with percentage
- [ ] Color coding:
  - Green: > 150% (healthy)
  - Yellow: 110-150% (warning)
  - Red: < 110% (danger)
- [ ] Add warning banner when health < 120%

**Implementation**:
```typescript
const healthFactor = vaultData.totalBorrowed && vaultData.totalBorrowed > 0n
  ? Number(vaultData.totalCollateral || 0n) / Number(vaultData.totalBorrowed)
  : Infinity;

const healthColor =
  healthFactor === Infinity ? 'green' :
  healthFactor > 1.5 ? 'green' :
  healthFactor > 1.1 ? 'yellow' : 'red';

const healthPercentage = healthFactor === Infinity ? 100 :
  Math.min(100, (healthFactor - 1) * 100);
```

**UI Component** (add new stat card):
```typescript
<div className={`bg-white border-2 border-${healthColor}-200 rounded-lg p-6`}>
  <div className="flex items-center justify-between mb-2">
    <span className="text-sm font-medium text-gray-600">Health Factor</span>
    <AlertCircle className={`h-5 w-5 text-${healthColor}-600`} />
  </div>
  <div className="text-2xl font-bold text-gray-900">
    {healthFactor === Infinity ? '∞' : `${healthFactor.toFixed(2)}x`}
  </div>
  <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
    <div
      className={`h-2 rounded-full bg-${healthColor}-600`}
      style={{ width: `${healthPercentage}%` }}
    />
  </div>
</div>
```

**Warning Banner** (when health < 120%):
```typescript
{healthFactor < 1.2 && healthFactor !== Infinity && (
  <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4">
    <div className="flex">
      <AlertTriangle className="h-5 w-5 text-yellow-400 mr-3" />
      <div>
        <p className="text-sm text-yellow-700">
          <strong>Warning:</strong> Your health factor is below 120%.
          Consider repaying some debt or adding more collateral.
        </p>
      </div>
    </div>
  </div>
)}
```

**Estimated Time**: 4 hours

---

### 4. Borrowed Amounts Display
**Goal**: Show borrowed amounts per chain and total

**Tasks**:
- [ ] Query `borrowBalances(user, "ethereum-sepolia")`
- [ ] Query `borrowBalances(user, "polygon-sepolia")`
- [ ] Display in stat cards
- [ ] Update `useVaultData()` hook to include these queries

**Hook Updates** (frontend/risk-dashboard/src/hooks/contracts/useVault.ts):
```typescript
export function useVaultBorrowBalance(
  userAddress?: Address,
  chainName?: string,
  vaultChainId: number = sepolia.id
) {
  const vaultAddress = CONTRACTS[vaultChainId]?.CrossChainVault as Address;

  return useReadContract({
    address: vaultAddress,
    abi: VAULT_ABI,
    functionName: 'borrowBalances',
    args: userAddress && chainName ? [userAddress, chainName] : undefined,
    chainId: vaultChainId,
    query: {
      enabled: !!vaultAddress && !!userAddress && !!chainName,
    },
  });
}

// Update useVaultData to include borrowed balances
export function useVaultData(userAddress?: Address, chainId: number = sepolia.id) {
  const sepoliaBalance = useVaultCollateralBalance(userAddress, 'ethereum-sepolia', chainId);
  const amoyBalance = useVaultCollateralBalance(userAddress, 'polygon-sepolia', chainId);
  const sepoliaBorrowed = useVaultBorrowBalance(userAddress, 'ethereum-sepolia', chainId);
  const amoyBorrowed = useVaultBorrowBalance(userAddress, 'polygon-sepolia', chainId);
  const totalCollateral = useVaultTotalCollateral(userAddress, chainId);
  const totalBorrowed = useVaultTotalBorrowed(userAddress, chainId);
  const creditLine = useVaultCreditLine(userAddress, chainId);

  return {
    sepoliaBalance: sepoliaBalance.data,
    amoyBalance: amoyBalance.data,
    sepoliaBorrowed: sepoliaBorrowed.data,
    amoyBorrowed: amoyBorrowed.data,
    totalCollateral: totalCollateral.data,
    totalBorrowed: totalBorrowed.data,
    creditLine: creditLine.data,
    isLoading:
      sepoliaBalance.isLoading ||
      amoyBalance.isLoading ||
      sepoliaBorrowed.isLoading ||
      amoyBorrowed.isLoading ||
      totalCollateral.isLoading ||
      totalBorrowed.isLoading ||
      creditLine.isLoading,
    // ... rest
  };
}
```

**Estimated Time**: 4 hours

---

### 5. Testing & Validation
**Goal**: Ensure all borrowing/lending flows work correctly

**Test Cases**:
- [ ] **Test 1**: Borrow on same chain as collateral
  - Deposit 1 ETH on Sepolia
  - Borrow 0.5 ETH on Sepolia
  - Verify borrowed amount shows in UI
  - Verify credit line decreases

- [ ] **Test 2**: Cross-chain borrowing
  - Deposit 1 ETH on Sepolia
  - Switch to Amoy network
  - Borrow 0.5 MATIC on Amoy (using Sepolia collateral)
  - Verify both vault dashboards show correct balances

- [ ] **Test 3**: Repayment
  - Repay 0.2 MATIC on Amoy
  - Verify borrowed amount decreases
  - Verify credit line increases

- [ ] **Test 4**: Health factor warnings
  - Borrow up to 95% of collateral
  - Verify warning banner appears
  - Verify health factor shows red

- [ ] **Test 5**: Insufficient collateral
  - Try to borrow more than credit line
  - Verify transaction reverts with clear error message

- [ ] **Test 6**: Withdraw with outstanding debt
  - Try to withdraw collateral with debt
  - Verify blocked if collateral < borrowed

**Estimated Time**: 6 hours

---

## Week-by-Week Plan

### Week 1 (Nov 6-12)
**Focus**: Core borrow/repay functionality

**Days 1-2 (Nov 6-7)**:
- [ ] Create borrow/repay hooks in useVault.ts
- [ ] Add ABI entries for borrow/repay functions
- [ ] Add borrowBalances query hooks
- [ ] Update useVaultData() to include borrowed amounts

**Days 3-4 (Nov 8-9)**:
- [ ] Update VaultDashboard with "Borrowed" stat cards
- [ ] Add "Borrow" and "Repay" tabs
- [ ] Implement borrow form with validation
- [ ] Implement repay form with validation
- [ ] Add loading states and error handling

**Day 5 (Nov 10)**:
- [ ] Test borrowing on same chain
- [ ] Test cross-chain borrowing scenario
- [ ] Fix any bugs discovered

**Weekend (Nov 11-12)**: Buffer for issues

---

### Week 2 (Nov 13-19)
**Focus**: Health factor visualization and polish

**Days 6-7 (Nov 13-14)**:
- [ ] Implement health factor calculation
- [ ] Add health factor stat card with gauge
- [ ] Add color-coded indicators
- [ ] Add warning banner for low health

**Days 8-9 (Nov 15-16)**:
- [ ] Comprehensive testing of all flows
- [ ] Test edge cases (borrow too much, withdraw with debt)
- [ ] UI polish and animations
- [ ] Documentation updates

**Day 10 (Nov 17)**:
- [ ] Final bug fixes
- [ ] Update CROSSCHAIN_VAULT_SPEC.md with completed features
- [ ] Record demo video showing cross-chain borrowing

**Days 11-12 (Nov 18-19)**: Sprint wrap-up and documentation

---

## Success Criteria

| Criteria | Target |
|----------|--------|
| Can borrow on current chain | ✅ Working |
| Can repay loans | ✅ Working |
| Borrowed amounts displayed | ✅ Per chain + total |
| Health factor visible | ✅ With color coding |
| Warning when health < 120% | ✅ Visible banner |
| Cross-chain borrowing works | ✅ Full scenario tested |
| UI is polished | ✅ Professional quality |
| No critical bugs | 0 bugs |

---

## Non-Goals (Explicitly Deferred)

These features are NOT included in Sprint 07:

- ❌ Interest rate calculation (keep 0% APR for now)
- ❌ Liquidation mechanism (warnings only, no auto-liquidation)
- ❌ Oracle integration (assumes 1:1 valuation for MVP)
- ❌ Automatic cross-chain broadcasting (existing issue remains)
- ❌ Historical loan data and charts
- ❌ Email notifications for health warnings

**Rationale**: Focus on core functionality. These can be Sprint 08 or later.

---

## Risk Management

### Risk: Smart Contract Bugs
**Mitigation**: Contracts already deployed and tested. UI just calls existing functions.

### Risk: Transaction Failures
**Mitigation**: Comprehensive error handling, show clear error messages.

### Risk: Health Factor Edge Cases
**Mitigation**: Test with various collateral/borrow ratios, handle division by zero.

### Risk: Cross-Chain Sync Issues
**Mitigation**: Manual sync still works. Automatic broadcasting is a known issue for later.

---

## Dependencies

**Required** (already done):
- ✅ CrossChainVault contracts deployed (Sprint 05)
- ✅ VaultDashboard component exists (Sprint 05)
- ✅ useVault hooks foundation (Sprint 05)
- ✅ Wallet connection working (Sprint 05)

**Blockers**: None - all dependencies complete

---

## Documentation Updates

**Files to Update**:
- [ ] `CROSSCHAIN_VAULT_SPEC.md` - Mark borrowing/repay UI as complete
- [ ] `IMPLEMENTATION_ROADMAP.md` - Update Phase 1 status
- [ ] `docs/sprints/sprint-07.md` - This file (update progress)
- [ ] `frontend/risk-dashboard/README.md` - Add borrowing/lending usage guide

---

## Metrics

**Sprint Velocity Target**:
- **Story Points**: 26 hours estimated work
- **Features Delivered**: 4 (borrow hooks, repay hooks, health factor, UI updates)
- **Test Cases**: 6 scenarios
- **Documentation**: 4 files updated

**Quality Metrics**:
- **Code Coverage**: Aim for 80%+ on new hooks
- **Bug Count**: < 3 critical bugs
- **UI Performance**: < 3s page load
- **Transaction Success Rate**: > 95%

---

## Retrospective Questions (for end of sprint)

1. Did we accurately estimate the time required?
2. Were there unexpected challenges with the vault hooks?
3. Is the health factor calculation correct and intuitive?
4. Does the UI clearly communicate borrowing capacity?
5. Are there edge cases we didn't test?

---

## Links & References

- **Smart Contract**: `contracts/cross-chain/src/CrossChainVault.sol`
- **Contract Functions**:
  - `borrow(uint256 amount)` - Line 108
  - `repay(uint256 amount)` - Line 123
  - `borrowBalances(address, string)` - Line 24
  - `totalBorrowed(address)` - Line 29
  - `totalCreditLine(address)` - Line 32
- **Frontend Component**: `frontend/risk-dashboard/src/pages/cross-chain/VaultDashboard.tsx`
- **Hooks**: `frontend/risk-dashboard/src/hooks/contracts/useVault.ts`
- **Spec Document**: `/home/koita/dev/web3/fusion-prime/CROSSCHAIN_VAULT_SPEC.md`
- **Roadmap**: `/home/koita/dev/web3/fusion-prime/IMPLEMENTATION_ROADMAP.md`

---

**Document Version**: 1.0
**Status**: 🟢 In Progress (Week 1, Day 1)
**Next Review**: November 10, 2025 (end of Week 1)
