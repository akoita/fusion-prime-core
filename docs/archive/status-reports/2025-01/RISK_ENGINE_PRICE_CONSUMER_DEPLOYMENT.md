# Risk Engine Price Consumer Deployment Summary

**Date**: 2025-10-29
**Status**: ⚠️ Partially Complete - Service Deployed, Price Consumer Not Active

---

## Overview

This document summarizes the deployment of the Risk Engine service with the new Price Consumer functionality for receiving real-time market price updates from the Price Oracle Service via Pub/Sub.

---

## Implementation Summary

### Code Changes (Previously Committed)

**Files Created**:
- `services/risk-engine/app/infrastructure/consumers/price_consumer.py` - Pub/Sub consumer for price updates

**Files Modified**:
- `services/risk-engine/app/infrastructure/consumers/__init__.py` - Added price consumer exports
- `services/risk-engine/app/main.py` - Integrated price consumer in lifespan
- `services/risk-engine/cloudbuild.yaml` - Fixed substitution variables and removed dir directive
- `.env.dev` - Added PRICE_ORACLE_URL environment variable

### GCP Infrastructure (Previously Created)

**Pub/Sub Resources**:
```bash
Subscription: risk-engine-prices-consumer
Topic: market.prices.v1
ACK Deadline: 60s
IAM: risk-service@fusion-prime.iam.gserviceaccount.com (roles/pubsub.subscriber)
```

---

## Deployment Process

### Build and Deploy

**Build ID**: `0dbf223d-04fd-46b6-b0f6-5f2da03b18e8`
**Status**: SUCCESS
**Duration**: 3 minutes 46 seconds
**Started**: 2025-10-29T21:12:54+00:00

**Deployment Steps**:
1. Fixed cloudbuild.yaml substitution issues
2. Deployed Docker image to Artifact Registry
3. Deployed to Cloud Run service: `risk-engine-service`

### Configuration Changes

**Current Revision**: `risk-engine-service-00005-7f2`

**Environment Variables**:
```bash
ENVIRONMENT=dev
GCP_PROJECT=fusion-prime
PRICE_ORACLE_URL=https://price-oracle-service-961424092563.us-central1.run.app
PRICE_SUBSCRIPTION=risk-engine-prices-consumer
RISK_SUBSCRIPTION=risk-events-consumer
RISK_DATABASE_URL=postgresql+asyncpg://risk_user:***@/risk_db?host=/cloudsql/fusion-prime:us-central1:fp-risk-db-1d929830
```

**Networking**:
- Cloud SQL Connection: `fusion-prime:us-central1:fp-risk-db-1d929830`
- VPC Connector: `fusion-prime-connector`
- VPC Egress: `private-ranges-only`
- Service Account: `961424092563-compute@developer.gserviceaccount.com`

**IAM**:
- Public access enabled (allUsers = roles/run.invoker)

---

## Issues Encountered and Resolutions

### Issue 1: Substitution Variables

**Error**:
```
INVALID_ARGUMENT: key in the template "TAG" is not a valid built-in substitution
```

**Resolution**:
- Changed `$TAG` → `$_TAG`
- Changed `$SHORT_SHA` → `$_SHORT_SHA`
- Added default values in substitutions section
- Removed unused substitutions (_SERVICE_NAME, _REGION, _PORT)

### Issue 2: Dockerfile Path

**Error**:
```
lstat /workspace/services/risk-engine/Dockerfile: no such file or directory
```

**Resolution**:
- Removed `dir: 'services/risk-engine'` from cloudbuild.yaml
- Build command already runs from service directory

### Issue 3: Database Connection

**Error**:
```
[Errno 2] No such file or directory
Connection refused
```

**Resolution**:
- Added Cloud SQL instance connection
- Added VPC connector and VPC egress configuration
- Set proper service account

### Issue 4: Environment Variable Mismatch

**Error**:
```
Price oracle client not available
```

**Cause**: Set `PRICE_ORACLE_SERVICE_URL` but code expects `PRICE_ORACLE_URL`

**Resolution**:
- Updated environment variable to `PRICE_ORACLE_URL`
- Updated .env.dev for consistency

---

## Current Status

### Service Health

✅ **Operational**:
- Service URL: https://risk-engine-service-961424092563.us-central1.run.app
- Response: `{"service": "Risk Engine", "status": "operational"}`
- Database connection: Working
- HTTP endpoints: Responding

❌ **Not Operational**:
- Price Consumer: Not starting
- Price Oracle Client: Not initializing

### Logs Analysis

**What We See**:
```
INFO: Started server process [1]
INFO: Waiting for application startup
Price oracle client not available, skipping price consumer initialization
INFO: Application startup complete
INFO: Uvicorn running on http://0.0.0.0:8000
```

**What's Missing**:
- No "Risk calculator initialized successfully" log
- No "Database tables initialized successfully" log
- No "Analytics engine initialized successfully" log
- No "Price event consumer started successfully" log

### Root Cause Analysis

**Hypothesis 1: Risk Calculator Not Initializing**
- The risk calculator might be failing to initialize
- Exception being caught silently in lifespan function
- Price oracle client is created within risk calculator

**Hypothesis 2: Logging Configuration Issue**
- Logs might not be reaching Cloud Logging
- Log level filtering might be hiding initialization logs
- Structured logging might need configuration

**Hypothesis 3: Price Oracle Client Missing**
- Risk calculator might initialize but not create price_oracle_client attribute
- Price Oracle URL might not be properly passed to RiskCalculator constructor
- RiskCalculator.initialize() might be failing to create the client

---

## Code Flow Analysis

From `services/risk-engine/app/main.py`:

```python
# Line 46-54: Risk Calculator Initialization
try:
    risk_calculator = get_risk_calculator()
    await risk_calculator.initialize()
    app.state.risk_calculator = risk_calculator
    logger.info("Risk calculator initialized successfully")  # NOT APPEARING
except Exception as e:
    logger.warning(f"Failed to initialize risk calculator: {e}")  # NOT APPEARING
    app.state.risk_calculator = None
```

From `services/risk-engine/app/dependencies.py`:

```python
# Line 55: Price Oracle URL
price_oracle_url = os.getenv("PRICE_ORACLE_URL", "")  # Now correctly set

# Line 73-77: RiskCalculator Creation
_risk_calculator = RiskCalculator(
    database_url=database_url,
    price_oracle_url=price_oracle_url if price_oracle_url else None,
    gcp_project=gcp_project if gcp_project else None,
)
```

**Missing Link**: Need to investigate `RiskCalculator.initialize()` to see:
1. Does it create `self.price_oracle_client`?
2. What conditions are required for price oracle client creation?
3. Are there any silent failures?

---

## Next Steps

### Immediate Investigation

1. **Check Risk Calculator Implementation**:
   ```bash
   # Read RiskCalculator class to understand price_oracle_client creation
   cat services/risk-engine/app/core/risk_calculator.py | grep -A 20 "price_oracle_client"
   ```

2. **Add Debug Logging**:
   - Add verbose logging to risk calculator initialization
   - Log all environment variables being used
   - Log price oracle client creation attempt

3. **Test Price Oracle Client Directly**:
   ```bash
   # Verify Price Oracle Service is accessible from Risk Engine
   curl https://price-oracle-service-961424092563.us-central1.run.app/health
   ```

### Verification Steps

Once price consumer is working:

1. **Check Consumer Startup**:
   ```bash
   gcloud logging read 'resource.labels.service_name=risk-engine-service \
     AND textPayload:"Price event consumer started"' --limit=5
   ```

2. **Monitor Price Updates**:
   ```bash
   gcloud logging read 'resource.labels.service_name=risk-engine-service \
     AND textPayload:"Processing price update"' --limit=20
   ```

3. **Check Subscription**:
   ```bash
   gcloud pubsub subscriptions describe risk-engine-prices-consumer \
     --format="value(numUndeliveredMessages)"
   ```

### Alternative Approaches

If initialization continues to fail:

1. **Option 1: Standalone Price Consumer**
   - Deploy price consumer as separate Cloud Run Job
   - Decouple from Risk Engine service lifecycle
   - More robust for streaming consumers

2. **Option 2: HTTP Polling**
   - Fall back to HTTP polling of Price Oracle API
   - Less efficient but more reliable for Cloud Run
   - Use Cloud Scheduler to trigger periodic updates

3. **Option 3: Direct Database Updates**
   - Price Oracle writes directly to shared cache table
   - Risk Engine reads from database
   - Simpler architecture, slightly higher latency

---

## Architecture Status

### Current Implementation

```
Price Oracle Service
    ↓ Publishes every 30 seconds
Pub/Sub Topic: market.prices.v1
    ↓ Subscription: risk-engine-prices-consumer
Risk Engine Service ⚠️ DEPLOYED BUT NOT CONSUMING
    ↓ (Should update cache)
Price Oracle Client ❌ NOT INITIALIZING
    ↓ (Should provide cached prices)
Margin Health Calculator
```

### Expected Flow (When Working)

1. Price Oracle publishes price update to `market.prices.v1`
2. Risk Engine Price Consumer receives message
3. Price cache handler updates Price Oracle Client cache
4. Margin health calculations use cached prices
5. Reduced API calls, improved performance

---

## Deployment Commands Reference

### Deploy Risk Engine

```bash
cd /home/koita/dev/web3/fusion-prime/services/risk-engine
gcloud builds submit --config=cloudbuild.yaml --project=fusion-prime
```

### Update Environment Variables

```bash
gcloud run services update risk-engine-service \
  --region=us-central1 \
  --project=fusion-prime \
  --set-env-vars="KEY=VALUE"
```

### Check Service Status

```bash
gcloud run services describe risk-engine-service \
  --region=us-central1 \
  --project=fusion-prime \
  --format="value(status.url,status.latestReadyRevisionName)"
```

### View Logs

```bash
gcloud logging read \
  'resource.type=cloud_run_revision AND
   resource.labels.service_name=risk-engine-service AND
   resource.labels.revision_name=risk-engine-service-00005-7f2' \
  --limit=50 \
  --project=fusion-prime
```

---

## Files Modified

**Services**:
- `services/risk-engine/cloudbuild.yaml` - Fixed build configuration
- `services/risk-engine/app/infrastructure/consumers/price_consumer.py` - Consumer implementation
- `services/risk-engine/app/infrastructure/consumers/__init__.py` - Exports
- `services/risk-engine/app/main.py` - Integration

**Configuration**:
- `.env.dev` - Added PRICE_ORACLE_URL

**Documentation**:
- `RISK_ENGINE_PRICE_CONSUMER_DEPLOYMENT.md` - This file

---

## Conclusion

**Deployment Status**: ✅ Service Deployed Successfully
**Price Consumer Status**: ❌ Not Operational
**Blocker**: Price Oracle Client not initializing in Risk Calculator

**Action Required**: Investigate Risk Calculator initialization and price oracle client creation logic to determine why the client is not being created despite proper environment configuration.

The code is deployed and ready, but requires further investigation into the Risk Calculator's internal initialization process to enable the Price Consumer functionality.

---

**Last Updated**: 2025-10-29
**Revision**: risk-engine-service-00005-7f2
**Build**: 0dbf223d-04fd-46b6-b0f6-5f2da03b18e8
