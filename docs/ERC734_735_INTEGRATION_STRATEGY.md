# ERC-734/735 Integration Strategy for Fusion Prime

**Date**: November 4, 2025
**Purpose**: Learning-focused, production-ready implementation
**Timeline**: Take time to do it right
**Philosophy**: Build once, build correctly

---

## 🎯 Strategy Overview

### Vision: **Decentralized Identity-First Platform**

Instead of traditional "account → wallet" approach, we'll build **"identity → everything"**:

```
Traditional Web3 App:           Fusion Prime (ERC-734/735):
==================             ==============================

User creates account           User creates identity contract
  ↓                              ↓
Links wallet                   Identity owns wallet(s)
  ↓                              ↓
Completes KYC (off-chain)      Receives on-chain claims
  ↓                              ↓
Backend tracks status          Smart contracts verify claims
  ↓                              ↓
Per-app authorization          Universal authorization
```

---

## 🏗️ Architecture Layers

### Layer 1: Identity Foundation (ERC-734)
**What**: Smart contract representing user's identity
**Purpose**: Key management, identity ownership
**Deployed**: One per user, owned by user

```solidity
Identity Contract {
  Owner: User's wallet
  Keys: {
    Management: User can manage identity
    Action: Wallets that can act on behalf
    Claim: Who can add claims
  }
}
```

### Layer 2: Claims System (ERC-735)
**What**: Verifiable attestations about the identity
**Purpose**: KYC, credentials, permissions
**Issued by**: Trusted claim issuers (Persona, your backend)

```solidity
Claims {
  KYC_VERIFIED: Issued by Persona
  EMAIL_VERIFIED: Issued by Privy
  ACCREDITED_INVESTOR: Issued by compliance provider
  COUNTRY_USA: Issued by KYC provider
}
```

### Layer 3: Application Smart Contracts
**What**: Your DeFi logic (Escrow, Vault, etc.)
**Purpose**: Business logic with identity checks
**Checks**: Verify claims before allowing actions

```solidity
function createEscrow() {
  require(hasKYCClaim(msg.sender), "KYC required");
  // Create escrow
}
```

### Layer 4: Backend Services
**What**: Off-chain orchestration
**Purpose**: Coordinate Privy, Persona, and blockchain
**Role**: Trusted claim issuer, API gateway

### Layer 5: Frontend dApp
**What**: User interface
**Purpose**: Seamless UX for identity, claims, features
**Experience**: Users don't think about complexity

---

## 🔄 Complete User Journey (Step-by-Step)

### Phase 1: First Visit (Identity Creation)

```
┌─────────────────────────────────────────────────────────────┐
│ User visits Fusion Prime for the first time                 │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Authentication (Privy)                              │
├─────────────────────────────────────────────────────────────┤
│ UI: "Welcome to Fusion Prime"                               │
│     [Sign in with Google] [Sign in with Email] [Wallet]     │
│                                                              │
│ User clicks: "Sign in with Google"                          │
│   ↓                                                          │
│ Privy modal opens → Google OAuth                            │
│   ↓                                                          │
│ Success! Privy returns:                                     │
│   - user.id (DID): "did:privy:abc123xyz"                   │
│   - user.email: "user@gmail.com"                           │
│   - user.wallet: Embedded wallet created automatically      │
│   - JWT token                                                │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Check for Identity Contract                         │
├─────────────────────────────────────────────────────────────┤
│ Frontend calls: identityFactory.getIdentity(user.wallet)    │
│                                                              │
│ Result: 0x0000... (No identity yet)                        │
│                                                              │
│ UI: Show welcome screen with explanation                    │
│     "Let's create your decentralized identity"              │
│     [Explanation of what this means]                        │
│     [Create My Identity] button                             │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Create Identity Contract                            │
├─────────────────────────────────────────────────────────────┤
│ User clicks: "Create My Identity"                           │
│   ↓                                                          │
│ Frontend calls smart contract:                              │
│   identityFactory.createIdentity(user.wallet)               │
│   ↓                                                          │
│ MetaMask popup (if using external wallet) or                │
│ Privy embedded wallet signs transaction automatically       │
│   ↓                                                          │
│ Transaction confirmed! ✅                                    │
│   ↓                                                          │
│ Identity contract deployed:                                 │
│   Address: 0xIDENTITY123...                                │
│   Owner: user.wallet                                        │
│   ↓                                                          │
│ Backend stores mapping:                                     │
│   users table: {                                            │
│     privy_did: "did:privy:abc123xyz"                       │
│     wallet_address: "0xUSER..."                            │
│     identity_address: "0xIDENTITY123..."                   │
│     identity_created_at: now()                             │
│   }                                                         │
│   ↓                                                          │
│ UI: "Identity created! 🎉"                                  │
│     Shows: Identity contract address                        │
│     [Continue to Dashboard]                                 │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Initial Dashboard (Limited Access)                  │
├─────────────────────────────────────────────────────────────┤
│ User sees dashboard with:                                   │
│   ✅ Portfolio overview (read-only blockchain data)         │
│   ✅ Cross-chain vault balances                             │
│   ⚠️  Escrow creation (disabled - needs KYC)               │
│   ⚠️  Fiat gateway (disabled - needs KYC)                  │
│                                                              │
│ Banner at top:                                              │
│   "Complete identity verification to unlock all features"   │
│   [Verify Identity]                                         │
└─────────────────────────────────────────────────────────────┘
```

### Phase 2: KYC Process (Claim Issuance)

```
┌─────────────────────────────────────────────────────────────┐
│ User clicks: "Verify Identity" button                       │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Check Existing Claims                               │
├─────────────────────────────────────────────────────────────┤
│ Frontend calls:                                             │
│   identity.hasClaim(KYC_VERIFIED, PERSONA_ISSUER)           │
│                                                              │
│ Result: false (no KYC claim yet)                           │
│                                                              │
│ Proceed to KYC...                                           │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Initiate KYC with Persona                           │
├─────────────────────────────────────────────────────────────┤
│ Frontend calls backend: POST /api/kyc/initiate              │
│   ↓                                                          │
│ Backend:                                                    │
│   1. Creates Persona inquiry                                │
│   2. Returns session token                                  │
│   ↓                                                          │
│ Frontend launches Persona widget                            │
│   ↓                                                          │
│ User completes:                                             │
│   - Upload government ID                                    │
│   - Take selfie                                             │
│   - Confirm personal details                                │
│   ↓                                                          │
│ Persona verifies (2-10 minutes):                            │
│   - Document authenticity                                   │
│   - Liveness check                                          │
│   - AML/sanctions screening                                 │
│   ↓                                                          │
│ Result: ✅ APPROVED or ❌ REJECTED                          │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Persona Webhook (Off-chain → On-chain)             │
├─────────────────────────────────────────────────────────────┤
│ Persona sends webhook to backend:                           │
│   POST /api/webhooks/persona                                │
│   {                                                          │
│     event: "inquiry.completed",                             │
│     status: "approved",                                     │
│     inquiry_id: "inq_123",                                  │
│     reference_id: "did:privy:abc123xyz"                    │
│   }                                                         │
│   ↓                                                          │
│ Backend processes webhook:                                  │
│   1. Validate webhook signature                             │
│   2. Find user by reference_id                              │
│   3. Update database: kyc_status = "approved"               │
│   4. **CREATE AND ISSUE ON-CHAIN CLAIM** ⭐                │
│   ↓                                                          │
│ Backend ClaimService:                                       │
│   claim = createKYCClaim(user):                             │
│     topic: 1 (KYC_VERIFIED)                                 │
│     scheme: 1 (ECDSA)                                       │
│     issuer: BACKEND_ISSUER_ADDRESS                          │
│     data: hash(kyc_inquiry_id + timestamp)                  │
│     signature: sign(claim_data, BACKEND_PRIVATE_KEY)        │
│   ↓                                                          │
│   Issue claim to user's identity contract:                  │
│     identity.addClaim(                                      │
│       topic: 1,                                             │
│       scheme: 1,                                            │
│       issuer: BACKEND_ISSUER_ADDRESS,                       │
│       signature: claim.signature,                           │
│       data: claim.data,                                     │
│       uri: ""                                               │
│     )                                                       │
│   ↓                                                          │
│ Transaction sent to blockchain ⛓️                          │
│ Gas paid by backend issuer account                          │
│   ↓                                                          │
│ Transaction confirmed! ✅                                    │
│ Claim now stored on-chain in user's identity contract       │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Frontend Updates (Real-time)                        │
├─────────────────────────────────────────────────────────────┤
│ Backend sends WebSocket message to frontend:                │
│   {                                                          │
│     type: "KYC_CLAIM_ISSUED",                               │
│     claimId: "0xCLAIM123...",                              │
│     txHash: "0xTX456..."                                   │
│   }                                                         │
│   ↓                                                          │
│ Frontend refreshes user profile:                            │
│   - Calls identity.hasClaim(KYC_VERIFIED, PERSONA_ISSUER)   │
│   - Result: true ✅                                         │
│   ↓                                                          │
│ UI updates:                                                 │
│   ✅ Banner: "Identity verified! 🎉"                        │
│   ✅ Escrow features unlocked                               │
│   ✅ Fiat gateway unlocked                                  │
│   ✅ Badge: "Verified" on user profile                      │
└─────────────────────────────────────────────────────────────┘
```

### Phase 3: Using Features (Claim Verification)

```
┌─────────────────────────────────────────────────────────────┐
│ User wants to create an escrow                              │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Frontend Pre-check (UX Optimization)                │
├─────────────────────────────────────────────────────────────┤
│ Before showing form, frontend checks:                       │
│   identity.hasClaim(KYC_VERIFIED, PERSONA_ISSUER)           │
│   ↓                                                          │
│ Result: true ✅                                             │
│   ↓                                                          │
│ Show escrow creation form                                   │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: User Fills Form                                     │
├─────────────────────────────────────────────────────────────┤
│ User enters:                                                │
│   - Payee address: 0xPAYEE...                              │
│   - Arbiter address: 0xARBITER...                          │
│   - Amount: 1.0 ETH                                         │
│   - Timelock: 1 hour                                        │
│   ↓                                                          │
│ Frontend also checks payee and arbiter:                     │
│   - Do they have identities?                                │
│   - Do they have KYC claims?                                │
│   ↓                                                          │
│ If not: Show warning                                        │
│   "⚠️ Payee is not KYC verified. Transaction may fail."    │
│   [Continue Anyway] [Cancel]                                │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Submit Transaction                                  │
├─────────────────────────────────────────────────────────────┤
│ User clicks: "Create Escrow"                                │
│   ↓                                                          │
│ Frontend calls smart contract:                              │
│   escrowFactory.createEscrow(payee, arbiter, timelock)      │
│   { value: 1 ETH }                                          │
│   ↓                                                          │
│ Smart contract executes:                                    │
│   function createEscrow(...) {                              │
│     // 1. Check payer KYC                                   │
│     require(                                                │
│       isKYCVerified(msg.sender),                           │
│       "Payer not KYC verified"                             │
│     );                                                      │
│                                                              │
│     // 2. Check payee KYC                                   │
│     require(                                                │
│       isKYCVerified(payee),                                │
│       "Payee not KYC verified"                             │
│     );                                                      │
│                                                              │
│     // 3. Check arbiter KYC                                 │
│     require(                                                │
│       isKYCVerified(arbiter),                              │
│       "Arbiter not KYC verified"                           │
│     );                                                      │
│                                                              │
│     // All verified! Create escrow ✅                       │
│     Escrow escrow = new Escrow(...);                       │
│     emit EscrowCreated(address(escrow), msg.sender);        │
│   }                                                         │
│   ↓                                                          │
│ isKYCVerified() helper function:                            │
│   function isKYCVerified(address user) internal view        │
│     returns (bool) {                                        │
│       // Get user's identity                                │
│       address identity = identityFactory.getIdentity(user); │
│       if (identity == address(0)) return false;             │
│                                                              │
│       // Check for KYC claim                                │
│       Identity identityContract = Identity(identity);       │
│       return identityContract.hasClaim(                     │
│         KYC_VERIFIED,                                       │
│         PERSONA_ISSUER                                      │
│       );                                                    │
│     }                                                       │
│   ↓                                                          │
│ Transaction succeeds! ✅                                     │
│ Escrow created at: 0xESCROW789...                          │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Success & Record                                    │
├─────────────────────────────────────────────────────────────┤
│ Frontend receives transaction receipt                       │
│   ↓                                                          │
│ UI shows success:                                           │
│   "Escrow created! 🎉"                                      │
│   Escrow address: 0xESCROW789...                           │
│   [View Escrow Details]                                     │
│   ↓                                                          │
│ Backend indexes event (optional):                           │
│   - Store escrow in database for quick queries              │
│   - Associate with user                                     │
│   - Send notification email                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎨 UI/UX Flow Design

### Onboarding Wizard (First Time Users)

```
┌─────────────────────────────────────────────────────────────┐
│                     STEP 1 OF 4                              │
│                                                              │
│  Welcome to Fusion Prime 🚀                                 │
│  ═══════════════════════════                                │
│                                                              │
│  Fusion Prime uses decentralized identity for security      │
│  and compliance. Let's set up your identity in 4 steps.     │
│                                                              │
│  What you'll need:                                          │
│  ✓ Email or Google account                                  │
│  ✓ Government-issued ID (for verification)                  │
│  ✓ 2-3 minutes                                              │
│                                                              │
│                      [Get Started]                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│                     STEP 2 OF 4                              │
│                                                              │
│  Sign In                                                    │
│  ═══════════                                                │
│                                                              │
│  Choose how you'd like to sign in:                          │
│                                                              │
│  ┌────────────────────────────────────────┐                │
│  │  [G] Continue with Google              │                │
│  └────────────────────────────────────────┘                │
│                                                              │
│  ┌────────────────────────────────────────┐                │
│  │  [@] Continue with Email               │                │
│  └────────────────────────────────────────┘                │
│                                                              │
│  ┌────────────────────────────────────────┐                │
│  │  [W] Connect Wallet                    │                │
│  └────────────────────────────────────────┘                │
│                                                              │
│                      [Back]                                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│                     STEP 3 OF 4                              │
│                                                              │
│  Create Your Identity 🆔                                    │
│  ════════════════════                                       │
│                                                              │
│  We'll create a smart contract that represents your         │
│  identity on the blockchain.                                │
│                                                              │
│  ┌────────────────────────────────────────┐                │
│  │  Your Identity Contract                │                │
│  │                                        │                │
│  │  This contract will:                   │                │
│  │  ✓ Store your credentials              │                │
│  │  ✓ Work across all DeFi platforms      │                │
│  │  ✓ Give you full control               │                │
│  │                                        │                │
│  │  Cost: ~$8-12 (one-time gas fee)       │                │
│  └────────────────────────────────────────┘                │
│                                                              │
│              [Create Identity Contract]                     │
│                      [Back]                                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│                     STEP 4 OF 4                              │
│                                                              │
│  Verify Your Identity ✓                                     │
│  ═══════════════════════                                    │
│                                                              │
│  To comply with regulations, we need to verify your          │
│  identity. This is required for:                            │
│                                                              │
│  ✓ Creating escrows                                         │
│  ✓ Using fiat gateway                                       │
│  ✓ Cross-border transactions                                │
│                                                              │
│  ┌────────────────────────────────────────┐                │
│  │  What you'll need:                     │                │
│  │  • Government ID (passport/license)    │                │
│  │  • Smartphone camera (for selfie)      │                │
│  │  • 5-10 minutes                        │                │
│  │                                        │                │
│  │  Your data is encrypted and secure.    │                │
│  └────────────────────────────────────────┘                │
│                                                              │
│              [Start Verification]                           │
│              [Skip for Now]                                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Dashboard (After Onboarding)

```
┌─────────────────────────────────────────────────────────────┐
│  Fusion Prime                          [🆔 Verified] John    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Identity Status                                      │  │
│  │  ════════════════                                     │  │
│  │                                                        │  │
│  │  Your Identity: 0x1234...5678                         │  │
│  │                                                        │  │
│  │  ✅ KYC Verified                                      │  │
│  │     Verified on: Nov 4, 2025                          │  │
│  │     Issuer: Persona (trusted)                         │  │
│  │                                                        │  │
│  │  ✅ Email Verified                                    │  │
│  │     john@gmail.com                                    │  │
│  │                                                        │  │
│  │  [View on Blockchain] [Manage Claims]                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─────────────────────┐  ┌─────────────────────┐         │
│  │  Create Escrow      │  │  Deposit Funds      │         │
│  │  ✅ Available       │  │  ✅ Available       │         │
│  └─────────────────────┘  └─────────────────────┘         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Implementation Roadmap

### Phase 1: Smart Contracts (Week 1)

**Day 1-2: Core Identity Contracts**
- [ ] Write Identity.sol (ERC-734/735 implementation)
- [ ] Write IERC734.sol, IERC735.sol interfaces
- [ ] Unit tests for Identity contract
- [ ] Deploy to local Hardhat network

**Day 3: Factory & Registry**
- [ ] Write IdentityFactory.sol
- [ ] Write ClaimIssuerRegistry.sol
- [ ] Integration tests
- [ ] Deploy to local network

**Day 4-5: Application Contracts**
- [ ] Update EscrowFactory with identity checks
- [ ] Update CrossChainVault with identity checks
- [ ] Write helper library: IdentityHelper.sol
- [ ] Full test suite

**Day 6-7: Testnet Deployment**
- [ ] Deploy to Sepolia testnet
- [ ] Deploy to Polygon Amoy testnet
- [ ] Verify contracts on Etherscan
- [ ] Register backend as trusted issuer
- [ ] Document contract addresses

### Phase 2: Backend Services (Week 2)

**Day 1-2: Identity Service**
- [ ] Create identity-service/ (FastAPI)
- [ ] Database schema (users, identities, claims)
- [ ] Alembic migrations
- [ ] Web3 integration (contract calls)

**Day 3: Claim Issuance**
- [ ] ClaimService (create & sign claims)
- [ ] Issue claim to blockchain
- [ ] Transaction monitoring
- [ ] Error handling & retries

**Day 4: API Endpoints**
- [ ] POST /identity/create
- [ ] POST /identity/add-claim
- [ ] GET /identity/claims
- [ ] GET /identity/verify
- [ ] Authentication middleware (Privy JWT)

**Day 5: Persona Integration**
- [ ] Update KYC webhook handler
- [ ] Auto-issue claim after KYC approval
- [ ] WebSocket notifications to frontend
- [ ] Audit logging

**Day 6-7: Testing & Deployment**
- [ ] Unit tests
- [ ] Integration tests
- [ ] Deploy to Cloud Run
- [ ] Configure environment variables
- [ ] Health checks & monitoring

### Phase 3: Frontend Integration (Week 3)

**Day 1-2: Identity Hooks**
- [ ] useIdentity hook
- [ ] useIdentityClaims hook
- [ ] useKYCStatus hook
- [ ] Contract interaction helpers

**Day 3: Onboarding Flow**
- [ ] Welcome wizard component
- [ ] Identity creation flow
- [ ] KYC initiation flow
- [ ] Success/error states

**Day 4: Dashboard Updates**
- [ ] Identity status widget
- [ ] Claim display component
- [ ] Verification badge
- [ ] Feature access indicators

**Day 5: Feature Gates**
- [ ] ProtectedFeature component
- [ ] Update escrow UI (check claims)
- [ ] Update vault UI (check claims)
- [ ] Update fiat gateway UI

**Day 6-7: Polish & Testing**
- [ ] Loading states
- [ ] Error handling
- [ ] Responsive design
- [ ] E2E testing

### Phase 4: Integration & Testing (Week 4)

**Day 1-3: End-to-End Testing**
- [ ] Test: Sign in → Create identity → KYC → Claim
- [ ] Test: Create escrow with verified users
- [ ] Test: Try escrow with unverified users
- [ ] Test: Multiple claim types
- [ ] Test: Cross-chain identity

**Day 4-5: Security & Audit**
- [ ] Smart contract security review
- [ ] Backend security audit
- [ ] Frontend security check
- [ ] Penetration testing (claim forgery attempts)

**Day 6-7: Documentation & Launch**
- [ ] User documentation
- [ ] Developer documentation
- [ ] Video tutorials
- [ ] Launch to production

---

## 🔐 Security Considerations

### Claim Issuance Security

**Threats:**
1. Fake claim issuance (attacker issues fake KYC claim)
2. Claim replay (reuse signature)
3. Man-in-the-middle (intercept claim data)

**Mitigations:**
1. **Trusted Issuer Registry**
   - Only whitelisted addresses can issue claims
   - Backend issuer private key secured in HSM/KMS
   - Multi-sig for issuer management

2. **Signature Verification**
   - Claims are signed by trusted issuer
   - Smart contract verifies signature on-chain
   - Includes timestamp to prevent replay

3. **Rate Limiting**
   - Limit claim issuance per user
   - Detect suspicious patterns
   - Manual review for edge cases

### Identity Contract Security

**Threats:**
1. Identity hijacking (steal ownership)
2. Unauthorized claim addition
3. Key compromise

**Mitigations:**
1. **Ownership Protection**
   - Only owner can modify management keys
   - Time-lock for key changes (24 hours)
   - Multi-sig option for high-value identities

2. **Claim Authorization**
   - Only addresses with CLAIM key can add claims
   - Only trusted issuers registered
   - Owner can remove claims

3. **Recovery Mechanism**
   - Social recovery (trusted guardians)
   - Time-locked recovery process
   - Emergency pause function

---

## 📊 Data Architecture

### Database Schema Updates

```sql
-- Users table (updated)
CREATE TABLE users (
  -- Existing fields
  id VARCHAR(255) PRIMARY KEY,
  privy_did VARCHAR(255) UNIQUE,
  wallet_address VARCHAR(255),
  email VARCHAR(255),

  -- NEW: Identity fields
  identity_address VARCHAR(255),           -- ERC-734 contract address
  identity_created_at TIMESTAMP,
  identity_tx_hash VARCHAR(255),

  -- NEW: Claim tracking
  kyc_claim_id VARCHAR(255),               -- On-chain claim ID
  kyc_claim_issued_at TIMESTAMP,
  kyc_claim_tx_hash VARCHAR(255),

  -- Existing KYC fields
  kyc_status VARCHAR(50),
  kyc_inquiry_id VARCHAR(255),
  kyc_verified_at TIMESTAMP
);

-- New: Claims table (off-chain record)
CREATE TABLE claims (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(255) REFERENCES users(id),
  identity_address VARCHAR(255),

  claim_id VARCHAR(255) UNIQUE,            -- On-chain claim ID
  claim_topic INTEGER,                     -- 1=KYC, 2=EMAIL, etc.
  claim_scheme INTEGER,                    -- Signature type
  issuer_address VARCHAR(255),

  signature TEXT,
  data_hash VARCHAR(255),
  uri TEXT,

  tx_hash VARCHAR(255),                    -- Issuance transaction
  block_number BIGINT,

  created_at TIMESTAMP DEFAULT NOW(),
  revoked_at TIMESTAMP,                    -- If claim removed
  revoke_reason TEXT
);

-- New: Identity events (audit trail)
CREATE TABLE identity_events (
  id SERIAL PRIMARY KEY,
  identity_address VARCHAR(255),
  event_type VARCHAR(100),                 -- 'created', 'claim_added', 'claim_removed'
  event_data JSONB,
  tx_hash VARCHAR(255),
  block_number BIGINT,
  timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_claims_user ON claims(user_id);
CREATE INDEX idx_claims_identity ON claims(identity_address);
CREATE INDEX idx_identity_events_address ON identity_events(identity_address);
```

---

## 🎯 Success Metrics

### Technical Metrics

- [ ] **Identity Creation Success Rate**: >95%
- [ ] **Claim Issuance Time**: <30 seconds (off-chain → on-chain)
- [ ] **Identity Verification Checks**: <1 second (read from blockchain)
- [ ] **Gas Costs**: <$15 per user (one-time)
- [ ] **Uptime**: >99.9% for claim issuance service

### User Experience Metrics

- [ ] **Onboarding Completion Rate**: >80%
- [ ] **Time to First Identity**: <5 minutes
- [ ] **Time to KYC Verification**: <10 minutes
- [ ] **User Confusion Rate**: <10% (support tickets)

### Business Metrics

- [ ] **KYC Conversion Rate**: >70% (users who create identity)
- [ ] **Feature Adoption**: >90% use identity-gated features
- [ ] **Cross-platform Portability**: Identity used on >1 platform

---

## 📚 Learning Outcomes

By implementing this system, you'll learn:

### Smart Contract Development
✅ ERC standard implementation (734/735)
✅ Factory pattern for contract deployment
✅ Access control and permissions
✅ On-chain data structures
✅ Event emission and indexing

### Backend Development
✅ Web3 integration (ethers.js/web3.py)
✅ Cryptographic signatures (ECDSA)
✅ Claim creation and verification
✅ Transaction monitoring
✅ WebSocket real-time updates

### Frontend Development
✅ Web3 hooks (wagmi)
✅ Identity UX patterns
✅ Onboarding flows
✅ Real-time blockchain data
✅ Transaction state management

### System Design
✅ Decentralized identity architecture
✅ Off-chain to on-chain synchronization
✅ Multi-layer security
✅ Scalability patterns

---

## 🚀 Ready to Start?

This strategy gives us a **complete roadmap** from concept to production.

**Next Steps:**

1. ✅ Review strategy (you're here)
2. Start Phase 1: Smart Contracts
3. Build incrementally and test thoroughly
4. Deploy to production

**Estimated Timeline**: 4 weeks (taking time to do it right)

**Learning-focused**: Every component explained and documented

---

**Status**: 📋 Strategy Complete - Ready to Implement
**Next**: Shall we start with Phase 1 (Smart Contracts)?
