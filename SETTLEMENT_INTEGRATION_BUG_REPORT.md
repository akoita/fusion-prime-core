# Settlement Service Integration Bug Report

**Report Date**: 2025-11-01
**Priority**: HIGH
**Status**: INVESTIGATING
**Impact**: End-to-end escrow creation workflow broken

---

## Executive Summary

The Settlement service is unable to process blockchain events from the Relayer service due to missing `event_type` attribute in Pub/Sub messages. This breaks the end-to-end workflow: Blockchain → Relayer → Pub/Sub → Settlement → Database.

**Business Impact**: Real escrow transactions created on the blockchain are NOT being persisted to the database.

---

## Bug Details

### Symptoms
- Test: `test_escrow_creation_workflow` - FAILING
- Error: `Escrow not found in database after 360s timeout`
- Settlement logs: `Detected event_type: '' (empty) - Failed to process Pub/Sub message`

### What's Working ✅
1. Blockchain transactions execute successfully
2. Smart contract events are emitted correctly
3. Relayer publishes messages to Pub/Sub (confirmed in logs)
4. Settlement service receives Pub/Sub messages (confirmed in logs)

### What's Broken ❌
5. **Settlement service receives messages with EMPTY `event_type` attribute**
6. Settlement rejects messages due to missing event type
7. Escrow data is never written to database

---

## Investigation Timeline

### 2025-11-01 01:15 UTC - Initial Discovery
Workflow test failed after 6 minutes waiting for database record.

### 2025-11-01 01:47-01:51 UTC - Log Analysis
**Relayer Logs** (✅ Publishing):
```
2025-11-01 01:15:54 - Published EscrowDeployed to Pub/Sub
  message_id: 16767734457819721
  escrow: 0x628ae77ae29ac51bfc2ee9683b777a34805df287
```

**Settlement Logs** (❌ Receiving but rejecting):
```
2025-11-01 01:51:56 - Received Pub/Sub message
2025-11-01 01:51:56 - Detected event_type: ''
2025-11-01 01:51:56 - Failed to process Pub/Sub message:
                       Error parsing message with type 'fusionprime.settlement.v1.SettlementEvent'
```

### 2025-11-01 02:10 UTC - Code Review
**Relayer Code** (services/relayer/app/main.py:170-174):
```python
future = self.publisher.publish(
    self.topic_path,
    message_data,
    event_type=event_type,  # This should be "EscrowDeployed"
)
```

Code appears correct - using standard Pub/Sub Python client syntax.

### 2025-11-01 02:12 UTC - Pub/Sub Client Test
Created test script (`/tmp/test_pubsub_attrs.py`) to verify Pub/Sub attribute transmission.

**Result**: ✅ **Published successfully** with `event_type="EscrowDeployed"` as keyword argument.

Message IDs:
- 16708705607001260 (single attribute)
- 16709917008198977 (multiple attributes)

**Conclusion**: The Pub/Sub Python client DOES support the syntax used in relayer code.

---

## Root Cause Analysis

### Hypothesis 1: Deployed Code Mismatch ⚠️
**Theory**: The deployed relayer service may be running older code without the `event_type` attribute.

**Evidence**:
- Latest git commits show event_type attribute in code (services/relayer/app/main.py:173)
- Deployed revision: escrow-event-relayer-service-00024-bzs (2025-10-31 23:49 UTC)
- Commits after that time exist with admin endpoint changes

**Likelihood**: HIGH - Code was modified after last deployment

### Hypothesis 2: Attribute Stripping in Transit
**Theory**: Something between publish and receipt is stripping the attribute.

**Evidence Against**:
- Test messages published manually were also stripped
- Pub/Sub client test confirms attribute transmission works

**Likelihood**: LOW

### Hypothesis 3: Subscription Filter Issue
**Theory**: Pub/Sub subscription configuration may not preserve attributes.

**Evidence**: Not yet investigated

**Likelihood**: MEDIUM

---

## Recommended Fix

### Option 1: Redeploy Relayer Service (RECOMMENDED)
Ensure the latest code with `event_type` attribute is deployed.

```bash
# From repository root
gcloud builds submit --config services/relayer/cloudbuild.yaml \
  --region=us-central1 \
  --project=fusion-prime
```

**Expected Outcome**: Settlement starts receiving `event_type` attribute correctly.

### Option 2: Add Explicit Logging
Add logging to relayer to confirm what attributes are being sent:

```python
logger.info(f"Publishing with attributes: event_type={event_type}")
future = self.publisher.publish(
    self.topic_path,
    message_data,
    event_type=event_type,
)
```

### Option 3: Investigate Deployed Code
Pull the actual running container and inspect the code:

```bash
gcloud run revisions describe escrow-event-relayer-service-00024-bzs \
  --region=us-central1 \
  --project=fusion-prime \
  --format="value(spec.containers[0].image)"
```

---

## Workaround

Until fixed, escrow data must be manually inserted or retrieved directly from blockchain:

```python
# Workaround: Query blockchain directly instead of database
from web3 import Web3
w3 = Web3(Web3.HTTPProvider(RPC_URL))
escrow_contract = w3.eth.contract(address=escrow_address, abi=ESCROW_ABI)
# Read state directly from chain
```

---

## Test Results

### Before Fix
- **Total Tests**: 86
- **Passing**: 84 (97.7%)
- **Failing**: 2
  - `test_escrow_creation_workflow` ❌
  - `test_relayer_caught_up_with_blockchain` ❌ (FIXED separately)

### After Relayer Readiness Fix
- **Total Tests**: 86
- **Passing**: 85 (98.8%)
- **Failing**: 1
  - `test_escrow_creation_workflow` ❌ (this bug)

---

## Next Steps

1. **Immediate**: Redeploy relayer service with latest code
2. **Verify**: Run test suite to confirm workflow test passes
3. **Monitor**: Check Settlement logs for successful `event_type` receipt
4. **Document**: Update this report with resolution details

---

## Related Files

- Relayer code: `services/relayer/app/main.py` (line 170-174)
- Test failing: `tests/test_escrow_creation_workflow.py`
- Test utilities: `tests/common/database_validation_utils.py`
- Pub/Sub test: `/tmp/test_pubsub_attrs.py`

---

## References

- Google Cloud Pub/Sub Python Client: https://cloud.google.com/python/docs/reference/pubsub/latest
- Test output: `/tmp/wrapper_test_results.txt`
- Relayer logs: `gcloud logging read 'resource.labels.service_name="escrow-event-relayer-service"'`
- Settlement logs: `gcloud logging read 'resource.labels.service_name="settlement-service"'`
