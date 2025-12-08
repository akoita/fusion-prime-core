# Escrow Testing Guide

Complete guide for testing the escrow functionality on Sepolia testnet.

## Prerequisites

Before testing, ensure you have:
1. **3 Sepolia testnet wallets** with ETH:
   - Wallet A (Payer) - Creates and funds the escrow
   - Wallet B (Payee) - Receives funds after approval
   - Wallet C (Arbiter) - Mediates disputes and can release/refund
2. **Sepolia testnet ETH** - Get from [Sepolia Faucet](https://sepoliafaucet.com/)
3. **Browser with MetaMask** configured for Sepolia testnet

## ⚠️ Important: Escrow Discovery Limitation

**The escrow list ONLY shows escrows where you are the PAYER (creator).**

- **Wallet A** (Payer) → Will see escrows in "My Escrows" ✅
- **Wallet B** (Payee) → Will see EMPTY list (not a bug!) ❌
- **Wallet C** (Arbiter) → Will see EMPTY list (not a bug!) ❌

**How Payees/Arbiters Access Escrows:**
1. **Save the escrow address** when it's shared with you
2. **Navigate directly** to `/escrow/{escrowAddress}`
3. **Bookmark** the escrow detail page
4. Use block explorer to find transactions to your address

This is a smart contract design limitation. The `getUserEscrows()` function only tracks the payer/creator.

## Test Scenarios

### Scenario 1: Happy Path - Complete Escrow Flow

**Objective**: Test the full escrow lifecycle from creation to successful fund release.

#### Step 1: Create Escrow (as Payer - Wallet A)

1. Connect Wallet A to the application
2. Navigate to `/escrow/create`
3. Fill in the form:
   - **Payee Address**: Wallet B address
   - **Amount**: `0.001` ETH (or any test amount)
   - **Arbiter Address**: Wallet C address
   - **Timelock Duration**: Select "1 Hour" for quick testing
   - **Description**: "Test escrow for goods delivery"
4. Click "Create Escrow"
5. **Approve the transaction** in MetaMask
6. Wait for transaction confirmation
7. **Expected Result**: Success screen with transaction hash
8. Click "View My Escrows"
9. **Verify**: New escrow appears with status "Created" (blue)
10. **IMPORTANT**: Copy the escrow address (0x...) - you'll need this for testing with other wallets!

**Verification Checklist**:
- [ ] Escrow card shows correct payee, arbiter addresses (truncated)
- [ ] Amount displays correctly
- [ ] Status shows "Created"
- [ ] Contract address is clickable to Etherscan
- [ ] Transaction hash visible on Etherscan

#### Step 2: Approve Escrow (as Payee - Wallet B)

1. **Switch to Wallet B** in MetaMask
2. **Navigate directly** to `/escrow/{escrowAddress}` (paste the address you copied)
   - Note: `/escrow/manage` will be EMPTY for Wallet B since they didn't create any escrows
3. **Verify**: You see "YOU" badge next to Payee section (green)
4. Under "Available Actions", you should see:
   - "Step 1: Approve Receipt" section highlighted in green
5. Click "Approve Escrow"
6. **Approve the transaction** in MetaMask
7. Wait for confirmation
8. **Expected Result**: Success screen "Transaction Successful! Escrow has been approved."
9. Click "Refresh Page"
10. **Verify**:
    - Status changed to "Approved" (green)
    - Approval Status shows "✓ Approved"
    - New action available based on timelock

**Verification Checklist**:
- [ ] Payee can approve successfully
- [ ] Status updates to "Approved"
- [ ] UI updates after approval
- [ ] Transaction confirmed on Etherscan

#### Step 3A: Release by Arbiter (as Arbiter - Wallet C)

**Option A: Arbiter releases immediately (recommended for testing)**

1. **Switch to Wallet C** in MetaMask
2. **Navigate directly** to `/escrow/{escrowAddress}` (paste the escrow address)
   - Note: `/escrow/manage` will be EMPTY for Wallet C since they didn't create any escrows
3. **Verify**: You see "YOU" badge next to Arbiter section (purple)
4. Under "Available Actions", you should see:
   - "Arbiter Action: Release Funds" section in purple
5. Click "Release to Payee"
6. **Approve the transaction** in MetaMask
7. Wait for confirmation
8. **Expected Result**: Success screen "Funds have been released to the payee"
9. **Verify on Etherscan**: Payee (Wallet B) received the funds

**Verification Checklist**:
- [ ] Arbiter can release funds after approval
- [ ] Transaction succeeds
- [ ] Funds transferred to payee
- [ ] Status updates to "Released"

#### Step 3B: Release by Payee after Timelock (Alternative)

**Option B: Wait for timelock to expire, payee claims**

1. **Wait for timelock to expire** (1 hour if you selected that duration)
   - Or change timelock to 3600 seconds (1 hour) when creating
2. **Switch to Wallet B** (Payee)
3. Navigate to escrow details
4. **Verify**:
   - Timelock Status shows "✅ Timelock Expired"
   - "Step 2: Claim Your Funds" action is available
5. Click "Claim Funds"
6. **Approve the transaction** in MetaMask
7. **Expected Result**: Funds released to payee

**Verification Checklist**:
- [ ] Timelock expiration detected correctly
- [ ] Payee can claim after timelock
- [ ] Funds transferred successfully

---

### Scenario 2: Dispute - Refund Flow

**Objective**: Test the refund mechanism when there's a dispute.

#### Setup: Create and Approve Escrow

1. Follow **Steps 1 & 2** from Scenario 1 to create and approve an escrow
2. **Do NOT release the funds yet**

#### Step 1: Refund by Arbiter (as Arbiter - Wallet C)

1. **Switch to Wallet C** (Arbiter)
2. Navigate to escrow details
3. Scroll to "Emergency: Refund to Payer" section (gray)
4. Click "Refund to Payer"
5. **Approve the transaction** in MetaMask
6. Wait for confirmation
7. **Expected Result**: Success screen "Funds have been refunded to the payer"
8. **Verify on Etherscan**: Payer (Wallet A) received the refund

**Verification Checklist**:
- [ ] Arbiter can refund
- [ ] Funds returned to payer
- [ ] Status updates to "Refunded"
- [ ] Transaction confirmed

---

### Scenario 3: Edge Cases & Error Handling

#### Test 3.1: Create Escrow with Invalid Data

1. Connect Wallet A
2. Navigate to `/escrow/create`
3. **Test Case 1**: Leave Payee address empty
   - **Expected**: Red error "Payee address is required"
4. **Test Case 2**: Enter invalid address (e.g., "0x123")
   - **Expected**: Red error "Invalid Ethereum address"
5. **Test Case 3**: Set Amount to 0
   - **Expected**: Red error "Amount must be greater than 0"
6. **Test Case 4**: Set Payee = your own address
   - **Expected**: Red error "Payee cannot be yourself (the payer)"
7. **Test Case 5**: Set Arbiter = Payee address
   - **Expected**: Red error "Arbiter cannot be the same as payee"

**Verification Checklist**:
- [ ] All validation errors show correctly
- [ ] Form cannot be submitted with invalid data
- [ ] Errors clear when field is corrected

#### Test 3.2: Insufficient Balance

1. Create escrow with amount > wallet balance
2. **Expected**: MetaMask shows "Insufficient funds" error

#### Test 3.3: Observer Mode

1. Connect **Wallet D** (not payer, payee, or arbiter)
2. Navigate to any escrow details page
3. **Expected**: "Observer Mode" message
4. **Verify**: No action buttons available

**Verification Checklist**:
- [ ] Observer sees read-only view
- [ ] No action buttons displayed
- [ ] "Observer Mode" message shown

#### Test 3.4: Transaction Rejection

1. Start any action (approve, release, refund)
2. **Reject the transaction** in MetaMask
3. **Expected**: Transaction fails gracefully
4. **Verify**: User can retry the action

---

### Scenario 4: Multiple Escrows

**Objective**: Test managing multiple concurrent escrows.

#### Setup: Create Multiple Escrows

1. Create 3 different escrows with different amounts:
   - Escrow 1: 0.001 ETH, 1 Hour timelock
   - Escrow 2: 0.002 ETH, 1 Day timelock
   - Escrow 3: 0.005 ETH, 3 Days timelock

#### Verification

1. Navigate to `/escrow/manage`
2. **Verify**: All 3 escrows appear in the list
3. **Check**: Each shows correct amount, status
4. **Statistics**: "Your Escrows" count shows 3
5. Test filtering/sorting (if implemented)

**Verification Checklist**:
- [ ] All escrows displayed
- [ ] Correct data for each
- [ ] Can view details of each
- [ ] Total count accurate

---

## Contract States & Transitions

### Escrow Status Flow

```
Created (0) → Approved (1) → Released (2)
                    ↓
                Refunded (3)
```

### Valid State Transitions

1. **Created → Approved**: Payee calls `approve()`
2. **Approved → Released**:
   - Arbiter calls `release()` (anytime after approval)
   - Payee calls `release()` (only after timelock expires)
3. **Created/Approved → Refunded**:
   - Arbiter calls `refund()` (anytime)
   - Payer calls `refund()` (only after extended delay)

---

## Smart Contract Functions Testing

### Read Functions (Verify Data)

Open browser console on any escrow details page to see debug logs:

```javascript
// Example console output:
Escrow 0x123... details: {
  payer: "0xABC...",
  payee: "0xDEF...",
  arbiter: "0xGHI...",
  amount: "1000000000000000", // 0.001 ETH in wei
  timelock: "1699999999",
  isApproved: true,
  status: 1, // 0=Created, 1=Approved, 2=Released, 3=Refunded
  isLoading: false,
  isError: false
}
```

### Write Functions Testing Checklist

- [ ] `createEscrow()` - ✅ Creates escrow and emits event
- [ ] `approve()` - ✅ Payee approves successfully
- [ ] `release()` by Arbiter - ✅ Releases to payee
- [ ] `release()` by Payee - ✅ Works after timelock
- [ ] `refund()` by Arbiter - ✅ Refunds to payer
- [ ] `refund()` by Payer - ⚠️ Only after extended timelock

---

## Common Issues & Troubleshooting

### Issue: "Empty Escrow Contract" Warning

**Symptoms**: Escrow card shows "⚠️ This escrow contract has no data"

**Possible Causes**:
1. Contract deployment failed
2. Transaction reverted during creation
3. Wrong network selected

**Solution**:
- Check transaction on Etherscan
- Verify contract has code deployed
- Ensure on Sepolia testnet

### Issue: Can't Approve Escrow

**Symptoms**: Approve button not appearing for payee

**Possible Causes**:
1. Wrong wallet connected (not the payee)
2. Already approved
3. Contract in wrong state

**Solution**:
- Verify you're using Wallet B (payee address)
- Check escrow status - if "Approved", it's already done
- Refresh the page

### Issue: Can't Release Funds

**Symptoms**: Release button disabled or not appearing

**Possible Causes**:
1. Not approved yet
2. Timelock not expired (for payee)
3. Wrong wallet (not arbiter or payee)

**Solution**:
- Ensure escrow is approved
- Check timelock status
- Use correct wallet (Arbiter or Payee)

### Issue: Transaction Pending Forever

**Symptoms**: Transaction stuck in MetaMask

**Solution**:
- Check gas price - may be too low
- Speed up transaction in MetaMask
- Or cancel and retry with higher gas

---

## Performance Testing

### Load Testing

1. Create 10+ escrows rapidly
2. **Verify**: All display correctly in list
3. **Check**: Page load time acceptable
4. **Monitor**: No memory leaks in browser

### Network Reliability

1. Test with slow network (throttle in DevTools)
2. **Verify**: Loading states show correctly
3. **Check**: Errors handled gracefully

---

## Security Testing

### Access Control

1. **Test**: Non-payee cannot approve
   - **Expected**: Transaction reverts
2. **Test**: Non-arbiter cannot release early
   - **Expected**: Transaction reverts
3. **Test**: Observer cannot perform actions
   - **Expected**: No action buttons shown

### Amount Validation

1. **Test**: Create with 0 amount
   - **Expected**: Frontend validation blocks
2. **Test**: Try to release multiple times
   - **Expected**: Contract rejects (already released)

---

## Test Data Tracking

Use this table to track your test results:

| Test Scenario | Wallet | Action | Expected Result | Actual Result | Pass/Fail |
|--------------|--------|---------|----------------|---------------|-----------|
| Create Escrow | A (Payer) | Create | Escrow created | | |
| Approve | B (Payee) | Approve | Status=Approved | | |
| Release (Arbiter) | C (Arbiter) | Release | Funds to payee | | |
| Release (Payee) | B (Payee) | Release | Funds claimed | | |
| Refund | C (Arbiter) | Refund | Funds to payer | | |
| Observer | D (Observer) | View | Read-only | | |
| Invalid Address | A | Create | Error shown | | |
| Empty Amount | A | Create | Error shown | | |

---

## Automated Testing Script

For quick testing, you can use this sequence:

```bash
# Quick Test Sequence (for testnet)

1. Connect Wallet A
2. Go to /escrow/create
3. Payee: <Wallet B>, Amount: 0.001, Arbiter: <Wallet C>, Timelock: 1 Hour
4. Create → Approve in MetaMask → Wait for confirmation
5. Switch to Wallet B
6. Go to /escrow/manage → Click escrow → Click "Approve Escrow"
7. Switch to Wallet C
8. Refresh escrow page → Click "Release to Payee"
9. Verify: Wallet B received 0.001 ETH
10. ✅ Test Complete
```

---

## Test Coverage Goals

- [ ] All escrow states tested (Created, Approved, Released, Refunded)
- [ ] All user roles tested (Payer, Payee, Arbiter, Observer)
- [ ] All happy paths working
- [ ] All error cases handled
- [ ] Edge cases covered
- [ ] Security controls verified
- [ ] Performance acceptable
- [ ] UI/UX polished

---

## Next Steps After Testing

1. **Document any bugs** found during testing
2. **Create GitHub issues** for improvements
3. **Consider adding**:
   - Multi-sig escrows (require multiple approvals)
   - ERC20 token support (not just ETH)
   - Partial releases
   - Escrow templates
   - Notification system
4. **Backend integration**: Index escrows for faster loading
5. **Analytics**: Track escrow metrics

---

## Testing Environment

- **Network**: Sepolia Testnet
- **Chain ID**: 11155111
- **EscrowFactory**: `0x311E63dfcEfe7f2c202715ef0DF01CDA82f58914`
- **Block Explorer**: https://sepolia.etherscan.io/
- **RPC**: Check `.env.local` for current RPC URL

---

## Additional Resources

- [Sepolia Faucet](https://sepoliafaucet.com/)
- [MetaMask Setup Guide](https://metamask.io/faqs/)
- [Etherscan Sepolia](https://sepolia.etherscan.io/)
- [Contract Source Code](../contracts/escrow/)

---

**Happy Testing! 🎉**

Report any issues or questions to the development team.
