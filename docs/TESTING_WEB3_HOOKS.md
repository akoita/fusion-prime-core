# Testing Web3 Contract Hooks - Step-by-Step Guide

**Dev Server**: http://localhost:5174/
**Last Updated**: November 4, 2025

---

## 🎯 What We're Testing

We're testing 30+ React hooks that interact with real smart contracts on:
- **Sepolia Testnet** (Ethereum)
- **Polygon Amoy Testnet** (Polygon)

### Deployed Contracts:
- **EscrowFactory**: `0x311E63dfcEfe7f2c202715ef0DF01CDA82f58914` (Sepolia)
- **CrossChainVault**: `0x0C95a78b0D72F882fae14CD7C842a5f000E0c4e2` (Sepolia)
- **CrossChainVault**: `0x7843C2eD8930210142DC51dbDf8419C74FD27529` (Amoy)
- **BridgeManager**: `0xC96DA7e94E8407e0988bb60A1b23B9358Cd63A56` (Sepolia)

---

## ✅ Prerequisites

### 1. MetaMask Wallet Setup

**Install MetaMask:**
- If not installed: https://metamask.io/download/
- Create a wallet or import existing one

**Add Sepolia Testnet:**
```
Network Name: Sepolia
RPC URL: https://rpc.sepolia.org
Chain ID: 11155111
Currency Symbol: ETH
Block Explorer: https://sepolia.etherscan.io
```

**Add Polygon Amoy Testnet:**
```
Network Name: Polygon Amoy
RPC URL: https://rpc-amoy.polygon.technology
Chain ID: 80002
Currency Symbol: MATIC
Block Explorer: https://amoy.polygonscan.com
```

### 2. Get Testnet Tokens (Optional - for transactions)

**Sepolia ETH:**
- https://sepoliafaucet.com/
- https://www.alchemy.com/faucets/ethereum-sepolia
- Requires 0.001 ETH on mainnet OR social media verification

**Polygon Amoy MATIC:**
- https://faucet.polygon.technology/
- Free, just connect wallet

**Note**: You DON'T need tokens just to read blockchain data!

---

## 🧪 Test 1: Basic Wallet Connection

**Goal**: Verify wallet connection works with RainbowKit

### Steps:

1. **Open the app**:
   ```
   http://localhost:5174/
   ```

2. **Login** (mock authentication):
   - Email: `test@test.com` (or anything)
   - Password: `password` (or anything)
   - Click "Login"

3. **Connect Wallet**:
   - Look for "Connect Wallet" button in the top-right header
   - Click it
   - You should see a modal with wallet options

4. **Select MetaMask**:
   - Click "MetaMask" option
   - MetaMask popup should appear
   - Click "Next" → "Connect"

5. **Verify Connection**:
   - ✅ Wallet address appears in header (shortened: `0x1234...5678`)
   - ✅ Network icon shows (⟠ for Sepolia or ⬡ for Amoy)
   - ✅ ETH/MATIC balance displays
   - ✅ Button shows chain name

**Success Indicators:**
```
Before: [Connect Wallet] button
After:  [⟠ Sepolia | 0x1234...5678 | 0.05 ETH ▼]
```

---

## 🧪 Test 2: View Web3 Demo Page

**Goal**: See all contract hooks in action

### Steps:

1. **Navigate to Web3 Demo**:
   - Click "Web3 Demo" (🔗) in the left sidebar
   - Page should load instantly

2. **Observe the page sections**:

**Section 1: Connection Info**
```
✅ Address: 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb
✅ Network: Sepolia (Chain ID: 11155111)
```

**Section 2: Escrow Factory (Sepolia)**
```
✅ Total Escrows Created: [number from blockchain]
✅ Your Escrows: [list of your escrows or "No escrows found"]
```

**Section 3: Cross-Chain Vault Data**
```
✅ Sepolia Testnet Card (Blue):
   - Total Collateral: 0 ETH (or your actual collateral)
   - Total Borrowed: 0 ETH
   - Credit Line Available: 0 ETH

✅ Polygon Amoy Card (Purple):
   - Total Collateral: 0 MATIC
   - Total Borrowed: 0 MATIC
   - Credit Line Available: 0 MATIC
```

**Section 4: Cross-Chain Bridge Info**
```
✅ Registered Bridge Protocols: [axelar] [ccip] (or similar)
✅ Supported Chains:
   - Ethereum Sepolia: ✓ Supported | Protocol: axelar
   - Polygon Amoy: ✓ Supported | Protocol: ccip
```

### What the Data Means:

**If all zeros:**
- ✅ Hooks are working!
- ✅ Reading from blockchain successfully
- ✅ You just don't have any activity yet (normal for new wallet)

**If loading forever:**
- ❌ Check MetaMask is connected
- ❌ Check you're on Sepolia or Amoy network
- ❌ Check browser console for errors (F12)

**If "No escrows found":**
- ✅ Normal! You haven't created any escrows yet
- ✅ The hook is working, just returning empty array

---

## 🧪 Test 3: Network Switching

**Goal**: Verify multi-chain hooks work correctly

### Steps:

1. **Check current network**:
   - Look at wallet button in header
   - Should show ⟠ Sepolia or ⬡ Amoy

2. **Switch to Sepolia** (if not already):
   - Click on network icon in wallet button
   - Select "Sepolia" from dropdown
   - MetaMask popup: click "Switch network"
   - Wait 1-2 seconds

3. **Observe data changes**:
   - Network name updates in "Connection Info"
   - Chain ID changes to 11155111
   - Vault data shows ETH values

4. **Switch to Polygon Amoy**:
   - Click network icon again
   - Select "Polygon Amoy"
   - Approve switch in MetaMask
   - Wait 1-2 seconds

5. **Observe data changes**:
   - Network name updates to "Polygon Amoy"
   - Chain ID changes to 80002
   - Vault data now shows MATIC values
   - **Note**: Escrow section may disappear (only on Sepolia)

**Success Indicators:**
- ✅ Network switch happens smoothly
- ✅ Data updates automatically
- ✅ No errors in console
- ✅ Correct currency shown (ETH vs MATIC)

---

## 🧪 Test 4: Real-Time Data Updates

**Goal**: Verify hooks fetch fresh data from blockchain

### Steps:

1. **Open browser console**:
   - Press F12
   - Go to "Console" tab

2. **Watch for data fetching**:
   - You should see no errors
   - Wagmi may log some queries (normal)

3. **Force refresh** (without closing):
   - On Web3 Demo page, click browser refresh (F5)
   - Watch data reload
   - Should show same values as before

4. **Disconnect and reconnect wallet**:
   - Click wallet button → "Disconnect"
   - Page should show "Please connect your wallet" message
   - Click "Connect Wallet" again
   - Select MetaMask
   - Data should reload with same values

**Success Indicators:**
- ✅ Data persists across refreshes
- ✅ No "undefined" or "null" errors
- ✅ Loading states show briefly then resolve
- ✅ Data matches blockchain state

---

## 🧪 Test 5: Check Specific Contract Data

**Goal**: Verify hooks are reading correct blockchain data

### Test Escrow Count:

1. **On Web3 Demo page, find**:
   ```
   Total Escrows Created: [number]
   ```

2. **Verify on Etherscan**:
   - Go to: https://sepolia.etherscan.io/address/0x311E63dfcEfe7f2c202715ef0DF01CDA82f58914
   - Click "Contract" → "Read Contract"
   - Find `getEscrowCount()` function
   - Click "Query"
   - Compare number with what's shown in app

**They should match exactly!**

### Test Bridge Protocols:

1. **On Web3 Demo, find**:
   ```
   Registered Bridge Protocols: [axelar] [ccip]
   ```

2. **Verify on Etherscan**:
   - Go to: https://sepolia.etherscan.io/address/0xC96DA7e94E8407e0988bb60A1b23B9358Cd63A56
   - Click "Contract" → "Read Contract"
   - Find `getRegisteredProtocols()` function
   - Click "Query"
   - Compare protocols

**They should match exactly!**

---

## 🧪 Test 6: Browser Console Inspection

**Goal**: Ensure no errors and verify hook behavior

### Steps:

1. **Open Console** (F12)

2. **Check for errors**:
   - ❌ Red errors = problem
   - ⚠️ Yellow warnings = usually OK
   - ℹ️ Blue info = normal

3. **Look for wagmi/viem logs**:
   ```
   [wagmi] useReadContract: { ... }
   ```
   This is normal and shows hooks are working!

4. **Common errors and fixes**:

**Error**: `Chain not configured`
- **Fix**: Make sure you added Sepolia/Amoy to MetaMask

**Error**: `Connector not found`
- **Fix**: Reload page and try connecting again

**Error**: `User rejected request`
- **Fix**: Approve the connection in MetaMask

**Error**: `Network mismatch`
- **Fix**: Switch to Sepolia or Amoy in MetaMask

---

## 🧪 Test 7: Developer Tools Inspection

**Goal**: See hook internals and state

### Steps:

1. **Install React DevTools**:
   - Chrome: https://chrome.google.com/webstore/detail/react-developer-tools/fmkadmapgofadopljbjfkapdkoienihi

2. **Open React DevTools** (F12 → "Components" tab)

3. **Find Web3Demo component**:
   - Search for `Web3Demo` in the tree
   - Click on it

4. **Inspect hooks**:
   - On right panel, expand "hooks"
   - You should see:
     - `useAccount` → { address, isConnected, chain }
     - `useReadContract` → { data, isLoading, isError }
     - Multiple hooks for each contract call

5. **Verify data**:
   - `address` should be your wallet address
   - `isConnected` should be `true`
   - `chain.id` should be 11155111 or 80002
   - `data` in read hooks should contain blockchain data

**Success Indicators:**
- ✅ All hooks visible in DevTools
- ✅ Data is not undefined/null
- ✅ isLoading is false after initial load
- ✅ isError is false

---

## 🧪 Test 8: Multi-Chain Vault Data (Advanced)

**Goal**: See how multi-chain hook aggregates data

### What This Tests:
The `useMultiChainVaultData` hook fetches vault data from BOTH chains simultaneously.

### Steps:

1. **On Web3 Demo page, observe two vault cards**:
   - Blue card (Sepolia) - uses chainId 11155111
   - Purple card (Amoy) - uses chainId 80002

2. **Understanding the data**:
   ```typescript
   // This single hook calls:
   useTotalCollateral(address, 11155111) // Sepolia
   useTotalCollateral(address, 80002)    // Amoy
   useTotalBorrowed(address, 11155111)   // Sepolia
   useTotalBorrowed(address, 80002)      // Amoy
   // ... 6 total calls
   ```

3. **Switch networks in MetaMask**:
   - Notice BOTH cards still show data
   - The hook queries both chains regardless of connected network!

4. **This is the power of multi-chain hooks!**
   - You don't need to switch networks manually
   - Data from all chains loads simultaneously
   - Perfect for dashboards

**Success Indicators:**
- ✅ Both cards show data simultaneously
- ✅ Switching networks doesn't break either card
- ✅ Data loads independently

---

## 📊 Expected Results Summary

### ✅ What You SHOULD See:

1. **Wallet Connection**:
   - ✅ Connect wallet button works
   - ✅ MetaMask opens and connects
   - ✅ Wallet address shown in header
   - ✅ Network badge displays correctly

2. **Web3 Demo Page**:
   - ✅ Connection info displays
   - ✅ Escrow count shows (even if 0)
   - ✅ Vault data shows for both chains (even if 0)
   - ✅ Bridge protocols display

3. **No Errors**:
   - ✅ Console is clean (no red errors)
   - ✅ Data loads without hanging
   - ✅ Network switching works smoothly

### ❌ What You Should NOT See:

1. **Errors**:
   - ❌ "Cannot read property of undefined"
   - ❌ "Chain not configured"
   - ❌ "Failed to fetch"
   - ❌ Infinite loading states

2. **UI Issues**:
   - ❌ Blank sections (should show 0 or "No data")
   - ❌ Wallet button not appearing
   - ❌ Network switcher not working

---

## 🐛 Troubleshooting

### Problem: "Connect Wallet" button doesn't appear

**Solutions**:
1. Check header component is rendering
2. Open console and look for errors
3. Refresh page (F5)
4. Clear browser cache

### Problem: Wallet connects but no data loads

**Solutions**:
1. Check you're on Sepolia or Amoy (not mainnet!)
2. Open console and look for contract read errors
3. Verify contract addresses in `src/config/chains.ts`
4. Check RPC is responding (try Etherscan)

### Problem: "User rejected request" in MetaMask

**Solutions**:
1. This is normal if you clicked "Reject"
2. Just try connecting again
3. Click "Approve" this time

### Problem: Data shows all zeros

**Solutions**:
1. This is actually CORRECT if you haven't used the contracts!
2. Zero collateral = you haven't deposited
3. Zero escrows = you haven't created any
4. The hooks are working perfectly!

### Problem: Switching networks breaks the app

**Solutions**:
1. Refresh the page after switching
2. Disconnect and reconnect wallet
3. Check both networks are added to MetaMask

---

## 🎯 Quick Test Checklist

Use this to quickly verify everything works:

- [ ] Dev server running at http://localhost:5174/
- [ ] MetaMask installed and unlocked
- [ ] Sepolia network added to MetaMask
- [ ] Can login to app (any credentials)
- [ ] "Connect Wallet" button visible
- [ ] Wallet connects successfully
- [ ] Address shows in header
- [ ] Can navigate to Web3 Demo page
- [ ] Connection info displays
- [ ] Escrow count displays (number or 0)
- [ ] Vault data displays for Sepolia (blue card)
- [ ] Vault data displays for Amoy (purple card)
- [ ] Bridge protocols display
- [ ] Can switch between Sepolia and Amoy
- [ ] No red errors in console
- [ ] Can disconnect and reconnect wallet

**If all checked**: ✅ Everything is working perfectly!

---

## 💡 Understanding the Data

### Why might all values be zero?

**This is normal!** Here's why:

1. **Escrow Count = 0**:
   - No one has created escrows on this contract yet
   - OR the counter starts from a specific block
   - Solution: Create an escrow to test (requires testnet ETH)

2. **Your Escrows = Empty**:
   - You haven't created any escrows with your wallet
   - Perfectly normal for a new wallet
   - Solution: Create an escrow to see it appear

3. **Vault Collateral = 0**:
   - You haven't deposited collateral yet
   - Normal for new users
   - Solution: Deposit testnet ETH/MATIC to see balance

4. **Credit Line = 0**:
   - No collateral = no credit line
   - Makes sense mathematically
   - Solution: Deposit collateral to get credit

### What if escrow count shows a number?

**Example**: `Total Escrows Created: 42`

This means:
- ✅ The hook successfully called `getEscrowCount()`
- ✅ Contract has 42 escrows total (from all users)
- ✅ Your hook is reading real blockchain data!

### What if bridge protocols show "axelar" and "ccip"?

**This means**:
- ✅ BridgeManager contract is deployed
- ✅ Both Axelar and CCIP adapters are registered
- ✅ Your hook successfully called `getRegisteredProtocols()`
- ✅ Cross-chain messaging is configured!

---

## 🚀 Next Steps After Testing

Once you've verified everything works:

1. **Take screenshots** of the Web3 Demo page
2. **Test creating an escrow** (requires testnet ETH)
3. **Test depositing collateral** (requires testnet MATIC/ETH)
4. **Try sending a cross-chain message** (advanced)

Or continue building:
- Build Escrow UI pages (Week 2)
- Build Cross-Chain UI pages (Week 2)
- Implement real authentication (Week 1)

---

## 📚 Additional Resources

**Blockchain Explorers:**
- Sepolia: https://sepolia.etherscan.io
- Amoy: https://amoy.polygonscan.com

**Faucets:**
- Sepolia: https://sepoliafaucet.com
- Amoy: https://faucet.polygon.technology

**Documentation:**
- wagmi: https://wagmi.sh
- viem: https://viem.sh
- RainbowKit: https://rainbowkit.com

**Contract ABIs:**
- Location: `/src/abis/*.json`
- Can view functions in each ABI file

---

**Happy Testing! 🧪**

If you encounter any issues not covered here, check the browser console (F12) for error messages and consult the troubleshooting section.
