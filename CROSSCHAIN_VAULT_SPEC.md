# CrossChainVault - Complete Feature Specification

## Overview
The CrossChainVault is a **cross-chain lending protocol** that enables users to:
- Deposit collateral on ANY supported chain
- Borrow against their TOTAL collateral across ALL chains
- Have all state automatically synced via bridge protocols

## Core Innovation
**Capital Efficiency Through Cross-Chain Collateral Aggregation**
- Deposit ETH on Ethereum Sepolia
- Borrow MATIC on Polygon Amoy using that same ETH as collateral
- All balances tracked and synced automatically across chains

---

## Contract Architecture

### State Variables

**Per-Chain Balances:**
```solidity
mapping(address => mapping(string => uint256)) public collateralBalances;  // user => chain => amount
mapping(address => mapping(string => uint256)) public borrowBalances;      // user => chain => amount
```

**Aggregated Totals (Cross-Chain):**
```solidity
mapping(address => uint256) public totalCollateral;  // Sum across ALL chains
mapping(address => uint256) public totalBorrowed;    // Sum across ALL chains
mapping(address => uint256) public totalCreditLine;  // Available to borrow = collateral - borrowed
```

---

## Complete Feature Set

### 1. Collateral Management

#### Deposit Collateral (`depositCollateral`)
- **What**: User deposits native tokens (ETH/MATIC) as collateral
- **Where**: On current chain
- **Updates**:
  - `collateralBalances[user][thisChain]` += amount
  - `totalCollateral[user]` += amount
  - Recalculates credit line
  - **Broadcasts to ALL other chains** to sync state
- **Gas**: User pays for cross-chain broadcast

#### Withdraw Collateral (`withdrawCollateral`)
- **What**: User withdraws their collateral back to wallet
- **Checks**:
  - Sufficient balance on this chain
  - Total collateral >= total borrowed (after withdrawal)
- **Updates**:
  - `collateralBalances[user][thisChain]` -= amount
  - `totalCollateral[user]` -= amount
  - Recalculates credit line
  - **Broadcasts to ALL other chains**
- **Transfer**: Sends native tokens back to user

### 2. Borrowing/Lending

#### Borrow (`borrow`)
- **What**: User borrows native tokens against their cross-chain collateral
- **Checks**: `totalCollateral >= totalBorrowed + amount` (across ALL chains!)
- **Updates**:
  - `borrowBalances[user][thisChain]` += amount
  - `totalBorrowed[user]` += amount
  - Recalculates credit line
  - **Broadcasts to ALL other chains**
- **Transfer**: Sends borrowed amount to user
- **Key Feature**: Can borrow on Chain A using collateral from Chain B!

#### Repay (`repay`)
- **What**: User repays their borrowed amount
- **Checks**: Has outstanding borrow balance on this chain
- **Updates**:
  - `borrowBalances[user][thisChain]` -= amount
  - `totalBorrowed[user]` -= amount
  - Recalculates credit line
  - **Broadcasts to ALL other chains**
- **Transfer**: Accepts payment from user (with refund if overpaid)

### 3. Cross-Chain State Synchronization

#### Message Types (Action Codes)
```
1 = Collateral Deposit
2 = Collateral Withdrawal
3 = Borrow
4 = Repay
```

#### Broadcast Mechanism
- **When**: After every deposit/withdraw/borrow/repay
- **What**: Sends state update to ALL other supported chains
- **How**: Via BridgeManager (Axelar, CCIP, etc.)
- **Payload**: `(messageId, user, action, amount, chainName)`

#### Message Receiving (`execute`)
- **Entry Point**: Called by Axelar Gateway
- **Security**: Only Axelar Gateway can call
- **Processing**:
  - Decodes payload
  - Replay protection (messageId check)
  - Updates local state based on action code
  - Recalculates credit line
  - Emits events

### 4. Credit Line Management

#### Credit Line Calculation
```
totalCreditLine = totalCollateral - totalBorrowed
```

#### Updated On:
- Every deposit
- Every withdrawal
- Every borrow
- Every repay
- Every received cross-chain message

#### Used For:
- Determining borrowing capacity
- Health checks before withdrawals
- Risk monitoring

---

## User Workflows

### Workflow 1: Single-Chain Deposit & Borrow
```
1. User on Sepolia deposits 1 ETH
   → collateralBalances[user][sepolia] = 1 ETH
   → totalCollateral[user] = 1 ETH
   → Broadcasts to Amoy

2. User on Sepolia borrows 0.5 ETH
   → borrowBalances[user][sepolia] = 0.5 ETH
   → totalBorrowed[user] = 0.5 ETH
   → totalCreditLine[user] = 0.5 ETH
   → Broadcasts to Amoy

3. Amoy vault receives messages
   → Updates its local view of user's total balances
   → Same totalCollateral, totalBorrowed on both chains
```

### Workflow 2: Cross-Chain Collateral Utilization
```
1. User on Sepolia deposits 1 ETH
   → totalCollateral = 1 ETH (across all chains)
   → Broadcasts to Amoy

2. User switches to Amoy network

3. User on Amoy borrows 0.5 MATIC
   → Uses ETH on Sepolia as collateral!
   → borrowBalances[user][amoy] = 0.5 MATIC
   → totalBorrowed = 0.5 MATIC equivalent
   → Broadcasts back to Sepolia

4. Both vaults now show:
   - Total Collateral: 1 ETH
   - Total Borrowed: 0.5 MATIC
   - Credit Line: Remaining capacity
```

### Workflow 3: Managing Position Across Chains
```
1. User has:
   - 1 ETH collateral on Sepolia
   - 0.5 MATIC borrowed on Amoy

2. User repays 0.2 MATIC on Amoy
   → totalBorrowed -= 0.2 MATIC
   → Credit line increases
   → Broadcasts to Sepolia

3. User withdraws 0.3 ETH on Sepolia
   → Checks: totalCollateral - 0.3 >= totalBorrowed ✓
   → Withdrawal succeeds
   → Broadcasts to Amoy

4. State synced across both chains
```

---

## Implementation Status

### ✅ Completed

**Smart Contracts:**
- [x] CrossChainVault with all core functions
- [x] Proper execute() for Axelar messages
- [x] BridgeManager V2 with correct config
- [x] Deployed on Sepolia and Amoy

**Frontend - Basic:**
- [x] Vault Dashboard (view balances)
- [x] Deposit functionality
- [x] Withdraw functionality
- [x] Cross-chain sync UI

### ❌ Missing / Incomplete

**Borrowing/Lending Features:**
- [ ] Borrow UI and flow
- [ ] Repay UI and flow
- [ ] Interest rate calculation
- [ ] Liquidation mechanism
- [ ] Health factor visualization
- [ ] Loan management dashboard

**Cross-Chain Sync Issues:**
- [ ] Automatic broadcasting not working (gas payment issue)
- [ ] Manual sync required via separate page
- [ ] No cross-chain message tracking
- [ ] No confirmation of sync completion

**Risk Management:**
- [ ] Collateralization ratio enforcement
- [ ] Health factor monitoring
- [ ] Liquidation triggers
- [ ] Oracle integration for price feeds

**UI/UX:**
- [ ] Unified cross-chain position view
- [ ] Borrowing capacity calculator
- [ ] Interest accrual display
- [ ] Transaction history per user

---

## Proposed Implementation Roadmap

### Phase 1: Fix Core Sync Mechanism (High Priority)
**Problem**: Deposit/withdraw broadcasts don't work automatically

**Tasks:**
1. Fix gas payment for broadcasts in vault functions
2. Test automatic cross-chain sync on deposit
3. Verify state updates on all chains
4. Add message tracking/confirmation

**Deliverable**: Deposits on Chain A automatically update balance on Chain B

### Phase 2: Implement Borrowing (Core Feature)
**Goal**: Enable cross-chain borrowing

**Tasks:**
1. Add borrow hooks to useVault.ts
2. Create Borrow UI with capacity calculator
3. Add repay hooks and UI
4. Show borrowed amounts on dashboard
5. Display credit line utilization

**Deliverable**: Users can borrow on any chain against cross-chain collateral

### Phase 3: Risk Management (Safety)
**Goal**: Prevent undercollateralized positions

**Tasks:**
1. Add health factor calculation
2. Implement collateralization ratio checks
3. Add warning indicators in UI
4. (Optional) Liquidation mechanism

**Deliverable**: System prevents risky borrows, shows health status

### Phase 4: Polish & Optimization
**Goal**: Production-ready experience

**Tasks:**
1. Unified position dashboard (all chains)
2. Transaction history and tracking
3. Gas optimization for broadcasts
4. Error handling and edge cases
5. User documentation

---

## Key Questions to Answer

### 1. Automatic vs Manual Sync?
**Current**: Manual sync via separate page
**Intended**: Automatic on every deposit/withdraw/borrow/repay

**Question**: Should we fix automatic sync, or keep manual for gas control?

### 2. Interest Rates?
**Current**: No interest calculation
**Question**: Should borrowed amounts accrue interest? What rate?

### 3. Price Oracles?
**Current**: Assumes 1:1 value across chains
**Question**: Do we need Chainlink oracles to value ETH vs MATIC?

### 4. Liquidation?
**Current**: No liquidation mechanism
**Question**: What happens if collateral < borrowed? Manual intervention?

### 5. Gas Economics?
**Current**: User pays gas for every broadcast
**Problem**: Expensive to sync to ALL chains on every action

**Options:**
A. User pays (current)
B. Vault subsidizes (needs funding)
C. Lazy sync (only when needed)
D. Batch updates

---

## Recommended Next Steps

1. **Decide on Scope**: Full lending protocol or simplified tracking?

2. **If Full Protocol**:
   - Phase 1: Fix automatic sync
   - Phase 2: Add borrowing
   - Phase 3: Add risk management

3. **If Simplified**:
   - Remove borrow/repay from UI
   - Focus on cross-chain balance tracking
   - Keep contracts as-is (they work for this too)

4. **Create Detailed Specs** for chosen path

What would you like to focus on?
