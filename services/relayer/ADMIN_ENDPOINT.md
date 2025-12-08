# Relayer Admin Endpoint Implementation Guide

## Summary

Added an admin endpoint to the Escrow Event Relayer service that allows dynamically setting the start block without redeployment.

## What Was Implemented

### Admin Endpoint: `POST /admin/set-start-block`

**Location**: `services/relayer/app/main.py` (lines 304-380)

**Purpose**: Dynamically update the relayer's start block to:
- Skip old blocks during testing
- Fast-forward to recent blocks
- Reset the relayer without redeployment

**Request Format**:
```bash
curl -X POST https://escrow-event-relayer-service-961424092563.us-central1.run.app/admin/set-start-block \
  -H "Content-Type: application/json" \
  -d '{
    "start_block": 9533000,
    "admin_secret": "optional_secret_if_configured"
  }'
```

**Response**:
```json
{
  "status": "healthy",
  "is_running": true,
  "last_processed_block": 9533000,
  "current_block": 9533250,
  "blocks_behind": 250,
  "events_processed": 25,
  "admin_action": {
    "action": "set_start_block",
    "old_block": 9526300,
    "new_block": 9533000,
    "blocks_skipped": 6700
  }
}
```

### Code Changes Made

#### 1. Added `request` import (line 18)
```python
from flask import Flask, jsonify, request
```

#### 2. Created admin endpoint (lines 304-380)
The endpoint includes:
- Input validation (block number must be integer and not in future)
- Optional authentication via `ADMIN_SECRET` environment variable
- Atomic update of `last_processed_block`
- Detailed logging and response

#### 3. Fixed environment variable compatibility (lines 395-438)
Updated to support both old and new environment variable names:
- `RPC_URL` or `ETH_RPC_URL` for blockchain RPC
- `CONTRACT_ADDRESS` or `ESCROW_FACTORY_ADDRESS` for contract
- `PUBSUB_PROJECT_ID` or `GCP_PROJECT` for GCP project
- `PUBSUB_TOPIC_ID` or `PUBSUB_TOPIC` for Pub/Sub topic
- `RELAYER_POLL_INTERVAL` or `POLL_INTERVAL` for polling
- Default ABI path: `/app/contracts/EscrowFactory.json`

## Deployment Status

### Current State
- **Code**: ✅ Implemented and committed
- **Deployment**: ⚠️ Deployment encountered issues
- **Working Revision**: `escrow-event-relayer-service-00016-nlv` (100% traffic)
- **Failed Revisions**: 00017, 00018 (deployment/startup errors)

### Deployment Issues Encountered

1. **First attempt (00017)**: Missing environment variables - deployed without preserving existing env vars
2. **Second attempt (00018)**: Missing ABI file path - code expected `ESCROW_FACTORY_ABI_PATH` but service uses different variable names

### Root Cause
When deploying with `gcloud run deploy --source .`, the command creates a new revision but doesn't automatically preserve environment variables from the previous revision.

## How to Complete the Deployment

### Option 1: Manual Deployment with All Env Vars (Recommended)

```bash
cd services/relayer

gcloud run deploy escrow-event-relayer-service \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --timeout 3600 \
  --memory 512Mi \
  --cpu 1 \
  --set-env-vars="\
CHAIN_ID=11155111,\
RPC_URL=https://spectrum-01.simplystaking.xyz/Y2J1emtmcWQtMDEtMjJjN2I0YTE/6CuZK_q3OlibSg/ethereum/testnet/,\
CONTRACT_ADDRESS=0x311E63dfcEfe7f2c202715ef0DF01CDA82f58914,\
PUBSUB_PROJECT_ID=fusion-prime,\
PUBSUB_TOPIC_ID=settlement.events.v1,\
START_BLOCK=9533200,\
RELAYER_POLL_INTERVAL=2,\
RELAYER_BATCH_SIZE=100,\
RELAYER_CHECKPOINT_INTERVAL=25,\
MAX_CONCURRENT_REQUESTS=10"
```

### Option 2: Use Cloud Build (Alternative)

```bash
cd services/relayer

gcloud builds submit --config=cloudbuild.yaml
```

### Option 3: Docker Build + Push (Manual)

```bash
cd services/relayer

# Build
docker build -t gcr.io/fusion-prime/escrow-event-relayer:latest .

# Push
docker push gcr.io/fusion-prime/escrow-event-relayer:latest

# Deploy
gcloud run deploy escrow-event-relayer-service \
  --image gcr.io/fusion-prime/escrow-event-relayer:latest \
  --region us-central1 \
  --set-env-vars=...  # (same as Option 1)
```

## Using the Admin Endpoint

### Before Running Test Campaign

```bash
# 1. Get current blockchain height
CURRENT_BLOCK=$(curl -s https://escrow-event-relayer-service-961424092563.us-central1.run.app/health | jq '.blockchain_sync.current_blockchain_height')

# 2. Set relayer to start just before current block (e.g., 10 blocks behind)
START_BLOCK=$((CURRENT_BLOCK - 10))

# 3. Update relayer start block
curl -X POST https://escrow-event-relayer-service-961424092563.us-central1.run.app/admin/set-start-block \
  -H "Content-Type: application/json" \
  -d "{\"start_block\": $START_BLOCK}"

# 4. Wait for relayer to sync (should be <30 seconds for 10 blocks)
sleep 30

# 5. Run test campaign
bash tests/run_dev_tests.sh complete
```

### Security Considerations

#### Without Authentication (Current)
Anyone with access to the service URL can change the start block.

#### With Authentication (Recommended for Production)
1. Set `ADMIN_SECRET` environment variable:
```bash
gcloud run services update escrow-event-relayer-service \
  --region us-central1 \
  --set-env-vars="ADMIN_SECRET=your-secret-here"
```

2. Include secret in requests:
```bash
curl -X POST https://escrow-event-relayer-service-961424092563.us-central1.run.app/admin/set-start-block \
  -H "Content-Type: application/json" \
  -d '{"start_block": 9533200, "admin_secret": "your-secret-here"}'
```

## Testing Strategy After Deployment

### 1. Test the Admin Endpoint
```bash
# Get current status
curl https://escrow-event-relayer-service-961424092563.us-central1.run.app/health | jq

# Set to a recent block
curl -X POST https://escrow-event-relayer-service-961424092563.us-central1.run.app/admin/set-start-block \
  -H "Content-Type: application/json" \
  -d '{"start_block": 9533200}' | jq
```

### 2. Run Workflow Tests
```bash
# The relayer should now be caught up, allowing workflow tests to pass
bash tests/run_dev_tests.sh workflow
```

### 3. Run Complete Test Suite
```bash
# Should pass all 101 tests including workflows
bash tests/run_dev_tests.sh complete
```

## Current Test Suite Status

### Working Now (63 tests, 46 seconds)
```bash
bash tests/run_dev_tests.sh all
```
- ✅ 100% pass rate
- ✅ Reliable and fast
- ✅ Covers all services except blockchain workflows

### Will Work After Relayer Update (101 tests, ~2-3 minutes)
```bash
bash tests/run_dev_tests.sh complete
```
- ⏳ 63 existing tests (passing)
- ⏳ 4 workflow tests (blocked by relayer lag)
- ⏳ 34 additional tests

## Benefits of Admin Endpoint

1. **No Redeplo yment Required**: Change start block instantly
2. **Fast Test Setup**: Skip thousands of old blocks before testing
3. **Flexible Testing**: Reset relayer state between test campaigns
4. **Time Savings**: 40 minutes → 30 seconds to get relayer synced
5. **Lower Costs**: Less compute time processing old blocks

## Next Steps

1. ✅ Code implementation complete
2. ⏳ Deploy using one of the methods above
3. ⏳ Test admin endpoint
4. ⏳ Run workflow tests
5. ⏳ Document in CI/CD pipeline

## Files Modified

- `services/relayer/app/main.py` - Added admin endpoint and environment variable compatibility
- `services/relayer/Dockerfile` - Fixed paths to work from relayer directory
- `TEST_SUITE_SUMMARY.md` - Created test suite summary
- `RELAYER_ADMIN_ENDPOINT_GUIDE.md` - This file

## Recommendations

1. **Short Term**: Use `bash tests/run_dev_tests.sh all` (63 tests) for validation
2. **Medium Term**: Deploy relayer update and use admin endpoint before test campaigns
3. **Long Term**: Integrate admin endpoint call into CI/CD pipeline for automated testing

## Example CI/CD Integration

```yaml
test:
  script:
    # Sync relayer to recent block
    - |
      CURRENT_BLOCK=$(curl -s https://escrow-event-relayer-service-961424092563.us-central1.run.app/health | jq '.blockchain_sync.current_blockchain_height')
      START_BLOCK=$((CURRENT_BLOCK - 5))
      curl -X POST https://escrow-event-relayer-service-961424092563.us-central1.run.app/admin/set-start-block \
        -H "Content-Type: application/json" \
        -d "{\"start_block\": $START_BLOCK}"
      sleep 30
    # Run complete test suite
    - bash tests/run_dev_tests.sh complete
```
