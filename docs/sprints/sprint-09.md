# Sprint 09: Risk Management & Safety Features

**Duration**: 2 weeks (November 27 - December 10, 2025)
**Status**: 📋 **PLANNED**
**Goal**: Add risk controls to prevent undercollateralized positions and protect users

**Last Updated**: 2025-11-06

---

## Context

**Current State**: Users can borrow up to their full collateral amount with no safety margins or warnings.

**Risk**: If collateral value drops or user borrows too much, position becomes unhealthy but system doesn't prevent it.

**Sprint Objective**: Add risk management features to protect users and the protocol.

---

## Strategic Value

Risk management is critical for:
- **User Protection**: Prevent users from creating risky positions
- **Protocol Safety**: Ensure system remains solvent
- **Institutional Trust**: Professional risk controls required for institutional adoption
- **Regulatory Compliance**: Demonstrate responsible lending practices

---

## Objectives

### 1. Collateralization Ratio Enforcement ✅
**Goal**: Require minimum collateral-to-debt ratio

**Current Problem**: User can borrow 100% of collateral value
- Deposit: 1 ETH
- Can borrow: 1 ETH (100% utilization)
- **Risk**: No buffer for price fluctuations or interest

**Solution**: Enforce minimum collateralization ratio

**Smart Contract Update** (contracts/cross-chain/src/CrossChainVault.sol):
```solidity
// Add state variable
uint256 public constant MIN_COLLATERALIZATION_RATIO = 120; // 120% = 1.2x

// Update borrow function
function borrow(uint256 amount, uint256 gasAmount) external payable {
    // Current check
    require(totalCollateral[msg.sender] >= totalBorrowed[msg.sender] + amount,
            "Insufficient collateral");

    // NEW: Check collateralization ratio
    uint256 newBorrowed = totalBorrowed[msg.sender] + amount;
    uint256 requiredCollateral = (newBorrowed * MIN_COLLATERALIZATION_RATIO) / 100;
    require(totalCollateral[msg.sender] >= requiredCollateral,
            "Below minimum collateralization ratio");

    // Rest of borrow logic...
}

// Add view function to check health
function getCollateralizationRatio(address user) public view returns (uint256) {
    if (totalBorrowed[user] == 0) return type(uint256).max;
    return (totalCollateral[user] * 100) / totalBorrowed[user];
}
```

**Frontend Display** (VaultDashboard.tsx):
```typescript
const collateralRatio = vaultData.totalBorrowed > 0n
  ? (Number(vaultData.totalCollateral) * 100) / Number(vaultData.totalBorrowed)
  : Infinity;

const minRatio = 120; // 120%

// Show in borrow form
<div className="bg-yellow-50 border border-yellow-200 rounded p-3 mb-4">
  <p className="text-sm text-yellow-800">
    <strong>Minimum collateral ratio: {minRatio}%</strong>
    <br />
    You must maintain at least {minRatio}% collateral vs borrowed.
  </p>
</div>
```

**Estimated Time**: 6 hours

---

### 2. Interest Rate Calculation (Optional - DECISION REQUIRED)
**Goal**: Decide if loans should accrue interest

**Option A: 0% Interest (Recommended for MVP)**
- Simpler to implement
- Focus on cross-chain mechanics
- Add interest in later version

**Option B: Simple Fixed Rate**
- e.g., 5% APR
- Interest accrues per block
- Update totalBorrowed periodically

**Implementation (if Option B chosen)**:
```solidity
// State variables
uint256 public constant ANNUAL_INTEREST_RATE = 5; // 5% APR
mapping(address => uint256) public lastInterestUpdate;

// Update on every borrow/repay
function _accrueInterest(address user) internal {
    if (totalBorrowed[user] == 0) return;

    uint256 timeElapsed = block.timestamp - lastInterestUpdate[user];
    uint256 interest = (totalBorrowed[user] * ANNUAL_INTEREST_RATE * timeElapsed)
                        / (100 * 365 days);

    totalBorrowed[user] += interest;
    lastInterestUpdate[user] = block.timestamp;

    emit InterestAccrued(user, interest, totalBorrowed[user]);
}

function borrow(uint256 amount, uint256 gasAmount) external payable {
    _accrueInterest(msg.sender); // Accrue before borrowing
    // ... rest of logic
}
```

**Recommendation**: **Start with Option A (0% interest)**, add in Sprint 12+ if needed

**Estimated Time**: 0 hours (deferred) OR 8 hours (if implementing)

---

### 3. Liquidation Warnings
**Goal**: Alert users when position becomes risky

**Warning Thresholds**:
- **Green**: Ratio > 150% (healthy)
- **Yellow**: Ratio 110-150% (caution)
- **Red**: Ratio < 110% (danger)

**UI Component** (VaultDashboard.tsx):
```typescript
function HealthWarningBanner({ collateralRatio }: { collateralRatio: number }) {
  if (collateralRatio === Infinity || collateralRatio > 150) {
    return null; // Healthy, no warning
  }

  const isRed = collateralRatio < 110;
  const isYellow = collateralRatio >= 110 && collateralRatio <= 150;

  return (
    <div className={`rounded-lg p-4 mb-6 ${
      isRed ? 'bg-red-50 border-2 border-red-300' : 'bg-yellow-50 border-2 border-yellow-300'
    }`}>
      <div className="flex items-start gap-3">
        <AlertTriangle className={`h-6 w-6 ${isRed ? 'text-red-600' : 'text-yellow-600'}`} />
        <div>
          <h3 className={`font-bold ${isRed ? 'text-red-900' : 'text-yellow-900'}`}>
            {isRed ? '⚠️ CRITICAL: Position at Risk' : '⚠️ Warning: Low Collateral Ratio'}
          </h3>
          <p className={`text-sm mt-1 ${isRed ? 'text-red-800' : 'text-yellow-800'}`}>
            Your collateral ratio is {collateralRatio.toFixed(1)}%.
            {isRed
              ? ' Immediate action required to avoid liquidation.'
              : ' Consider adding more collateral or repaying some debt.'
            }
          </p>
          <div className="mt-3 flex gap-2">
            <button className="px-4 py-2 bg-white border border-gray-300 rounded text-sm font-medium">
              Add Collateral
            </button>
            <button className="px-4 py-2 bg-white border border-gray-300 rounded text-sm font-medium">
              Repay Debt
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Usage in VaultDashboard
<HealthWarningBanner collateralRatio={collateralRatio} />
```

**Estimated Time**: 4 hours

---

### 4. Enhanced Health Factor Visualization
**Goal**: Make risk status immediately obvious

**Circular Gauge Component**:
```typescript
function HealthFactorGauge({ ratio }: { ratio: number }) {
  const percentage = Math.min(100, ((ratio - 100) / 50) * 100); // 100%=0%, 150%=100%
  const color = ratio > 150 ? 'green' : ratio > 110 ? 'yellow' : 'red';

  return (
    <div className="relative w-32 h-32">
      <svg viewBox="0 0 100 100" className="transform -rotate-90">
        {/* Background circle */}
        <circle
          cx="50"
          cy="50"
          r="45"
          fill="none"
          stroke="#e5e7eb"
          strokeWidth="10"
        />
        {/* Progress circle */}
        <circle
          cx="50"
          cy="50"
          r="45"
          fill="none"
          stroke={color === 'green' ? '#10b981' : color === 'yellow' ? '#f59e0b' : '#ef4444'}
          strokeWidth="10"
          strokeDasharray={`${percentage * 2.827} 282.7`}
          className="transition-all duration-500"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center flex-col">
        <span className="text-2xl font-bold">{ratio === Infinity ? '∞' : ratio.toFixed(0)}%</span>
        <span className="text-xs text-gray-600">Health</span>
      </div>
    </div>
  );
}
```

**Add to Stats Section**:
```typescript
<div className="bg-white border-2 border-gray-200 rounded-lg p-6">
  <div className="flex items-center justify-between mb-4">
    <span className="text-sm font-medium text-gray-600">Position Health</span>
    <Activity className="h-5 w-5 text-blue-600" />
  </div>
  <div className="flex justify-center">
    <HealthFactorGauge ratio={collateralRatio} />
  </div>
  <div className="mt-4 text-center">
    <p className="text-sm text-gray-600">
      Collateralization: {collateralRatio === Infinity ? '∞' : `${collateralRatio.toFixed(1)}%`}
    </p>
  </div>
</div>
```

**Estimated Time**: 6 hours

---

### 5. Position Dashboard & Analytics
**Goal**: Unified view of risk across all chains

**New Component**: `RiskDashboard.tsx`
```typescript
export function RiskDashboard({ userAddress }: { userAddress: Address }) {
  const vaultData = useVaultData(userAddress);

  return (
    <div className="space-y-6">
      {/* Overall Health Summary */}
      <div className="bg-white rounded-lg border p-6">
        <h2 className="text-xl font-bold mb-4">Position Overview</h2>
        <div className="grid grid-cols-3 gap-4">
          <MetricCard
            label="Total Collateral"
            value={formatEther(vaultData.totalCollateral)}
            unit="ETH"
            color="green"
          />
          <MetricCard
            label="Total Borrowed"
            value={formatEther(vaultData.totalBorrowed)}
            unit="ETH"
            color="red"
          />
          <MetricCard
            label="Available to Borrow"
            value={formatEther(vaultData.creditLine)}
            unit="ETH"
            color="blue"
          />
        </div>
      </div>

      {/* Per-Chain Breakdown */}
      <div className="bg-white rounded-lg border p-6">
        <h2 className="text-xl font-bold mb-4">Chain Breakdown</h2>
        <table className="w-full">
          <thead>
            <tr className="border-b">
              <th className="text-left py-2">Chain</th>
              <th className="text-right py-2">Collateral</th>
              <th className="text-right py-2">Borrowed</th>
              <th className="text-right py-2">Utilization</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b">
              <td className="py-3">Ethereum Sepolia</td>
              <td className="text-right">{formatEther(vaultData.sepoliaBalance)} ETH</td>
              <td className="text-right">{formatEther(vaultData.sepoliaBorrowed)} ETH</td>
              <td className="text-right">
                {calculateUtilization(vaultData.sepoliaBalance, vaultData.sepoliaBorrowed)}%
              </td>
            </tr>
            <tr>
              <td className="py-3">Polygon Amoy</td>
              <td className="text-right">{formatEther(vaultData.amoyBalance)} MATIC</td>
              <td className="text-right">{formatEther(vaultData.amoyBorrowed)} MATIC</td>
              <td className="text-right">
                {calculateUtilization(vaultData.amoyBalance, vaultData.amoyBorrowed)}%
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Historical Health Factor (optional - Phase 5) */}
      <div className="bg-white rounded-lg border p-6">
        <h2 className="text-xl font-bold mb-4">Health Factor History</h2>
        <p className="text-gray-500">Coming in Sprint 11 (Polish & Optimization)</p>
      </div>
    </div>
  );
}
```

**Estimated Time**: 8 hours

---

## Week-by-Week Plan

### Week 1 (Nov 27 - Dec 3): Contract & Core Features

**Days 1-2 (Nov 27-28)**:
- [ ] Add collateralization ratio constant to contract
- [ ] Update borrow() function with ratio check
- [ ] Add getCollateralizationRatio() view function
- [ ] Decide on interest rates (0% OR 5% APR)
- [ ] If 5%, implement interest accrual logic
- [ ] Write contract tests for new logic
- [ ] Deploy to Sepolia
- [ ] Deploy to Amoy

**Days 3-4 (Nov 29-30)**:
- [ ] Update frontend hooks to show collateral ratio
- [ ] Add health warning banner component
- [ ] Display minimum ratio requirement in borrow form
- [ ] Test borrow attempts with insufficient collateral
- [ ] Verify error messages are clear

**Day 5 (Dec 1)**:
- [ ] Create HealthFactorGauge component
- [ ] Add to VaultDashboard stats section
- [ ] Test with various collateral ratios
- [ ] Polish animations and styling

**Weekend (Dec 2-3)**: Buffer for issues

---

### Week 2 (Dec 4-10): Dashboard & Testing

**Days 6-7 (Dec 4-5)**:
- [ ] Create RiskDashboard component
- [ ] Add overall health summary
- [ ] Add per-chain breakdown table
- [ ] Test with real vault data
- [ ] Navigation from VaultDashboard to RiskDashboard

**Days 8-9 (Dec 6-7)**:
- [ ] Comprehensive testing of all features
- [ ] Test edge cases (exactly at min ratio, slightly below)
- [ ] Test warnings show/hide correctly
- [ ] Test circular gauge at different ratios
- [ ] Fix any bugs discovered

**Days 10-12 (Dec 8-10)**:
- [ ] Documentation updates
- [ ] Create user guide for risk management
- [ ] Update CROSSCHAIN_VAULT_SPEC.md
- [ ] Record demo video
- [ ] Prepare for Sprint 10

---

## Testing Scenarios

**Test 1: Minimum Ratio Enforcement**
- [ ] Deposit 1 ETH collateral
- [ ] Try to borrow 0.85 ETH (85% ratio)
- [ ] Verify transaction reverts
- [ ] Error message: "Below minimum collateralization ratio"

**Test 2: Warning Banner Display**
- [ ] Set up position with 140% ratio
- [ ] Verify yellow warning shows
- [ ] Borrow more to reach 105% ratio
- [ ] Verify red warning shows

**Test 3: Health Gauge Accuracy**
- [ ] Create positions at 200%, 150%, 120%, 110%, 100% ratios
- [ ] Verify gauge shows correct colors and percentages
- [ ] Verify smooth transitions

**Test 4: Per-Chain Breakdown**
- [ ] Have collateral on both chains
- [ ] Borrow on different chains
- [ ] Verify RiskDashboard shows accurate breakdown
- [ ] Check utilization calculations

**Test 5: Add Collateral to Improve Health**
- [ ] Start with 110% ratio (yellow warning)
- [ ] Deposit more collateral
- [ ] Verify ratio improves
- [ ] Verify warning disappears when > 150%

**Test 6: Repay to Improve Health**
- [ ] Start with 115% ratio (yellow warning)
- [ ] Repay partial debt
- [ ] Verify ratio improves
- [ ] Verify warning changes or disappears

---

## Success Criteria

| Criteria | Target |
|----------|--------|
| Collateralization ratio enforced | 120% minimum |
| Health warnings visible | When ratio < 150% |
| Gauge displays accurately | ±1% accuracy |
| Cannot borrow below min ratio | 100% prevention |
| Risk dashboard shows all chains | Both Sepolia & Amoy |
| Warning actions work | Add collateral/Repay buttons functional |

---

## Non-Goals (Deferred)

- ❌ Automatic liquidation mechanism (no auto-liquidation)
- ❌ Liquidation incentives for liquidators
- ❌ Historical health factor charts (Sprint 11)
- ❌ Email/SMS notifications (requires backend)
- ❌ Dynamic interest rates (fixed OR 0% only)
- ❌ Multi-asset collateral (ETH/MATIC treated separately)

**Rationale**: Focus on preventing risky positions. Liquidation mechanism is complex and can be added later if needed.

---

## Risk Management

### Risk: Users Frustrated by Min Ratio
**Mitigation**: Clear messaging, show available-to-borrow amount

### Risk: False Positives on Warnings
**Mitigation**: Test thresholds carefully, allow users to dismiss warnings

### Risk: Gauge Confusing to Users
**Mitigation**: Add tooltips explaining what the gauge means

---

## Dependencies

**Required**:
- ✅ Sprint 07 complete (borrowing/lending UI)
- ✅ Sprint 08 complete (auto-sync working)

**Blockers**: None

---

## Documentation Updates

- [ ] Update CROSSCHAIN_VAULT_SPEC.md (Risk Management section)
- [ ] Create user guide for managing position health
- [ ] Update IMPLEMENTATION_ROADMAP.md (Phase 3 complete)
- [ ] Add FAQ: "What is collateralization ratio?"

---

## Metrics

- **Sprint Velocity**: 40 hours estimated work
- **Features**: 5 (ratio enforcement, warnings, gauge, dashboard, testing)
- **Contract Changes**: 2 new functions, 1 constant
- **Frontend Components**: 3 new (HealthWarning, HealthGauge, RiskDashboard)

---

**Document Version**: 1.0
**Status**: 📋 Planned (starts after Sprint 08)
**Predecessor**: Sprint 08 (Auto-Sync)
**Successor**: Sprint 10 (Oracle Integration)
