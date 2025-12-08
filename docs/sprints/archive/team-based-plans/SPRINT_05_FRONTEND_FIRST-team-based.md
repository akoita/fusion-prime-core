# Sprint 05: Frontend-First - Web3 Integration & UI Completion

**Planning Date**: November 3, 2025 (Revised - Frontend Priority)
**Sprint Duration**: 4 weeks
**Status**: 🚀 **READY TO START**
**Prerequisites**: ✅ Sprint 04 Complete (Backend)

---

## 🎯 Critical Discovery

**MAJOR FINDING**: After comprehensive code analysis, we discovered:
- ✅ Smart contracts are deployed and functional on Sepolia testnet
- ✅ Backend services are 100% operational (12 microservices)
- 🔴 **Frontend has ZERO blockchain integration** - no Web3 libraries, no wallet connection, no contract interaction
- 🔴 **Frontend has ZERO Sprint 04 feature integration** - no cross-chain UI, no fiat gateway UI
- 🔴 **Frontend has mock authentication** - any password works

**Current State**: The frontend is a backend API dashboard, not a Web3 application.

**See**: `docs/PROJECT_IMPLEMENTATION_STATUS.md` for full analysis

---

## 🎯 Sprint 05 Overview (Frontend-First)

### Goal
Transform the frontend from a backend API dashboard into a **polished, production-ready Web3 application** with full blockchain integration, real authentication, and all Sprint 04 features.

### Objectives (Priority Order)
1. 🔴 **CRITICAL**: Implement Web3 integration layer (wallet connection, contract interaction)
2. 🔴 **CRITICAL**: Build Escrow UI (create, manage, approve/release/refund escrows)
3. 🔴 **CRITICAL**: Build Cross-Chain UI (settlements, collateral snapshots, message tracking)
4. 🔴 **CRITICAL**: Implement real authentication (backend + frontend)
5. 🟡 **HIGH**: Build Fiat Gateway UI (on-ramp, off-ramp, transaction history)
6. 🟡 **HIGH**: Polish UI/UX (consistency, responsiveness, error handling)
7. 🟡 **HIGH**: End-to-end testing with real blockchain
8. 🟢 **MEDIUM**: Deploy Developer Portal

---

## 📋 Workstream Breakdown (4 Weeks)

### Week 1: Web3 Foundation + Authentication 🔴

#### 1.1 Web3 Infrastructure Setup (Days 1-3)
**Owner**: Frontend Team
**Priority**: CRITICAL

**Tasks:**
- [ ] Install Web3 libraries
  ```bash
  cd frontend/risk-dashboard
  pnpm add ethers@6 wagmi@2 viem@2 @rainbow-me/rainbowkit@2
  pnpm add @tanstack/react-query@5  # Required by wagmi
  ```

- [ ] Set up Wagmi + RainbowKit configuration
  - [ ] Create `src/config/wagmi.ts` - Chain config (Sepolia, Amoy)
  - [ ] Configure RPC providers (Infura, Alchemy, or custom)
  - [ ] Set up wallet connectors (MetaMask, WalletConnect, Coinbase Wallet)

- [ ] Create wallet connection UI
  - [ ] Add "Connect Wallet" button to header
  - [ ] Implement wallet connection modal (RainbowKit)
  - [ ] Display connected wallet address
  - [ ] Add network switcher (Sepolia ↔ Amoy)
  - [ ] Handle wallet disconnection

- [ ] Import contract ABIs
  - [ ] Copy ABIs from `contracts/out/` to `frontend/risk-dashboard/src/abis/`
  - [ ] Create ABI files:
    - `EscrowFactory.json`
    - `Escrow.json`
    - `CrossChainVault.json`
    - `BridgeManager.json`
    - `AxelarAdapter.json`
    - `CCIPAdapter.json`
  - [ ] Generate TypeScript types using wagmi CLI or typechain

- [ ] Create contract hooks
  - [ ] `src/hooks/useEscrowFactory.ts` - Read/write EscrowFactory
  - [ ] `src/hooks/useEscrow.ts` - Interact with individual escrows
  - [ ] `src/hooks/useCrossChainVault.ts` - CrossChainVault interactions
  - [ ] `src/hooks/useBridgeManager.ts` - Bridge messaging

- [ ] Create contract service layer
  - [ ] `src/services/contracts/escrowFactory.ts`
  - [ ] `src/services/contracts/crossChainVault.ts`
  - [ ] Contract address configuration (Sepolia, Amoy)

**Deliverables:**
- Web3 libraries installed and configured
- Wallet connection functional (MetaMask, WalletConnect)
- Contract ABIs imported with TypeScript types
- Contract hooks ready for use
- Network switcher working (Sepolia ↔ Amoy)

**Contract Addresses to Configure:**

**Sepolia (Chain ID: 11155111):**
```typescript
export const CONTRACTS_SEPOLIA = {
  EscrowFactory: '0x311E63dfcEfe7f2c202715ef0DF01CDA82f58914',
  CrossChainVault: '0x0C95a78b0D72F882fae14CD7C842a5f000E0c4e2',
  BridgeManager: '0xC96DA7e94E8407e0988bb60A1b23B9358Cd63A56',
  AxelarAdapter: '0x3C8e965aFF06DFcaE9f6cc778b38d72D54D1381d',
  CCIPAdapter: '0x9204E095e6d50Ff8f828e71F4C0849C5aEfe992c',
};
```

**Amoy (Chain ID: 80002):**
```typescript
export const CONTRACTS_AMOY = {
  CrossChainVault: '0x7843C2eD8930210142DC51dbDf8419C74FD27529',
  BridgeManager: '0x3481dbE036C0F4076B397e27FFb8dC32B88d8882',
  AxelarAdapter: '0x6e48D179CD80979c8eDf65A5d783B501A0313159',
  CCIPAdapter: '0xe15A30f1eF8c1De56F19b7Cef61cC3776119451C',
};
```

---

#### 1.2 Authentication Implementation (Days 3-5)
**Owner**: Backend + Frontend Teams
**Priority**: CRITICAL

**Backend Tasks:**
- [ ] Create Identity Service
  - [ ] Service scaffold (FastAPI)
  - [ ] User registration endpoint (`POST /auth/register`)
  - [ ] User login endpoint (`POST /auth/login`)
  - [ ] Token refresh endpoint (`POST /auth/refresh`)
  - [ ] User profile endpoint (`GET /auth/me`)
  - [ ] JWT token generation (access + refresh)
  - [ ] Password hashing (bcrypt)
  - [ ] Database: users table, refresh_tokens table
  - [ ] Alembic migrations
  - [ ] Tests (>80% coverage)
  - [ ] Deploy to Cloud Run

**Frontend Tasks:**
- [ ] Replace mock authentication
  - [ ] Update `src/lib/auth.ts` to call Identity Service
  - [ ] Implement real login function
  - [ ] Implement real registration function
  - [ ] Implement token refresh logic
  - [ ] Remove ALL mock authentication code

- [ ] Token management
  - [ ] Store access token in memory
  - [ ] Store refresh token in httpOnly cookie or localStorage
  - [ ] Automatic token refresh before expiry
  - [ ] Clear tokens on logout

- [ ] API client updates
  - [ ] Add Authorization header (Bearer token)
  - [ ] Implement token refresh on 401 responses
  - [ ] Retry failed requests after refresh

- [ ] Login/Registration UI
  - [ ] Update login form
  - [ ] Add registration form
  - [ ] Add password reset flow (optional)
  - [ ] Loading states and error handling

**Deliverables:**
- Identity Service deployed and operational
- Frontend authentication functional with real backend
- No mock authentication code remaining
- Token management working correctly

---

### Week 2: Escrow UI + Cross-Chain UI 🔴

#### 2.1 Escrow Management UI (Days 1-3)
**Owner**: Frontend Team
**Priority**: CRITICAL

**New Pages to Create:**

**A. `/escrow/create` - Create Escrow Page**
- [ ] Create escrow form
  - [ ] Payee address input (with ENS support)
  - [ ] Amount input (ETH or token)
  - [ ] Arbiter address input
  - [ ] Timelock duration selector
  - [ ] Description/notes field
- [ ] Transaction flow
  - [ ] Estimate gas
  - [ ] Show transaction preview
  - [ ] Request wallet signature
  - [ ] Submit transaction to EscrowFactory
  - [ ] Show transaction status (pending, confirmed, failed)
  - [ ] Display new escrow address
- [ ] Post-creation
  - [ ] Redirect to escrow details page
  - [ ] Add to user's escrow list
  - [ ] Show success notification

**B. `/escrow/manage` - Escrow List Page**
- [ ] List all user escrows
  - [ ] Query `EscrowFactory.getUserEscrows(userAddress)` on-chain
  - [ ] Display escrow cards with:
    - Escrow address
    - Status (Created, Approved, Released, Refunded, Disputed)
    - Amount
    - Payee
    - Created date
    - Actions (View, Approve, Release, Refund)
- [ ] Filter and sort
  - [ ] Filter by status (Active, Completed, Disputed)
  - [ ] Sort by date, amount
- [ ] Pagination
  - [ ] Handle large escrow lists

**C. `/escrow/:escrowAddress` - Escrow Details Page**
- [ ] Escrow information display
  - [ ] Read all escrow data from blockchain:
    - `getStatus()` - Current status
    - `payer()`, `payee()`, `arbiter()` - Parties
    - `amount` - Escrow amount
    - `timelock` - Release time
    - `isApproved()` - Approval status
  - [ ] Show transaction history (events from blockchain)
  - [ ] Display timeline (Created → Approved → Released)

- [ ] Action buttons (based on user role)
  - [ ] **Payer actions:**
    - "Refund" button → calls `escrow.refund()`
  - [ ] **Payee actions:**
    - "Approve" button → calls `escrow.approve()`
  - [ ] **Arbiter actions:**
    - "Release to Payee" button → calls `escrow.release()`
    - "Refund to Payer" button → calls `escrow.refund()`

- [ ] Transaction execution
  - [ ] Request wallet signature for each action
  - [ ] Show transaction status (pending, confirmed, failed)
  - [ ] Update UI on transaction success
  - [ ] Handle errors gracefully

- [ ] Real-time updates
  - [ ] Listen to contract events:
    - `EscrowApproved(address escrow)`
    - `EscrowReleased(address escrow, address payee)`
    - `EscrowRefunded(address escrow, address payer)`
  - [ ] Update UI when events occur
  - [ ] Show notifications for status changes

**Technical Implementation:**

```typescript
// Example: useEscrowFactory hook
import { useContractRead, useContractWrite } from 'wagmi';
import EscrowFactoryABI from '@/abis/EscrowFactory.json';

export function useCreateEscrow() {
  const { write, isLoading, isSuccess, data } = useContractWrite({
    address: CONTRACTS_SEPOLIA.EscrowFactory,
    abi: EscrowFactoryABI,
    functionName: 'createEscrow',
  });

  const createEscrow = (payee: Address, arbiter: Address, timelock: number) => {
    write({
      args: [payee, arbiter, timelock],
      value: parseEther('1.0'), // Amount in ETH
    });
  };

  return { createEscrow, isLoading, isSuccess, txHash: data?.hash };
}

// Example: useEscrow hook
export function useEscrowStatus(escrowAddress: Address) {
  const { data: status } = useContractRead({
    address: escrowAddress,
    abi: EscrowABI,
    functionName: 'getStatus',
    watch: true, // Real-time updates
  });

  return status; // 0: Created, 1: Approved, 2: Released, 3: Refunded, 4: Disputed
}
```

**Deliverables:**
- Escrow creation UI functional
- Escrow list page showing on-chain escrows
- Escrow details page with approve/release/refund actions
- All escrow contract interactions working
- Real-time escrow status updates

---

#### 2.2 Cross-Chain UI (Days 3-5)
**Owner**: Frontend Team
**Priority**: CRITICAL

**New Pages to Create:**

**A. `/cross-chain/vault` - Collateral Vault Page**
- [ ] Multi-chain collateral display
  - [ ] Query collateral balances from blockchain:
    - Call `CrossChainVault.collateralBalances(userAddress, "sepolia")` on Sepolia
    - Call `CrossChainVault.collateralBalances(userAddress, "amoy")` on Amoy
  - [ ] Display collateral per chain:
    - Sepolia: X ETH ($Y USD)
    - Amoy: Z MATIC ($W USD)
    - Total: $XYZ USD
  - [ ] Show available credit line:
    - Query `CrossChainVault.totalCreditLine(userAddress)`
    - Display: "Available Credit: $X,XXX"

- [ ] Deposit collateral form
  - [ ] Chain selector (Sepolia / Amoy)
  - [ ] Asset selector (ETH, USDC, WETH)
  - [ ] Amount input
  - [ ] "Deposit" button → calls `CrossChainVault.depositCollateral()`
  - [ ] Transaction flow with wallet signature

- [ ] Withdraw collateral form
  - [ ] Chain selector
  - [ ] Asset selector
  - [ ] Amount input (max: available balance)
  - [ ] "Withdraw" button → calls `CrossChainVault.withdrawCollateral()`
  - [ ] Transaction flow

- [ ] Borrow/Repay forms (if implemented)
  - [ ] Borrow against collateral
  - [ ] Repay borrowed amount
  - [ ] Show borrow limits

**B. `/cross-chain/settle` - Cross-Chain Settlement Page**
- [ ] Settlement initiation form
  - [ ] Source chain selector (Sepolia / Amoy)
  - [ ] Destination chain selector
  - [ ] Asset selector (USDC, WETH)
  - [ ] Amount input
  - [ ] Bridge protocol selector:
    - Axelar (faster, lower cost)
    - CCIP (more secure, higher cost)
  - [ ] Estimated fees display
  - [ ] Estimated time display (2-5 minutes)

- [ ] Settlement execution
  - [ ] Encode cross-chain message payload
  - [ ] Call `BridgeManager.sendMessage()` on source chain
  - [ ] Request wallet signature
  - [ ] Submit transaction
  - [ ] Return message ID

- [ ] Integration with Cross-Chain Integration Service (backend)
  - [ ] After blockchain transaction succeeds, call backend:
    - `POST /cross-chain/settlement` with message ID
    - Backend starts monitoring message status
  - [ ] Backend tracks message through Axelar/CCIP
  - [ ] Frontend polls backend for status updates

**C. `/cross-chain/messages` - Message Tracking Page**
- [ ] List of cross-chain messages
  - [ ] Fetch from backend: `GET /cross-chain/messages`
  - [ ] Display message cards:
    - Message ID
    - Source chain → Destination chain
    - Amount and asset
    - Bridge protocol (Axelar/CCIP)
    - Status (Pending / Confirmed / Failed)
    - Timestamp
  - [ ] Filter by status, chain, protocol

- [ ] Message details view
  - [ ] Show detailed message information
  - [ ] Display transaction hashes (source and destination)
  - [ ] Show message payload
  - [ ] Display gas fees paid
  - [ ] Show confirmation time

- [ ] Message status tracking
  - [ ] For Axelar messages:
    - Show AxelarScan link
    - Display confirmation status
  - [ ] For CCIP messages:
    - Show CCIP Explorer link
    - Display confirmation status
  - [ ] Real-time updates via WebSocket from backend

- [ ] Failed message retry
  - [ ] "Retry" button for failed messages
  - [ ] Calls backend: `POST /cross-chain/retry/{message_id}`
  - [ ] Backend retries bridge transaction

**D. `/cross-chain/snapshot` - Collateral Snapshot Page**
- [ ] Current snapshot display
  - [ ] Fetch from backend: `GET /cross-chain/snapshot`
  - [ ] Display:
    - Total collateral across all chains (USD)
    - Per-chain breakdown with pie chart
    - Credit line available
    - Borrow utilization %

- [ ] Snapshot history
  - [ ] Chart showing collateral over time
  - [ ] Historical snapshots list
  - [ ] Export functionality (CSV, PDF)

**Technical Implementation:**

```typescript
// Example: useCrossChainVault hook
export function useCollateralBalance(chain: 'sepolia' | 'amoy') {
  const { address } = useAccount();

  const { data: balance } = useContractRead({
    address: chain === 'sepolia'
      ? CONTRACTS_SEPOLIA.CrossChainVault
      : CONTRACTS_AMOY.CrossChainVault,
    abi: CrossChainVaultABI,
    functionName: 'collateralBalances',
    args: [address, chain],
    chainId: chain === 'sepolia' ? 11155111 : 80002,
    watch: true,
  });

  return balance; // Returns collateral amount
}

// Example: useSendCrossChainMessage hook
export function useSendCrossChainMessage() {
  const { write, isLoading, data } = useContractWrite({
    address: CONTRACTS_SEPOLIA.BridgeManager,
    abi: BridgeManagerABI,
    functionName: 'sendMessage',
  });

  const sendMessage = (
    destinationChain: string,
    payload: Hex,
    gasAmount: bigint
  ) => {
    write({
      args: [destinationChain, payload],
      value: gasAmount, // Gas fees for bridge
    });
  };

  return { sendMessage, isLoading, txHash: data?.hash };
}
```

**Deliverables:**
- Collateral vault page showing real on-chain balances
- Cross-chain settlement initiation working
- Message tracking page with real-time updates
- Integration between blockchain (contracts) and backend (monitoring service)
- Snapshot visualization from backend data

---

### Week 3: Fiat Gateway UI + UI Polish 🟡

#### 3.1 Fiat Gateway UI (Days 1-2)
**Owner**: Frontend Team
**Priority**: HIGH

**New Pages to Create:**

**A. `/fiat/on-ramp` - Fiat On-Ramp Page**
- [ ] Circle USDC on-ramp form
  - [ ] Amount input (USD)
  - [ ] Payment method selector:
    - Bank transfer (ACH)
    - Debit card
    - Wire transfer
  - [ ] Destination address input (user's wallet or vault)
  - [ ] Preview:
    - Amount in USD
    - Amount in USDC
    - Fees
    - Total
  - [ ] "Continue" button

- [ ] Payment execution
  - [ ] Call backend: `POST /fiat/on-ramp` (Fiat Gateway Service)
  - [ ] Backend creates Circle payment intent
  - [ ] Frontend displays Circle payment widget
  - [ ] User completes payment
  - [ ] Show transaction confirmation

- [ ] Transaction tracking
  - [ ] Poll backend for transaction status
  - [ ] Display status: Pending → Processing → Completed
  - [ ] Show USDC transfer to destination address
  - [ ] Link to blockchain transaction

**B. `/fiat/off-ramp` - Fiat Off-Ramp Page**
- [ ] USDC to Fiat form
  - [ ] Amount input (USDC)
  - [ ] Source selector (wallet or vault)
  - [ ] Bank account details form:
    - Account holder name
    - Routing number
    - Account number
  - [ ] Preview:
    - Amount in USDC
    - Amount in USD
    - Fees
    - Net amount received
  - [ ] "Withdraw" button

- [ ] Withdrawal execution
  - [ ] Call backend: `POST /fiat/off-ramp` (Fiat Gateway Service)
  - [ ] Backend creates Stripe payout
  - [ ] Show confirmation
  - [ ] Display estimated arrival time (3-5 business days)

**C. `/fiat/transactions` - Transaction History Page**
- [ ] Transaction list
  - [ ] Fetch from backend: `GET /fiat/transactions`
  - [ ] Display transactions:
    - Type (On-ramp / Off-ramp)
    - Amount (USD and USDC)
    - Status (Pending / Completed / Failed)
    - Provider (Circle / Stripe)
    - Date
    - Transaction ID
  - [ ] Filter by type, status, date range
  - [ ] Pagination

- [ ] Transaction details modal
  - [ ] Show full transaction details
  - [ ] Display provider transaction ID
  - [ ] Link to blockchain transaction (if applicable)
  - [ ] Show fees breakdown
  - [ ] Receipt download (PDF)

**Deliverables:**
- Fiat on-ramp functional (Circle integration)
- Fiat off-ramp functional (Stripe integration)
- Transaction history page
- Integration with Fiat Gateway Service

---

#### 3.2 UI/UX Polish (Days 3-5)
**Owner**: Frontend Team
**Priority**: HIGH

**Design System & Consistency:**
- [ ] Establish design system
  - [ ] Color palette (primary, secondary, accent, neutral)
  - [ ] Typography scale (headings, body, captions)
  - [ ] Spacing system (4px, 8px, 16px, 24px, 32px, etc.)
  - [ ] Border radius standards
  - [ ] Shadow/elevation standards

- [ ] Component library
  - [ ] Button variants (primary, secondary, outline, ghost, danger)
  - [ ] Input components (text, number, select, textarea)
  - [ ] Card component (consistent padding, borders, shadows)
  - [ ] Modal/Dialog component
  - [ ] Toast/Notification component
  - [ ] Loading states (spinners, skeletons)
  - [ ] Empty states
  - [ ] Error states

- [ ] Ensure consistency
  - [ ] Audit all pages for design inconsistencies
  - [ ] Apply design system to all components
  - [ ] Consistent spacing and layout
  - [ ] Consistent typography
  - [ ] Consistent button styles

**Responsiveness:**
- [ ] Mobile-first design
  - [ ] Test all pages on mobile (375px width)
  - [ ] Responsive breakpoints: mobile (< 640px), tablet (640-1024px), desktop (> 1024px)
  - [ ] Mobile navigation (hamburger menu)
  - [ ] Touch-friendly buttons (min 44px height)

- [ ] Tablet optimization
  - [ ] 2-column layouts where appropriate
  - [ ] Optimized spacing for medium screens

- [ ] Desktop optimization
  - [ ] Max content width (1280px or 1440px)
  - [ ] Sidebars and multi-column layouts
  - [ ] Hover states for interactive elements

**Error Handling:**
- [ ] Global error boundary
  - [ ] Catch React errors
  - [ ] Display user-friendly error page
  - [ ] Log errors to monitoring service

- [ ] Network error handling
  - [ ] Detect offline state
  - [ ] Show "No internet connection" message
  - [ ] Retry failed requests

- [ ] Blockchain error handling
  - [ ] User rejected transaction → Show friendly message
  - [ ] Insufficient funds → Display clear error
  - [ ] Network congestion → Suggest higher gas price
  - [ ] Contract revert → Parse revert reason and display

- [ ] Form validation
  - [ ] Real-time validation with clear error messages
  - [ ] Prevent invalid form submissions
  - [ ] Highlight invalid fields

**Loading States:**
- [ ] Skeleton screens
  - [ ] Implement skeletons for data-heavy pages
  - [ ] Show loading skeletons while fetching data

- [ ] Progress indicators
  - [ ] Spinner for short waits (< 3 seconds)
  - [ ] Progress bar for longer operations
  - [ ] Transaction status indicators

- [ ] Optimistic UI updates
  - [ ] Update UI immediately, confirm later
  - [ ] Revert on error

**Accessibility:**
- [ ] Keyboard navigation
  - [ ] All interactive elements focusable
  - [ ] Logical tab order
  - [ ] Focus indicators visible

- [ ] ARIA labels
  - [ ] Add aria-label to icon buttons
  - [ ] Use semantic HTML (nav, main, footer, etc.)
  - [ ] Proper heading hierarchy (h1, h2, h3)

- [ ] Color contrast
  - [ ] Ensure WCAG AA compliance (4.5:1 for text)
  - [ ] Don't rely on color alone for information

**Performance:**
- [ ] Code splitting
  - [ ] Lazy load routes
  - [ ] Lazy load heavy components (charts)

- [ ] Image optimization
  - [ ] Use WebP format
  - [ ] Lazy load images
  - [ ] Proper sizing (no oversized images)

- [ ] Bundle optimization
  - [ ] Analyze bundle size
  - [ ] Remove unused dependencies
  - [ ] Tree-shake libraries

**Deliverables:**
- Consistent design system applied
- Fully responsive (mobile, tablet, desktop)
- Comprehensive error handling
- Loading states for all async operations
- Accessible to keyboard users
- Optimized performance

---

### Week 4: Testing, Deployment & Documentation 🟢

#### 4.1 End-to-End Testing (Days 1-2)
**Owner**: Frontend + QA Teams
**Priority**: HIGH

**Test Setup:**
- [ ] Install testing tools
  ```bash
  pnpm add -D @playwright/test vitest @testing-library/react
  ```

- [ ] Configure Playwright
  - [ ] Set up for E2E tests
  - [ ] Configure test networks (Sepolia testnet)
  - [ ] Set up test wallets with testnet ETH

**E2E Test Scenarios:**

**A. Authentication Flow**
- [ ] Test: User registration
  - Navigate to register page
  - Fill registration form
  - Submit and verify account created
  - Verify redirect to dashboard

- [ ] Test: User login
  - Navigate to login page
  - Enter credentials
  - Submit and verify successful login
  - Verify access token stored

- [ ] Test: User logout
  - Click logout button
  - Verify tokens cleared
  - Verify redirect to login page

**B. Wallet Connection Flow**
- [ ] Test: Connect MetaMask
  - Click "Connect Wallet" button
  - Select MetaMask from modal
  - Approve connection in MetaMask (using Playwright with MetaMask extension)
  - Verify wallet address displayed
  - Verify network is Sepolia

- [ ] Test: Switch networks
  - Click network switcher
  - Select Amoy testnet
  - Approve network switch in wallet
  - Verify network changed

- [ ] Test: Disconnect wallet
  - Click disconnect button
  - Verify wallet disconnected
  - Verify UI updated

**C. Escrow Creation Flow**
- [ ] Test: Create escrow successfully
  - Connect wallet
  - Navigate to /escrow/create
  - Fill escrow form (payee, amount, arbiter, timelock)
  - Submit form
  - Approve transaction in MetaMask
  - Wait for transaction confirmation
  - Verify escrow created on blockchain
  - Verify redirect to escrow details page
  - Verify escrow appears in escrow list

- [ ] Test: Escrow approval flow (as payee)
  - Connect as payee wallet
  - Navigate to escrow details
  - Click "Approve" button
  - Approve transaction
  - Wait for confirmation
  - Verify escrow status updated to "Approved"

- [ ] Test: Escrow release flow (as arbiter)
  - Connect as arbiter wallet
  - Navigate to escrow details
  - Click "Release" button
  - Approve transaction
  - Wait for confirmation
  - Verify funds transferred to payee
  - Verify escrow status updated to "Released"

**D. Cross-Chain Settlement Flow**
- [ ] Test: Initiate cross-chain settlement
  - Connect wallet on Sepolia
  - Navigate to /cross-chain/settle
  - Fill settlement form (destination: Amoy, amount: 0.1 ETH, bridge: Axelar)
  - Submit form
  - Approve transaction
  - Wait for confirmation
  - Verify message appears in message list with status "Pending"

- [ ] Test: Track cross-chain message
  - Navigate to /cross-chain/messages
  - Find recently created message
  - Click to view details
  - Verify transaction hashes displayed
  - Wait for status to change to "Confirmed" (may take 2-5 minutes)
  - Verify destination transaction hash appears

**E. Fiat Gateway Flow**
- [ ] Test: Fiat on-ramp
  - Navigate to /fiat/on-ramp
  - Fill form (amount: $100, payment: test card)
  - Submit form
  - Complete Circle payment widget (test mode)
  - Wait for transaction confirmation
  - Verify USDC received in wallet

- [ ] Test: Fiat off-ramp
  - Navigate to /fiat/off-ramp
  - Fill form (amount: 100 USDC, bank account: test account)
  - Submit form
  - Verify withdrawal initiated
  - Verify transaction in history with status "Pending"

**F. Error Handling Tests**
- [ ] Test: Insufficient funds
  - Attempt to create escrow with amount > wallet balance
  - Verify error message displayed
  - Verify transaction not sent

- [ ] Test: User rejects transaction
  - Start any blockchain transaction
  - Reject in MetaMask
  - Verify friendly error message
  - Verify UI not stuck in loading state

- [ ] Test: Network disconnection
  - Disconnect internet
  - Attempt to fetch data
  - Verify "No internet connection" message
  - Reconnect internet
  - Verify data loads

**Unit Tests:**
- [ ] Component tests
  - [ ] Test form validation
  - [ ] Test button states (loading, disabled, etc.)
  - [ ] Test modal open/close

- [ ] Hook tests
  - [ ] Test custom hooks (useEscrow, useCrossChainVault, etc.)
  - [ ] Mock contract calls
  - [ ] Verify correct data transformations

**Deliverables:**
- E2E test suite with 20+ test scenarios
- Unit tests for critical components
- Test coverage >70%
- CI/CD integration (tests run on every commit)

---

#### 4.2 Developer Portal Deployment (Day 3)
**Owner**: DevOps Team
**Priority**: MEDIUM

**Tasks:**
- [ ] Create Cloud Build configuration
  - [ ] Create `frontend/developer-portal/cloudbuild.yaml`
  - [ ] Configure build steps (install, build, containerize)
  - [ ] Set environment variables

- [ ] Deploy to Cloud Run
  - [ ] Create Cloud Run service
  - [ ] Configure service (CPU, memory, autoscaling)
  - [ ] Set custom domain (optional): `developers.fusionprime.dev`

- [ ] Update API documentation
  - [ ] Add Cross-Chain Integration Service endpoints
  - [ ] Add Fiat Gateway Service endpoints
  - [ ] Add Identity Service endpoints
  - [ ] Update examples and code snippets

- [ ] Test deployment
  - [ ] Verify portal loads
  - [ ] Test API key creation
  - [ ] Test interactive playground
  - [ ] Verify all API docs render correctly

**Deliverables:**
- Developer Portal deployed to Cloud Run
- Public URL accessible
- API documentation complete and up-to-date

---

#### 4.3 Documentation & Sprint Review (Days 4-5)
**Owner**: All Teams
**Priority**: MEDIUM

**Documentation Tasks:**
- [ ] User Guide
  - [ ] Write "Getting Started" guide
  - [ ] Document wallet connection process
  - [ ] Document escrow creation and management
  - [ ] Document cross-chain settlements
  - [ ] Document fiat on/off-ramps

- [ ] Developer Documentation
  - [ ] Document Web3 integration architecture
  - [ ] Document contract interaction patterns
  - [ ] Document state management approach
  - [ ] Document testing strategy

- [ ] Deployment Guide
  - [ ] Document frontend deployment process
  - [ ] Document environment variables
  - [ ] Document build configuration

- [ ] Troubleshooting Guide
  - [ ] Common wallet connection issues
  - [ ] Common transaction errors
  - [ ] Network configuration issues

**Sprint Review:**
- [ ] Demo preparation
  - [ ] Prepare live demo (end-to-end user journey)
  - [ ] Test demo on staging environment

- [ ] Sprint retrospective
  - [ ] What went well?
  - [ ] What could be improved?
  - [ ] Blockers encountered?

- [ ] Metrics review
  - [ ] Test coverage achieved
  - [ ] Performance metrics (Lighthouse scores)
  - [ ] Deployment success

**Deliverables:**
- Complete user and developer documentation
- Sprint review presentation
- Retrospective notes
- Metrics report

---

## 📊 Sprint 05 Success Criteria

### Critical Success Criteria (Must Have)
- [ ] ✅ Wallet connection functional (MetaMask, WalletConnect)
- [ ] ✅ Users can create escrows via UI interacting with EscrowFactory contract
- [ ] ✅ Users can approve/release/refund escrows via UI
- [ ] ✅ Users can see their collateral balances from CrossChainVault contracts
- [ ] ✅ Users can initiate cross-chain settlements via UI
- [ ] ✅ Users can track cross-chain messages in real-time
- [ ] ✅ Users can perform fiat on-ramp (Circle) and off-ramp (Stripe)
- [ ] ✅ Real authentication working (no mock auth remaining)
- [ ] ✅ UI is polished, consistent, and responsive
- [ ] ✅ E2E tests passing (>20 scenarios)

### High Priority Criteria (Should Have)
- [ ] Test coverage >70% for frontend
- [ ] Developer Portal deployed
- [ ] Performance: Lighthouse score >90 (Performance, Accessibility)
- [ ] Error handling comprehensive
- [ ] Documentation complete

### Medium Priority Criteria (Nice to Have)
- [ ] Mobile app design (responsive web as foundation)
- [ ] Advanced analytics visualizations
- [ ] Real-time notifications (WebSocket)
- [ ] Internationalization (i18n) support

---

## 📅 Week-by-Week Summary

| Week | Focus | Key Deliverables |
|------|-------|------------------|
| **Week 1** | Web3 Foundation + Authentication | Wallet connection, Contract ABIs, Identity Service, Real auth |
| **Week 2** | Blockchain UI (Escrow + Cross-Chain) | Escrow creation/management, Cross-chain settlements, Message tracking |
| **Week 3** | Fiat Gateway + UI Polish | Fiat on/off-ramp, Design system, Responsiveness, Error handling |
| **Week 4** | Testing + Deployment | E2E tests, Developer Portal, Documentation, Sprint review |

---

## 🔍 Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Web3 integration complexity** | High | Use battle-tested libraries (wagmi, RainbowKit). Follow official docs |
| **Testnet instability** | Medium | Have fallback RPC providers. Use Infura/Alchemy for reliability |
| **Cross-chain message delays** | Medium | Set user expectations (2-5 min). Show real-time status updates |
| **Wallet connection issues** | Medium | Provide clear troubleshooting guides. Support multiple wallets |
| **Testing with real blockchain** | High | Allocate extra time for E2E tests. Use testnet faucets for funds |
| **UI/UX consistency** | Low | Establish design system early. Review all pages for consistency |

---

## 📝 Technical Stack (Frontend)

### Core Libraries
- **React 18** - UI framework
- **Vite** - Build tool
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling

### Web3 Libraries (NEW)
- **ethers.js v6** - Ethereum library
- **wagmi v2** - React hooks for Ethereum
- **viem v2** - TypeScript Ethereum interface
- **RainbowKit v2** - Wallet connection UI

### State Management
- **Zustand** - Global state
- **@tanstack/react-query** - Server state (required by wagmi)

### Testing
- **Vitest** - Unit tests
- **@testing-library/react** - Component tests
- **Playwright** - E2E tests

### Other
- **Recharts** - Data visualization
- **axios** - HTTP client (for backend APIs)
- **socket.io-client** - WebSocket (for real-time updates)

---

## 🎯 Definition of Done

A feature is considered "done" when:
1. ✅ Code is written and reviewed
2. ✅ Unit tests written and passing
3. ✅ E2E test scenario created and passing
4. ✅ Works on mobile, tablet, and desktop
5. ✅ Error handling implemented
6. ✅ Loading states implemented
7. ✅ Accessible (keyboard navigation, ARIA labels)
8. ✅ Integrated with real blockchain contracts
9. ✅ Integrated with real backend services
10. ✅ Documentation updated
11. ✅ Deployed to staging environment
12. ✅ QA approved

---

## 📦 Deliverables Checklist

### Week 1
- [ ] Web3 libraries installed and configured
- [ ] Wallet connection UI functional
- [ ] Contract ABIs imported with TypeScript types
- [ ] Identity Service deployed
- [ ] Frontend authentication working (no mock)

### Week 2
- [ ] Escrow creation UI (/escrow/create)
- [ ] Escrow management UI (/escrow/manage)
- [ ] Escrow details UI (/escrow/:id)
- [ ] Cross-chain vault UI (/cross-chain/vault)
- [ ] Cross-chain settlement UI (/cross-chain/settle)
- [ ] Message tracking UI (/cross-chain/messages)

### Week 3
- [ ] Fiat on-ramp UI (/fiat/on-ramp)
- [ ] Fiat off-ramp UI (/fiat/off-ramp)
- [ ] Transaction history UI (/fiat/transactions)
- [ ] Design system established and applied
- [ ] Fully responsive (mobile, tablet, desktop)
- [ ] Comprehensive error handling
- [ ] Loading states everywhere

### Week 4
- [ ] E2E test suite (20+ scenarios)
- [ ] Unit test coverage >70%
- [ ] Developer Portal deployed
- [ ] User guide documentation
- [ ] Developer documentation
- [ ] Sprint review completed

---

## 🚀 Post-Sprint 05

After Sprint 05 completion, the platform will have:
- ✅ **Fully functional Web3 frontend** with wallet connection
- ✅ **Complete blockchain integration** (escrow + cross-chain contracts)
- ✅ **Real authentication** (no mock)
- ✅ **All Sprint 04 features** in UI (cross-chain, fiat gateway)
- ✅ **Polished, consistent, responsive UI**
- ✅ **Comprehensive testing** (E2E + unit)
- ✅ **Production-ready frontend**

**Next Sprint (Sprint 06):**
- Security audit (smart contracts + services)
- Performance optimization and load testing
- Production deployment (mainnet)
- Advanced features (governance, staking, etc.)

---

**Status**: 🚀 Ready to Start
**Priority**: Frontend-First with Blockchain Integration
**Timeline**: 4 weeks to production-ready frontend
**Next Action**: Install Web3 libraries and set up wallet connection (Week 1, Day 1)

---

## See Also
- `docs/PROJECT_IMPLEMENTATION_STATUS.md` - Full implementation analysis
- `docs/FRONTEND_CONTRACT_INTEGRATION_ANALYSIS.md` - Detailed blockchain integration gaps
- `contracts/out/` - Contract ABIs to import
- `frontend/risk-dashboard/src/lib/auth.ts` - Current mock auth (TO BE REPLACED)
