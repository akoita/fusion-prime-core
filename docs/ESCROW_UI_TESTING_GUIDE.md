# Escrow UI Testing Guide

**Date**: November 4, 2025

---

## ✅ **Pre-Test Checklist**

### Services Running
- [x] Frontend: http://localhost:5174 ✅
- [x] Identity Service: http://localhost:8002 ✅
- [x] PostgreSQL: Running ✅

### Browser Setup
- [ ] MetaMask installed
- [ ] MetaMask connected to Sepolia testnet
- [ ] Test wallet has Sepolia ETH (get from faucet if needed)

### Test Account
```
Email: testuser@example.com
Password: SecurePass123
```

---

## 🧪 **Test Scenarios**

### **Test 1: Login Flow**

**Steps:**
1. Open http://localhost:5174
2. You should see the login page
3. Enter credentials:
   - Email: `testuser@example.com`
   - Password: `SecurePass123`
4. Click "Login"

**Expected Result:**
- ✅ Login successful
- ✅ Redirected to Portfolio Overview
- ✅ User info displayed in header

**Status:** [ ]

---

### **Test 2: Wallet Connection**

**Steps:**
1. Click "Connect Wallet" button in header
2. Select MetaMask from RainbowKit modal
3. Approve connection in MetaMask
4. Ensure network is Sepolia

**Expected Result:**
- ✅ Wallet connected
- ✅ Address displayed in header (e.g., "0x1234...5678")
- ✅ Network shows Sepolia
- ✅ Can see balance

**Status:** [ ]

**Troubleshooting:**
- If not on Sepolia, MetaMask will prompt to switch networks
- If no Sepolia ETH, get from faucet: https://sepoliafaucet.com

---

### **Test 3: Navigate to Escrows**

**Steps:**
1. Look at sidebar navigation
2. You should see:
   - "My Escrows" 🔒
   - "Create Escrow" ➕
3. Click "My Escrows"

**Expected Result:**
- ✅ Navigated to `/escrow/manage`
- ✅ See stats: Total Escrows, Your Escrows, Network
- ✅ See empty state or existing escrows

**Status:** [ ]

---

### **Test 4: Create Escrow - Form Validation**

**Steps:**
1. Click "Create Escrow" in sidebar
2. Try to submit empty form

**Expected Result:**
- ✅ Form validation errors shown
- ✅ Cannot submit without required fields

**Test Invalid Addresses:**
3. Enter invalid address in Payee field: `0x123`
4. Try to submit

**Expected Result:**
- ✅ Shows "Invalid Ethereum address" error

**Test Self-Payment:**
5. Enter your own wallet address as Payee
6. Try to submit

**Expected Result:**
- ✅ Shows "Payee cannot be yourself" error

**Status:** [ ]

---

### **Test 5: Create Escrow - Valid Transaction**

**Pre-requisites:**
- Have 3 different wallet addresses ready:
  1. Your wallet (Payer) - the connected wallet
  2. Payee wallet - any other address
  3. Arbiter wallet - any other address (can be the same as payee for testing)

**Steps:**
1. Fill form with valid data:
   ```
   Payee: 0x70997970C51812dc3A010C7d01b50e0d17dc79C8
   Amount: 0.01
   Arbiter: 0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC
   Timelock: 1 Day
   Description: Test escrow for development
   ```

2. Review summary (shows your address as Payer)
3. Click "Create Escrow"
4. Approve transaction in MetaMask

**Expected Result:**
- ✅ MetaMask popup appears
- ✅ Transaction details show:
  - To: EscrowFactory contract
  - Value: 0.01 ETH
  - Gas estimate
- ✅ After approval, loading state shows
- ✅ Success screen appears with transaction hash
- ✅ Can click "View My Escrows"

**Status:** [ ]

**Transaction Hash:** _________________

---

### **Test 6: View Escrow in List**

**Steps:**
1. Click "View My Escrows" or navigate to "My Escrows" in sidebar
2. Find your newly created escrow

**Expected Result:**
- ✅ Escrow card appears
- ✅ Shows status: "Created" (blue badge)
- ✅ Shows amount: 0.01 ETH
- ✅ Shows "Approved: No"
- ✅ Shows shortened addresses for Payer, Payee, Arbiter
- ✅ "View Details" button present
- ✅ Etherscan link button present

**Status:** [ ]

---

### **Test 7: Escrow Details Page**

**Steps:**
1. Click "View Details" on your escrow
2. Examine the page

**Expected Result:**
- ✅ Shows escrow address
- ✅ Status badge: "Created"
- ✅ "Your Role: Payer" displayed
- ✅ Amount: 0.01 ETH shown prominently
- ✅ Approved: "Not Yet"
- ✅ All three parties listed (Payer with "You" label)
- ✅ Timeline shows "Created" step
- ✅ Actions section shows "Refund to Payer" button (payer can refund)
- ✅ Link to Sepolia Etherscan

**Status:** [ ]

---

### **Test 8: Click Etherscan Link**

**Steps:**
1. Click "View on Sepolia Etherscan" link
2. New tab opens

**Expected Result:**
- ✅ Etherscan page loads for escrow contract
- ✅ Shows contract address
- ✅ Can see creation transaction
- ✅ Can see contract balance (0.01 ETH)

**Status:** [ ]

---

### **Test 9: Test Escrow Actions (Role-Based)**

This requires switching wallets to test different roles.

#### **As Payee (Approve)**

**Steps:**
1. Switch MetaMask to payee wallet address
2. Navigate to the escrow details page
3. Your role should show "Payee"
4. Click "Approve Escrow" button
5. Approve transaction in MetaMask

**Expected Result:**
- ✅ Transaction submitted
- ✅ Success message appears
- ✅ Page refreshes showing "Approved: Yes"
- ✅ Status changes (if implemented)

**Status:** [ ]

#### **As Arbiter (Release)**

**Steps:**
1. Switch MetaMask to arbiter wallet address
2. Navigate to escrow details
3. Your role should show "Arbiter"
4. If escrow is approved, "Release to Payee" button shows
5. Click "Release to Payee"
6. Approve transaction

**Expected Result:**
- ✅ Transaction submitted
- ✅ Success message
- ✅ Funds transferred to payee
- ✅ Status changes to "Released"

**Status:** [ ]

#### **As Arbiter (Refund)**

**Alternative to Release:**
1. As arbiter, click "Refund to Payer" instead
2. Approve transaction

**Expected Result:**
- ✅ Transaction submitted
- ✅ Funds returned to payer
- ✅ Status changes to "Refunded"

**Status:** [ ]

---

### **Test 10: Error Handling**

#### **Insufficient Funds**

**Steps:**
1. Try to create escrow with amount > wallet balance
2. Approve in MetaMask

**Expected Result:**
- ✅ MetaMask shows insufficient funds error
- ✅ Transaction fails
- ✅ Error message shown in UI

**Status:** [ ]

#### **User Rejects Transaction**

**Steps:**
1. Start creating escrow
2. Click "Create Escrow"
3. Click "Reject" in MetaMask

**Expected Result:**
- ✅ Error message: "User rejected transaction" or similar
- ✅ Form remains, can try again
- ✅ No stuck loading state

**Status:** [ ]

#### **Network Disconnection**

**Steps:**
1. Disconnect wallet
2. Try to view escrow page

**Expected Result:**
- ✅ Shows "Wallet Not Connected" message
- ✅ Prompts to connect wallet

**Status:** [ ]

---

### **Test 11: UI/UX Checks**

**Responsive Design:**
- [ ] Test on desktop (1920x1080)
- [ ] Test on tablet size (768px)
- [ ] Test on mobile size (375px)

**Loading States:**
- [ ] Spinners show while fetching data
- [ ] Loading text is clear
- [ ] No blank screens

**Navigation:**
- [ ] Back button works (Escrow Details → My Escrows)
- [ ] Sidebar highlighting works
- [ ] Breadcrumbs (if any) work

**Visual Polish:**
- [ ] Status badges have correct colors
- [ ] Buttons have hover states
- [ ] Forms have focus states
- [ ] No layout shifts

**Status:** [ ]

---

## 📊 **Test Results Summary**

| Test | Status | Notes |
|------|--------|-------|
| 1. Login Flow | [ ] | |
| 2. Wallet Connection | [ ] | |
| 3. Navigate to Escrows | [ ] | |
| 4. Form Validation | [ ] | |
| 5. Create Escrow | [ ] | TX: _____ |
| 6. View Escrow List | [ ] | |
| 7. Escrow Details | [ ] | |
| 8. Etherscan Link | [ ] | |
| 9. Escrow Actions | [ ] | |
| 10. Error Handling | [ ] | |
| 11. UI/UX Checks | [ ] | |

---

## 🐛 **Issues Found**

### Issue 1
**Description:**

**Steps to Reproduce:**

**Expected:**

**Actual:**

**Severity:** Low / Medium / High / Critical

---

### Issue 2
**Description:**

**Steps to Reproduce:**

**Expected:**

**Actual:**

**Severity:** Low / Medium / High / Critical

---

## 🎯 **Test Data Reference**

### Test Wallets (Sepolia)
```
Payer (Your Wallet):
Connected wallet address

Payee (Test Wallet 1):
0x70997970C51812dc3A010C7d01b50e0d17dc79C8

Arbiter (Test Wallet 2):
0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC
```

### Contract Addresses
```
EscrowFactory (Sepolia):
0x311E63dfcEfe7f2c202715ef0DF01CDA82f58914

View on Etherscan:
https://sepolia.etherscan.io/address/0x311E63dfcEfe7f2c202715ef0DF01CDA82f58914
```

### Faucets
```
Sepolia ETH:
- https://sepoliafaucet.com
- https://faucet.sepolia.dev
- https://www.alchemy.com/faucets/ethereum-sepolia
```

---

## ✅ **Completion Criteria**

- [ ] All 11 tests passed
- [ ] No critical bugs found
- [ ] UI is responsive
- [ ] Error handling works
- [ ] Can complete full escrow flow
- [ ] Documentation updated with findings

---

## 📝 **Notes**

**Testing Date:** __________

**Tester:** __________

**Browser:** Chrome / Firefox / Safari / Edge

**MetaMask Version:** __________

**Additional Comments:**




---

**Happy Testing!** 🧪
