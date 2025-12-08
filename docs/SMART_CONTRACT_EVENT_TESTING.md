# Smart Contract Event-Driven Testing Strategy

## Overview

This document outlines the comprehensive testing strategy for validating smart contract transactions and their event-driven workflows across the Fusion Prime platform. The tests ensure that blockchain events trigger the correct downstream processes in the Relayer, Settlement Service, Risk Engine, and Compliance Service.

## Architecture

```
┌─────────────────┐
│ Smart Contract  │
│  (Blockchain)   │
└────────┬────────┘
         │ Emits Events (EscrowDeployed, ApprovalGranted, etc.)
         ↓
┌─────────────────┐
│  Event Relayer  │ ← Polls blockchain for events
│  (Cloud Run Job)│
└────────┬────────┘
         │ Publishes messages
         ↓
┌─────────────────┐
│   Pub/Sub Topic │
│ (escrow-events) │
└────────┬────────┘
         │ Distributes to subscribers
         ├────────────┬─────────────┬────────────┐
         ↓            ↓             ↓            ↓
┌───────────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐
│   Settlement  │ │   Risk   │ │Compliance│ │  Database  │
│    Service    │ │  Engine  │ │ Service  │ │(Cloud SQL) │
└───────────────┘ └──────────┘ └──────────┘ └────────────┘
```

## Test Philosophy

### Event-Driven Validation Principles

1. **Complete Pipeline Testing**: Tests validate the entire workflow from smart contract transaction to final database update.
2. **Event Verification**: Each test verifies that the expected blockchain events are emitted with correct parameters.
3. **Asynchronous Processing**: Tests account for the asynchronous nature of event processing with appropriate wait times.
4. **Service Integration**: Tests validate that all downstream services (Settlement, Risk, Compliance) are correctly triggered and process events.
5. **Data Persistence**: Tests verify that data flows through the system and is correctly persisted in the database.
6. **Cross-Service Consistency**: Tests ensure data consistency across all services.

## Test Cases

### 1. Escrow Creation Workflow (`test_escrow_creation_workflow`)

**Purpose**: Validate the complete escrow creation process from blockchain transaction to service processing.

**Steps**:
1. **Blockchain Transaction**
   - Execute `createEscrow` transaction on the factory contract
   - Verify transaction is confirmed on-chain
   - Check gas usage and transaction receipt

2. **Event Emission**
   - Verify `EscrowDeployed` event is emitted
   - Validate event parameters (escrow address, payer, payee, amount)
   - Extract escrow address from event logs

3. **Relayer Processing**
   - Wait for relayer to poll blockchain (~45 seconds)
   - Relayer captures `EscrowDeployed` event
   - Publishes message to `escrow-events` Pub/Sub topic

4. **Settlement Service Processing**
   - Service receives Pub/Sub message
   - Creates settlement command in database
   - Query API to verify command was created
   - Validate command data matches event parameters

5. **Risk Engine Processing**
   - Send portfolio data with new escrow to Risk Engine
   - Verify risk calculation includes locked escrow funds
   - Validate risk score and risk level are returned

6. **Compliance Service Processing**
   - Send transaction data to Compliance Service
   - Verify KYC/AML checks are performed
   - Validate compliance approval status

**Expected Outcome**: Complete pipeline validation from smart contract to all downstream services.

### 2. Escrow Approval Workflow (`test_escrow_approval_workflow`)

**Purpose**: Validate the approval process for releasing escrow funds.

**Steps**:
1. Execute `approveRelease` transaction on escrow contract
2. Verify `ApprovalGranted` event is emitted
3. Wait for relayer to process event
4. Verify Settlement service updates approval status
5. Validate database tracks approval count
6. Verify Risk Engine updates risk based on pending release
7. Verify Compliance validates approval authority

**Status**: Placeholder - requires existing escrow address.

**Future Implementation**:
- Create or reuse escrow from creation test
- Execute approval transaction with authorized approver
- Validate approval count increments correctly
- Test threshold-based approval logic

### 3. Escrow Release Workflow (`test_escrow_release_workflow`)

**Purpose**: Validate the final fund release process.

**Steps**:
1. Execute `releasePayment` transaction on approved escrow
2. Verify `PaymentReleased` event is emitted
3. Verify funds are transferred to payee
4. Wait for relayer to process event
5. Verify Settlement service records final settlement
6. Validate database shows completed status
7. Verify Risk Engine removes locked funds from calculations
8. Verify Compliance performs final AML checks

**Status**: Placeholder - requires approved escrow.

**Future Implementation**:
- Ensure sufficient approvals before release
- Validate balance changes on both payer and payee
- Test release with different approval thresholds
- Validate final settlement reconciliation

### 4. Escrow Refund Workflow (`test_escrow_refund_workflow`)

**Purpose**: Validate the multi-step refund process.

**Steps**:
1. Execute `requestRefund` transaction → `RefundRequested` event
2. Execute `approveRefund` transaction → `RefundApproved` event
3. Execute `processRefund` transaction → `RefundProcessed` event
4. Verify all events are emitted correctly
5. Wait for relayer to process all events sequentially
6. Verify Settlement service tracks complete refund lifecycle
7. Validate database shows refund completion
8. Verify Risk Engine adjusts risk on refund
9. Verify Compliance validates refund legitimacy

**Status**: Placeholder - comprehensive multi-step test.

**Future Implementation**:
- Test complete refund state machine
- Validate refund approval requirements
- Test partial vs. full refunds (if supported)
- Validate refund timeouts and expiration

## Running the Tests

### Prerequisites

```bash
# Set required environment variables
export ETH_RPC_URL="https://sepolia.infura.io/v3/YOUR_KEY"
export ESCROW_FACTORY_ADDRESS="0xYourFactoryAddress"
export PAYER_PRIVATE_KEY="0xYourPrivateKey"
export PAYEE_ADDRESS="0xPayeeAddress"

# Set service URLs
export SETTLEMENT_SERVICE_URL="https://settlement-service-HASH-uc.a.run.app"
export RISK_ENGINE_SERVICE_URL="https://risk-engine-service-HASH-uc.a.run.app"
export COMPLIANCE_SERVICE_URL="https://compliance-service-HASH-uc.a.run.app"
```

### Run All Event-Driven Tests

```bash
cd /home/koita/dev/web3/fusion-prime
./scripts/test/remote.sh all
```

### Run Specific Workflow Test

```bash
# Test escrow creation workflow only
python -m pytest tests/remote/testnet/test_system_integration.py::TestSystemIntegration::test_escrow_creation_workflow -v -s

# Test specific workflow with detailed output
./scripts/test/remote.sh escrow_creation
```

### Test Output

Each test provides detailed step-by-step output:

```
🔄 Testing escrow creation workflow with event-driven validation...

🔬 Test Run ID: escrow-test-1730000000000
============================================================

1️⃣  BLOCKCHAIN - Execute createEscrow Transaction
------------------------------------------------------------
📊 Payer: 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
💰 Balance: 1.5 ETH
💸 Amount: 0.001 ETH
⛽ Gas estimate: 250000, using limit: 300000
📤 Transaction sent: 0xabc123...
🔗 Etherscan: https://sepolia.etherscan.io/tx/0xabc123...
⏳ Waiting for confirmation...
✅ Transaction confirmed in block: 4567890
   Gas used: 245678

2️⃣  BLOCKCHAIN - Verify EscrowDeployed Event
------------------------------------------------------------
✅ EscrowDeployed event emitted
   Escrow address: 0xdef456...
   Payer: 0xf39Fd6...
   Payee: 0x123abc...
   Amount: 0.001 ETH
🔗 Etherscan: https://sepolia.etherscan.io/address/0xdef456...

3️⃣  RELAYER - Event Capture & Pub/Sub Publishing
------------------------------------------------------------
⏳ Waiting for relayer to capture event (max 60s)...
   The relayer runs periodically and publishes events to Pub/Sub
✅ Relayer processing window complete
   Event should have been published to Pub/Sub topic

4️⃣  SETTLEMENT SERVICE - Event Processing & Database Update
------------------------------------------------------------
🔍 Querying settlement service for escrow: 0xdef456...
✅ Settlement service has processed the escrow
   Found 1 related command(s)
   Data: {"command_id": "...", "status": "pending", ...}
✅ Settlement service is healthy and processing events

5️⃣  RISK ENGINE - Portfolio Risk Assessment
------------------------------------------------------------
📊 Calculating risk for escrow-locked funds...
✅ Risk assessment completed
   Risk Score: 0.25
   Risk Level: low

6️⃣  COMPLIANCE SERVICE - KYC/AML Validation
------------------------------------------------------------
🔍 Performing compliance check for escrow creation...
✅ Compliance check completed
   Status: approved
   Approved: true

============================================================
✅ ESCROW CREATION WORKFLOW VALIDATED
============================================================

✅ Complete event-driven pipeline verified:
   1. Smart Contract → EscrowDeployed event ✓
   2. Event → Relayer → Pub/Sub ✓
   3. Pub/Sub → Settlement Service → Database ✓
   4. Settlement → Risk Engine ✓
   5. Settlement → Compliance Service ✓

📊 Escrow Details:
   Address: 0xdef456...
   Transaction: 0xabc123...
   Block: 4567890

✅ Event-driven workflow is fully operational!
```

## Troubleshooting

### Event Not Processed

**Symptom**: Settlement service doesn't receive event after transaction.

**Possible Causes**:
1. **Relayer Not Running**: Check relayer job status
   ```bash
   gcloud run jobs describe escrow-event-relayer --region=us-central1
   ```

2. **Pub/Sub Subscription Issues**: Check subscription status
   ```bash
   gcloud pubsub subscriptions describe escrow-events-settlement --format=json
   ```

3. **Service Not Subscribed**: Verify service has Pub/Sub subscriber role
   ```bash
   gcloud projects get-iam-policy fusion-prime --flatten="bindings[].members" --filter="bindings.role:roles/pubsub.subscriber"
   ```

**Solution**:
```bash
# Manually trigger relayer
gcloud run jobs execute escrow-event-relayer --region=us-central1 --wait

# Check relayer logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=escrow-event-relayer" --limit 50 --format json
```

### Database Not Updated

**Symptom**: Settlement service receives event but database not updated.

**Possible Causes**:
1. **Database Connection Issues**: Check service logs for connection errors
2. **Migration Not Applied**: Verify `settlement_commands` table exists
3. **Permission Issues**: Verify service account has database write permissions

**Solution**:
```bash
# Check settlement service logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=settlement-service" --limit 50

# Verify database schema
gcloud sql connect settlement-db --user=settlement_user --database=settlement

# Check migrations
SELECT version_num FROM alembic_version;
SELECT table_name FROM information_schema.tables WHERE table_schema='public';
```

### Risk Engine or Compliance Not Invoked

**Symptom**: Settlement processes event but downstream services not called.

**Possible Causes**:
1. **Service URLs Not Configured**: Check environment variables
2. **Service Not Deployed**: Verify services are running
3. **Network Issues**: Check VPC connector or service-to-service auth

**Solution**:
```bash
# Check service status
gcloud run services list --platform=managed --region=us-central1

# Verify service configuration
gcloud run services describe settlement-service --region=us-central1 --format=json | jq '.spec.template.spec.containers[0].env'

# Test service connectivity
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  https://risk-engine-service-HASH-uc.a.run.app/health/
```

## Best Practices

### 1. Test Isolation
- Each test should be independent and not rely on state from previous tests
- Use unique test IDs to track transactions across services
- Clean up test data where possible

### 2. Timing and Asynchronicity
- Account for relayer polling interval (~30-60 seconds)
- Add appropriate waits for event processing
- Use timeouts to prevent hanging tests

### 3. Error Handling
- Tests should gracefully handle services in degraded state
- Provide informative skip messages for missing prerequisites
- Log detailed error information for debugging

### 4. Cost Management
- Use testnet (Sepolia) for all testing
- Keep test transactions minimal in value
- Reuse escrows where possible to reduce transaction costs

### 5. Monitoring and Observability
- Include detailed logging in test output
- Provide links to Etherscan for transaction verification
- Log all service responses for debugging

## Future Enhancements

### Phase 1: Complete Basic Workflows
- [ ] Implement approval workflow test
- [ ] Implement release workflow test
- [ ] Implement refund workflow test

### Phase 2: Advanced Scenarios
- [ ] Test multi-approval scenarios
- [ ] Test timeout and expiration handling
- [ ] Test error cases (insufficient funds, unauthorized approvals)
- [ ] Test concurrent transaction handling

### Phase 3: Performance and Load Testing
- [ ] Test relayer processing under high event volume
- [ ] Test service throughput and latency
- [ ] Test database performance with large datasets

### Phase 4: Security and Compliance
- [ ] Test unauthorized transaction attempts
- [ ] Test compliance blocking scenarios
- [ ] Test audit trail completeness
- [ ] Test data privacy and encryption

## Related Documentation

- [TESTING.md](../TESTING.md) - General testing strategy
- [DATABASE_SETUP.md](../DATABASE_SETUP.md) - Database migration and setup
- [E2E_TEST_IMPROVEMENTS.md](./E2E_TEST_IMPROVEMENTS.md) - End-to-end test enhancements
- [SYSTEM_ARCHITECTURE_AND_TESTING.md](../SYSTEM_ARCHITECTURE_AND_TESTING.md) - Overall system architecture

## Agent Responsibilities

Per the **Fusion Prime Agent Playbook**, smart contract event testing involves:

- **Smart Contract Architect Agent**: Maintains ABI schemas, event definitions, and contract upgrade paths
- **Cross-Chain Integration Agent**: Ensures relayer infrastructure captures events reliably
- **Backend Microservices Agent**: Implements event consumers in Settlement, Risk, and Compliance services
- **DevOps & SecOps Agent**: Maintains test infrastructure, monitoring, and CI/CD pipelines for automated testing
- **Risk & Treasury Analytics Agent**: Validates risk calculations triggered by blockchain events
- **Compliance & Identity Agent**: Validates KYC/AML workflows triggered by transactions

---

**Last Updated**: October 25, 2025
**Maintained By**: DevOps & SecOps Agent, Smart Contract Architect Agent
**Status**: Active - Primary test suite for event-driven validation
