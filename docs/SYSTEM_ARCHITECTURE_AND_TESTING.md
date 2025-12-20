# 🏗️ Fusion Prime - System Architecture & Testing Guide

**Purpose**: Comprehensive guide to Fusion Prime architecture and testing strategy
**Audience**: Developers, QA Engineers, DevOps
**Last Updated**: 2025-01-25

---

## 🎯 **System Overview**

Fusion Prime is a cross-chain digital asset treasury and settlement platform that combines:
- **Smart Contract Wallets** with escrow functionality
- **Cross-Chain Liquidity** aggregation
- **Prime Brokerage Services** (borrowing, lending, OTC settlement)
- **Institutional Compliance** (KYC/KYB, AML)

---

## 🏛️ **Architecture**

### **Component Diagram**

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FUSION PRIME PLATFORM                        │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                          SMART CONTRACT LAYER                         │
├──────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │   Escrow     │────│  Escrow      │────│  Events      │          │
│  │  Contract    │    │  Factory     │    │  (on-chain)  │          │
│  └──────────────┘    └──────────────┘    └──────────────┘          │
└──────────────────────────────────────────────────────────────────────┘
                                │
                                │ Events (EscrowCreated, EscrowReleased)
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        EVENT RELAYER LAYER                            │
├──────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │   Event      │────│  Checkpoint  │────│   Pub/Sub    │          │
│  │  Relayer     │    │    Store     │    │  Publisher   │          │
│  └──────────────┘    └──────────────┘    └──────────────┘          │
└──────────────────────────────────────────────────────────────────────┘
                                │
                                │ Messages (settlement.events.v1)
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         MESSAGING LAYER                               │
├──────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────┐          │
│  │              Google Cloud Pub/Sub                       │          │
│  │  Topic: settlement.events.v1                           │          │
│  └────────────────────────────────────────────────────────┘          │
└──────────────────────────────────────────────────────────────────────┘
                                │
                                │ Async Messages
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      MICROSERVICES LAYER                              │
├──────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  Settlement  │  │  Risk Engine │  │  Compliance  │              │
│  │   Service    │  │   Service    │  │   Service    │              │
│  │              │  │              │  │              │              │
│  │ • Commands   │  │ • Risk Calc  │  │ • KYC/AML   │              │
│  │ • Status     │  │ • Analytics  │  │ • Identity  │              │
│  │ • Webhooks   │  │ • Margin     │  │ • Cases     │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└──────────────────────────────────────────────────────────────────────┘
                                │
                                │ Persistence
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                                    │
├──────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  Cloud SQL   │  │  Checkpoint  │  │   BigQuery   │              │
│  │ (PostgreSQL) │  │    Store     │  │  (Analytics) │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 **Data Flow**

### **Complete End-to-End Workflow**

```
┌─────────────────────────────────────────────────────────────────────┐
│                  STEP 1: USER CREATES ESCROW                         │
└─────────────────────────────────────────────────────────────────────┘
         │
         │ User calls EscrowFactory.createEscrow()
         │ - Deploys new Escrow contract
         │ - Locks funds in escrow
         │ - Emits EscrowCreated event
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│             STEP 2: EVENT RELAYER DETECTS EVENT                      │
└─────────────────────────────────────────────────────────────────────┘
         │
         │ Event Relayer:
         │ - Polls blockchain for new events
         │ - Detects EscrowCreated event
         │ - Extracts event data (payer, payee, amount, escrow address)
         │ - Saves checkpoint (last processed block)
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│          STEP 3: RELAYER PUBLISHES TO PUB/SUB                       │
└─────────────────────────────────────────────────────────────────────┘
         │
         │ Pub/Sub Message:
         │ {
         │   "event_type": "EscrowCreated",
         │   "chain_id": 11155111,
         │   "contract_address": "0x...",
         │   "escrow_address": "0x...",
         │   "payer": "0x...",
         │   "payee": "0x...",
         │   "amount": "1000000000000000000",
         │   "block_number": 12345,
         │   "transaction_hash": "0x..."
         │ }
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│          STEP 4: SETTLEMENT SERVICE CONSUMES MESSAGE                 │
└─────────────────────────────────────────────────────────────────────┘
         │
         │ Settlement Service:
         │ - Subscribes to settlement.events.v1
         │ - Receives Pub/Sub message
         │ - Processes event handler
         │ - Updates command status in database
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│       STEP 5: SETTLEMENT SERVICE STORES COMMAND                      │
└─────────────────────────────────────────────────────────────────────┘
         │
         │ Database Record:
         │ - command_id: unique identifier
         │ - workflow_id: settlement workflow
         │ - status: "pending" → "processing" → "completed"
         │ - payer/payee addresses
         │ - amount and asset
         │ - chain_id
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│         STEP 6: RISK ENGINE VALIDATES PARAMETERS                     │
└─────────────────────────────────────────────────────────────────────┘
         │
         │ Risk Engine calculates:
         │ - Portfolio risk exposure
         │ - Margin requirements
         │ - Collateral valuation
         │ - Liquidation thresholds
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│          STEP 7: COMPLIANCE SERVICE CHECKS KYC/AML                   │
└─────────────────────────────────────────────────────────────────────┘
         │
         │ Compliance Service:
         │ - Validates payer/payee KYC status
         │ - Runs AML checks
         │ - Verifies transaction limits
         │ - Creates case if needed
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│           STEP 8: SETTLEMENT IS PROCESSED                            │
└─────────────────────────────────────────────────────────────────────┘
         │
         │ Settlement Service:
         │ - Updates command status to "completed"
         │ - Triggers webhooks/notifications
         │ - Records final state
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│              STEP 9: USER RECEIVES CONFIRMATION                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🧪 **Testing Strategy**

### **Test Pyramid**

```
                    ┌─────────────┐
                    │  End-to-End │
                    │    Tests    │
                    └─────────────┘
                  ┌───────────────────┐
                  │  Integration Tests│
                  │   (Remote/Local)  │
                  └───────────────────┘
              ┌───────────────────────────┐
              │     Service Tests         │
              │  (API, Health, Commands)  │
              └───────────────────────────┘
          ┌─────────────────────────────────────┐
          │         Unit Tests                  │
          │  (Domain Logic, Utilities, Models)  │
          └─────────────────────────────────────┘
```

### **Test Categories**

| Category | Location | Purpose | Duration |
|----------|----------|---------|----------|
| **Unit Tests** | `services/*/tests/` | Test individual functions and classes | ~30 seconds |
| **Integration Tests** | `tests/local/` | Test service interactions locally | ~5 minutes |
| **Remote Tests** | `tests/remote/testnet/` | Test deployed services on testnet | ~10 minutes |
| **E2E Tests** | `tests/remote/testnet/` | Test complete user workflows | ~15 minutes |

---

## 📋 **Test Scenarios**

### **1. Blockchain Connectivity Tests**

**File**: `test_system_integration.py::test_blockchain_connectivity`

**What it tests**:
- Web3 connection to RPC endpoint
- Latest block number retrieval
- Chain ID verification
- Gas price querying

**Why it's important**:
- Ensures blockchain layer is accessible
- Validates RPC configuration
- Confirms network connectivity

---

### **2. Smart Contract Verification Tests**

**File**: `test_system_integration.py::test_contract_verification`

**What it tests**:
- Contract code exists at deployed address
- Contract is properly deployed
- Contract size and validity

**Why it's important**:
- Confirms smart contracts are deployed
- Validates contract addresses
- Ensures contracts are functional

---

### **3. Service Health Tests**

**Files**: Multiple test methods for each service

**What it tests**:
- Settlement Service: `/health` endpoint returns 200
- Risk Engine Service: `/health/` endpoint returns 200 or degraded
- Compliance Service: `/health/` endpoint returns 200 or degraded
- Event Relayer: `/health` endpoint returns 200 or degraded

**Why it's important**:
- Confirms all services are deployed and running
- Validates service availability
- Handles degraded mode gracefully (services with mock implementations)

**Degraded Mode**:
- Services may run in degraded mode when external dependencies are unavailable
- Risk Engine uses mock implementations when Redis/BigQuery are unavailable
- Compliance uses SQLite when PostgreSQL is unavailable
- Relayer may not initialize if blockchain/Pub/Sub is unavailable
- Tests accept both "healthy" and "degraded" status

---

### **4. API Endpoint Tests**

**File**: `test_system_integration.py::test_settlement_service_connectivity`

**What it tests**:
- Settlement Service `/commands/ingest` endpoint
- Command validation and acceptance
- Response format and status codes

**Why it's important**:
- Validates core API functionality
- Tests command ingestion pipeline
- Ensures data persistence works

**Test Flow**:
```python
1. Create test command with valid data
2. POST to /commands/ingest
3. Expect 202 Accepted
4. Verify command_id in response
5. Confirm status is "accepted"
```

---

### **5. Service Integration Readiness Tests**

**File**: `test_system_integration.py::test_end_to_end_workflow`

**What it tests**:
- All services are available
- Core services (Settlement, Risk Engine, Compliance) are operational
- Services can communicate

**Why it's important**:
- Validates system-wide readiness
- Confirms all components are deployed
- Ensures integration is possible

---

### **6. Complete Workflow Simulation**

**File**: `test_system_integration.py::test_end_to_end_workflow`

**What it tests**:
Complete end-to-end workflow:
1. Blockchain connectivity
2. Event Relayer status
3. Settlement Service command processing
4. Risk Engine validation
5. Compliance validation
6. Overall system integration

**Why it's important**:
- Validates complete user journey
- Tests all components together
- Confirms system works end-to-end
- Identifies integration issues

**Test Flow**:
```
1️⃣  Verify blockchain is connected
2️⃣  Check Event Relayer is operational (or degraded)
3️⃣  Publish event to Pub/Sub (simulated)
4️⃣  Submit command to Settlement Service
5️⃣  Verify command is accepted and stored
6️⃣  Check Risk Engine can validate
7️⃣  Check Compliance can validate
8️⃣  Confirm all components are working
```

---


---
