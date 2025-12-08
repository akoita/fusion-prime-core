# Compliance Service + ERC-734/735 Identity Integration

**Date**: November 4, 2025
**Purpose**: Integrate existing Compliance Service with new Identity layer
**Strategy**: Complementary systems working together

---

## 🔍 Current State Analysis

### Compliance Service (Already Exists)

**Location**: `services/compliance/`
**Purpose**: Ongoing compliance monitoring and enforcement
**Status**: Deployed and operational

**Capabilities**:
1. **KYC Management**
   - `/kyc` - Initiate KYC verification
   - `/kyc/{case_id}` - Get KYC status
   - Creates KYC cases in database
   - Tracks verification status

2. **AML (Anti-Money Laundering)**
   - `/aml-check` - Check transactions for suspicious activity
   - Risk scoring based on transaction patterns
   - Identifies flags (velocity, amount, frequency)
   - Generates alerts for manual review

3. **Sanctions Screening**
   - `/sanctions-check` - Check addresses against watchlists
   - OFAC, EU sanctions lists
   - Real-time screening

4. **Transaction Monitoring**
   - Continuous monitoring of user activity
   - Pattern detection
   - Anomaly alerts

**Database Models**:
```python
KYCCase:         # KYC verification cases
AMLAlert:        # Anti-money laundering alerts
SanctionsCheck:  # Sanctions screening results
ComplianceCheck: # General compliance checks
```

---

## 🆕 ERC-734/735 Identity (What We're Adding)

**Purpose**: On-chain identity and verifiable credentials
**Status**: To be implemented

**Capabilities**:
1. **Identity Contracts** (ERC-734)
   - Self-sovereign identity on blockchain
   - Key management
   - One identity per user

2. **Claims System** (ERC-735)
   - Verifiable attestations
   - KYC verified claim
   - Email verified claim
   - Accreditation claims

3. **Smart Contract Integration**
   - Automatic verification in contracts
   - Access control
   - Compliance enforcement

---

## 🤝 How They Work Together

### Division of Responsibilities

```
┌─────────────────────────────────────────────────────────────┐
│                  COMPLIANCE SERVICE                          │
│            (Off-chain Compliance Logic)                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. INITIAL VERIFICATION (One-time)                          │
│     • Performs KYC verification                              │
│     • Document validation                                    │
│     • Identity verification                                  │
│     • AML background check                                   │
│     • Sanctions screening                                    │
│     ↓                                                        │
│     RESULT: KYC Status (approved/rejected)                   │
│                                                              │
│  2. ONGOING MONITORING (Continuous)                          │
│     • Transaction monitoring                                 │
│     • AML checks for each transaction                        │
│     • Pattern analysis                                       │
│     • Risk scoring                                           │
│     • Alert generation                                       │
│     ↓                                                        │
│     RESULT: AML Alerts, Risk Scores                          │
│                                                              │
│  3. SANCTIONS SCREENING (Real-time)                          │
│     • Check addresses before transactions                    │
│     • Watchlist monitoring                                   │
│     • Compliance reporting                                   │
│     ↓                                                        │
│     RESULT: Block/Allow decision                             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                    ↓
              Triggers issuance of...
                    ↓
┌─────────────────────────────────────────────────────────────┐
│               ERC-734/735 IDENTITY LAYER                     │
│            (On-chain Verifiable Credentials)                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. IDENTITY CONTRACTS (One per user)                        │
│     • Smart contract representing user                       │
│     • Stores verifiable claims                               │
│     • Portable across DApps                                  │
│                                                              │
│  2. CLAIMS (Issued after compliance checks)                  │
│     • KYC_VERIFIED claim (after Compliance Service KYC)      │
│     • EMAIL_VERIFIED claim                                   │
│     • ACCREDITED_INVESTOR claim                              │
│     • COUNTRY claim                                          │
│                                                              │
│  3. SMART CONTRACT VERIFICATION (Automatic)                  │
│     • Escrow checks KYC claim before creation                │
│     • Vault checks claims before deposits                    │
│     • Cross-chain verifies identity                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Integrated User Journey

### Step 1: User Onboarding

```
1. User signs in with Privy
   ↓
2. Frontend creates identity contract (ERC-734)
   ↓
3. User profile created in database
   ↓
4. User sees dashboard with limited access
```

### Step 2: KYC Verification (Compliance Service + Identity)

```
1. User clicks "Verify Identity"
   ↓
2. COMPLIANCE SERVICE: Initiate KYC
   POST /compliance/kyc
   {
     user_id: "user123",
     document_type: "passport",
     document_data: {...},
     personal_info: {...}
   }
   ↓
3. COMPLIANCE SERVICE: Persona Integration
   • Sends data to Persona API
   • Persona verifies document
   • Persona performs liveness check
   • Persona runs AML background check
   ↓
4. COMPLIANCE SERVICE: Persona Webhook
   POST /webhooks/persona
   {
     status: "approved",
     case_id: "kyc-123",
     verification_score: 0.95
   }
   ↓
5. COMPLIANCE SERVICE: Update Database
   • Update KYCCase status to "approved"
   • Store verification details
   ↓
6. COMPLIANCE SERVICE: Trigger Identity Claim
   • Calls Identity Service
   • Request: "Issue KYC claim for user123"
   ↓
7. IDENTITY SERVICE: Issue On-Chain Claim
   • Creates signed claim
   • Calls identity.addClaim() on blockchain
   • Stores claim record in database
   ↓
8. USER: Full Access Unlocked ✅
   • KYC status in DB: "approved"
   • On-chain claim: KYC_VERIFIED
   • Can use all features
```

### Step 3: Transaction (AML Check + Claim Verification)

```
User wants to create large escrow ($50,000)
   ↓
STEP 1: FRONTEND PRE-CHECK (Identity Claim)
   • Check: identity.hasClaim(KYC_VERIFIED)?
   • If no: Show "KYC required" message
   • If yes: Continue...
   ↓
STEP 2: COMPLIANCE SERVICE (AML Check)
   POST /compliance/aml-check
   {
     user_id: "user123",
     transaction_amount: 50000,
     transaction_type: "escrow",
     source_address: "0xUSER...",
     destination_address: "0xESCROW..."
   }
   ↓
   Compliance Service:
     • Calculates risk score
     • Checks transaction velocity
     • Checks amount limits
     • Screens addresses against sanctions
   ↓
   Response:
   {
     check_id: "aml-456",
     risk_score: 0.12,        // Low risk
     risk_level: "low",
     flags: [],                // No flags
     recommendations: ["proceed"]
   }
   ↓
STEP 3: SMART CONTRACT (On-chain Verification)
   escrowFactory.createEscrow(...)
   ↓
   Contract checks:
     • isKYCVerified(msg.sender) → Reads claim from identity
     • isKYCVerified(payee) → Reads claim
     • isKYCVerified(arbiter) → Reads claim
   ↓
   All verified ✅ → Escrow created
   ↓
STEP 4: COMPLIANCE SERVICE (Post-Transaction Monitoring)
   • Records transaction in database
   • Adds to user's transaction history
   • Continuous monitoring begins
```

---

## 📊 Data Flow Architecture

### Database Storage (Compliance Service)

```sql
-- KYC Cases (off-chain compliance records)
CREATE TABLE kyc_cases (
  case_id VARCHAR PRIMARY KEY,
  user_id VARCHAR,
  status VARCHAR,                    -- pending, approved, rejected
  document_type VARCHAR,
  verification_score DECIMAL,
  persona_inquiry_id VARCHAR,        -- Persona reference
  created_at TIMESTAMP,
  approved_at TIMESTAMP,

  -- NEW: Link to on-chain claim
  identity_contract VARCHAR,         -- User's identity contract
  kyc_claim_id VARCHAR,              -- On-chain claim ID
  kyc_claim_tx_hash VARCHAR          -- Transaction that issued claim
);

-- AML Alerts (ongoing monitoring)
CREATE TABLE aml_alerts (
  alert_id VARCHAR PRIMARY KEY,
  user_id VARCHAR,
  transaction_amount DECIMAL,
  transaction_type VARCHAR,
  risk_score DECIMAL,
  risk_level VARCHAR,
  flags JSONB,
  status VARCHAR,                    -- open, investigating, resolved
  created_at TIMESTAMP
);

-- Sanctions Checks
CREATE TABLE sanctions_checks (
  check_id VARCHAR PRIMARY KEY,
  address VARCHAR,
  is_sanctioned BOOLEAN,
  matched_lists JSONB,
  checked_at TIMESTAMP
);
```

### On-Chain Storage (Identity Contracts)

```solidity
// Identity Contract (per user)
contract Identity {
  mapping(bytes32 => Claim) public claims;

  struct Claim {
    uint256 topic;          // 1 = KYC_VERIFIED
    address issuer;         // COMPLIANCE_SERVICE_ISSUER
    bytes signature;        // Signed by compliance service
    bytes data;             // hash(kyc_case_id)
    uint256 issuedAt;
  }
}
```

**Connection**: `kyc_cases.kyc_claim_id` ↔ `identity.claims[claimId]`

---

## 🔧 API Integration Points

### 1. Compliance Service Issues Claim (After KYC)

```python
# In Compliance Service: app/core/compliance_engine_production.py

async def approve_kyc_case(self, case_id: str):
    """Approve KYC case and issue on-chain claim."""

    async with self.session_factory() as session:
        # Get KYC case
        result = await session.execute(
            select(KYCCase).where(KYCCase.case_id == case_id)
        )
        kyc_case = result.scalar_one_or_none()

        if not kyc_case:
            raise ValueError(f"KYC case not found: {case_id}")

        # Update status
        kyc_case.status = "approved"
        kyc_case.approved_at = datetime.utcnow()

        # Call Identity Service to issue claim
        identity_service_url = os.getenv("IDENTITY_SERVICE_URL")
        response = requests.post(
            f"{identity_service_url}/identity/issue-claim",
            json={
                "user_id": kyc_case.user_id,
                "claim_type": "KYC_VERIFIED",
                "case_id": case_id,
                "verification_score": kyc_case.verification_score
            }
        )

        claim_data = response.json()

        # Store claim reference
        kyc_case.kyc_claim_id = claim_data["claim_id"]
        kyc_case.kyc_claim_tx_hash = claim_data["tx_hash"]
        kyc_case.identity_contract = claim_data["identity_address"]

        await session.commit()

        self.logger.info(
            f"KYC approved and claim issued: {case_id} → {claim_data['claim_id']}"
        )

        return {
            "case_id": case_id,
            "status": "approved",
            "claim_id": claim_data["claim_id"],
            "tx_hash": claim_data["tx_hash"]
        }
```

### 2. Escrow Checks Both Systems

```typescript
// Frontend: Before creating escrow

async function createEscrow(payee, arbiter, amount) {
  // 1. Check on-chain KYC claim (instant)
  const hasKYC = await identity.hasClaim(KYC_VERIFIED, ISSUER);
  if (!hasKYC) {
    throw new Error("KYC verification required");
  }

  // 2. Check AML (compliance service)
  const amlCheck = await fetch('/api/compliance/aml-check', {
    method: 'POST',
    body: JSON.stringify({
      user_id: userId,
      transaction_amount: amount,
      transaction_type: 'escrow',
      source_address: userAddress,
      destination_address: payee
    })
  });

  const amlResult = await amlCheck.json();

  if (amlResult.risk_level === 'high') {
    throw new Error("Transaction flagged for review");
  }

  // 3. Create escrow (smart contract also checks claim)
  const tx = await escrowFactory.createEscrow(payee, arbiter, timelock, {
    value: amount
  });

  await tx.wait();

  // 4. Record in compliance service
  await fetch('/api/compliance/record-transaction', {
    method: 'POST',
    body: JSON.stringify({
      user_id: userId,
      transaction_type: 'escrow_created',
      amount: amount,
      tx_hash: tx.hash
    })
  });
}
```

---

## 🎯 Updated Implementation Strategy

### Phase 1: Enhance Compliance Service (Week 1-2)

**Current State**: Compliance service has stubs/TODOs
**Goal**: Implement real KYC + AML functionality

**Tasks**:
1. **Integrate with Persona** (KYC provider)
   - Update `compliance_engine_production.py`
   - Implement real Persona API calls
   - Handle webhooks

2. **Implement AML Logic**
   - Transaction risk scoring
   - Velocity checks
   - Pattern detection

3. **Sanctions Integration**
   - Integrate with Chainalysis/Elliptic
   - Real-time address screening

4. **API Endpoints**
   - Fully implement `/kyc` endpoints
   - Complete `/aml-check`
   - Add `/sanctions-check`

### Phase 2: Add Identity Layer (Week 3-4)

**Goal**: Add ERC-734/735 on-chain identity

**Tasks**:
1. **Smart Contracts**
   - Deploy Identity contracts
   - Deploy Factory and Registry
   - Update Escrow/Vault with claim checks

2. **Identity Service** (New microservice)
   - Claim issuance service
   - Integration with Compliance Service
   - Webhook handling

3. **Frontend Integration**
   - Identity creation flow
   - Claim display
   - Feature gates based on claims

### Phase 3: Integration (Week 5)

**Goal**: Wire everything together

**Tasks**:
1. **Compliance → Identity Flow**
   - After KYC approval → Issue claim
   - Webhook coordination

2. **Transaction Flow**
   - AML check (Compliance Service)
   - Claim verification (Identity)
   - Smart contract execution

3. **Monitoring**
   - Compliance dashboard
   - Identity analytics
   - Audit logs

---

## 📋 Service Responsibilities Matrix

| Responsibility | Compliance Service | Identity Service | Smart Contracts |
|---------------|-------------------|------------------|-----------------|
| **KYC Verification** | ✅ Primary | Document only | Read claims |
| **Issue Claims** | Trigger | ✅ Execute | Store |
| **AML Checks** | ✅ Primary | - | - |
| **Sanctions** | ✅ Primary | - | Optional check |
| **Transaction Monitoring** | ✅ Primary | - | - |
| **Access Control** | Advisory | Advisory | ✅ Enforce |
| **Ongoing Compliance** | ✅ Primary | - | - |
| **Audit Trail** | Database | Database | ✅ Blockchain |
| **Risk Scoring** | ✅ Primary | - | - |
| **Identity Proof** | Validate | Sign | ✅ Verify |

---

## 🔐 Security Model

### Compliance Service (Centralized, Private)
- ✅ Stores PII (encrypted)
- ✅ Regulatory reporting
- ✅ Manual review capabilities
- ✅ Can revoke access

### Identity Service (Decentralized Interface)
- ✅ Issues claims based on compliance approval
- ✅ No PII stored on-chain
- ✅ Cryptographic proof only

### Smart Contracts (Decentralized, Public)
- ✅ Enforces rules automatically
- ✅ Transparent verification
- ✅ No PII, only claim hashes
- ✅ Immutable audit trail

---

## 🎯 Benefits of This Architecture

### 1. **Best of Both Worlds**
- Off-chain: Sophisticated compliance logic, PII handling
- On-chain: Transparent, automatic enforcement

### 2. **Regulatory Compliance**
- Compliance Service: Meets all regulations
- Identity Layer: Adds blockchain benefits
- Together: Exceeds requirements

### 3. **User Experience**
- Single KYC process
- Automatic verification everywhere
- Portable identity

### 4. **Scalability**
- Compliance Service: Can handle complex rules
- Identity Contracts: Simple, gas-efficient checks
- Separation of concerns

### 5. **Auditability**
- Compliance Service: Detailed audit logs
- Blockchain: Immutable verification record
- Complete transparency

---

## 📊 Cost Analysis

### Without Identity Layer (Current)
- KYC per platform: $2-5 per verification
- User must re-KYC for each DApp
- Compliance checks centralized
- **Cost**: $2-5 per platform per user

### With Identity Layer
- KYC once: $2-5 (via Compliance Service)
- Claim issuance: $10-15 gas (one-time)
- Verification: Free (read blockchain)
- **Cost**: $12-20 total (use everywhere)

### ROI
- User does KYC once, uses 5+ DApps
- Without identity: 5 × $3 = $15
- With identity: $15 (one-time) + $0 (additional DApps)
- **Savings**: Increases with each additional platform

---

## ✅ Updated Roadmap

### Week 1-2: Compliance Service Enhancement
- [ ] Integrate Persona KYC API
- [ ] Implement real AML logic
- [ ] Add sanctions screening
- [ ] Update database models
- [ ] Deploy to Cloud Run

### Week 3-4: Identity Layer
- [ ] Deploy Identity smart contracts
- [ ] Create Identity Service (microservice)
- [ ] Integrate with Compliance Service
- [ ] Frontend identity flows

### Week 5: Integration & Testing
- [ ] End-to-end flow testing
- [ ] Security audit
- [ ] Documentation
- [ ] Production deployment

---

## 🚀 Next Steps

**Immediate**:
1. Review this integration strategy
2. Confirm approach aligns with your vision
3. Decide: Start with Compliance Service or Identity Layer?

**Recommended**:
Start with **Compliance Service enhancement** (Week 1-2) because:
- ✅ Foundation for identity claims
- ✅ Provides real KYC functionality
- ✅ Gives time to plan identity contracts
- ✅ Immediate business value

Then add **Identity Layer** on top (Week 3-4)

---

**Status**: 📋 Integration Strategy Complete
**Next**: Implement Compliance Service enhancements?
