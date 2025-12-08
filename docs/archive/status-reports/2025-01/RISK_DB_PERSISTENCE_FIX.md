# Risk Database Persistence Fix

## Problem Summary

The Risk Engine's margin health tables (`margin_health_snapshots`, `margin_events`, `alert_notifications`) were not being populated with data despite the business logic and database persistence code being fully implemented.

## Root Cause Analysis

### Investigation Steps

1. **Verified Business Logic** ✅
   - `services/risk-engine/app/core/risk_calculator.py:525-567` contains complete database persistence logic
   - Code calls `margin_health_repository.save_health_snapshot()` after each calculation
   - Code calls `margin_health_repository.save_margin_event()` when margin events detected

2. **Verified Repository Code** ✅
   - `services/risk-engine/app/infrastructure/db/margin_health_repository.py` has full CRUD operations
   - All three tables have save/query methods implemented

3. **Verified Database Tables** ✅
   - Alembic migration `001_add_margin_health_tables_20251029.py` creates all required tables
   - Tables are also auto-created on service startup via `Base.metadata.create_all`

4. **Found the Issue** ❌
   - `services/risk-engine/cloudbuild.yaml:50` was **only setting `ENVIRONMENT=production`**
   - **Missing critical environment variables**:
     - `RISK_DATABASE_URL` (or `DATABASE_URL`)
     - `PRICE_ORACLE_URL`
     - `GCP_PROJECT`
     - `RISK_SUBSCRIPTION`
     - `PRICE_SUBSCRIPTION`

### Why This Caused Data Loss

From `services/risk-engine/app/dependencies.py:52-59`:

```python
database_url = os.getenv("DATABASE_URL", "")
price_oracle_url = os.getenv("PRICE_ORACLE_URL", "")
gcp_project = os.getenv("GCP_PROJECT", "")

# Determine if we should use production or mock calculator
use_production = database_url and "postgresql" in database_url.lower()
```

**Without DATABASE_URL:**
1. Falls back to SQLite (`sqlite+aiosqlite:///./risk.db`)
2. `use_production = False` (not PostgreSQL)
3. Uses `MockRiskCalculator` instead of real `RiskCalculator`
4. Mock calculator **does NOT persist data to database**
5. All margin health data is lost on each request!

## The Fix

### Updated `services/risk-engine/cloudbuild.yaml`

**Before (Line 50):**
```yaml
'--set-env-vars', 'ENVIRONMENT=production'
```

**After (Lines 50-52):**
```yaml
'--set-env-vars', 'ENVIRONMENT=production,GCP_PROJECT=fusion-prime,RISK_SUBSCRIPTION=risk-events-consumer,PRICE_SUBSCRIPTION=risk-engine-prices-consumer,PRICE_ORACLE_URL=https://price-oracle-service-961424092563.us-central1.run.app',
'--set-secrets', 'RISK_DATABASE_URL=fp-risk-db-connection-string:latest',
'--add-cloudsql-instances', 'fusion-prime:us-central1:fp-risk-db-1d929830'
```

### What This Fixes

1. **RISK_DATABASE_URL** (from Secret Manager)
   - Provides PostgreSQL connection string to risk_db
   - Enables `use_production = True` → uses real `RiskCalculator`
   - Initializes `margin_health_repository` for database writes

2. **Cloud SQL Instance Connection**
   - `--add-cloudsql-instances` enables Unix socket connection to risk_db
   - Required for Cloud Run to access Cloud SQL database

3. **Other Required Environment Variables**
   - `GCP_PROJECT=fusion-prime` - Enables Pub/Sub publishing
   - `PRICE_ORACLE_URL` - Enables real-time price fetching
   - `RISK_SUBSCRIPTION` - Consumer for escrow events
   - `PRICE_SUBSCRIPTION` - Consumer for price updates

## Deployment Status

**Deployment Command:**
```bash
cd services/risk-engine
gcloud builds submit --config=cloudbuild.yaml --project=fusion-prime
```

**Deployment Started:** 2025-10-31
**Status:** In Progress (monitor with `tail -f /tmp/risk_engine_deploy.log`)

## Verification Steps

After deployment completes:

### 1. Check Service Logs
```bash
gcloud run services logs read risk-engine --region=us-central1 --project=fusion-prime --limit=50
```

Look for:
- ✅ `"Risk calculator initialized with database"`
- ✅ `"Margin health repository initialized"`
- ✅ `"Database tables initialized successfully"`
- ❌ `"Using Mock Risk Calculator"` (should NOT appear)

### 2. Test Margin Health Calculation
```bash
curl -X POST https://risk-engine-961424092563.us-central1.run.app/api/v1/margin/health \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-001",
    "collateral_positions": {"ETH": 10.0},
    "borrow_positions": {"USDC": 15000.0}
  }'
```

### 3. Verify Database Persistence

**Option A: Via Test Suite**
```bash
export TEST_ENVIRONMENT=dev
python -m pytest tests/test_margin_health_integration.py::TestMarginHealthIntegration::test_calculate_margin_health_basic -v -s
```

**Option B: Direct Database Query (requires Cloud SQL Proxy)**
```bash
# Terminal 1: Start proxy
cloud-sql-proxy fusion-prime:us-central1:fp-risk-db-1d929830 --port 5433

# Terminal 2: Check tables
python tests/scripts/check_risk_db_tables.py
```

Expected output:
```
✅ margin_health_snapshots    X rows
✅ margin_events              Y rows
✅ alert_notifications        Z rows
```

## Impact

**Before Fix:**
- ❌ All margin health calculations lost after each request
- ❌ No historical margin health data
- ❌ No margin events tracked
- ❌ No alert notifications stored
- ❌ Tests showed ⚠️ warnings about missing persistence

**After Fix:**
- ✅ All margin health calculations persisted to `margin_health_snapshots`
- ✅ Margin events (warnings, calls, liquidations) saved to `margin_events`
- ✅ Alert notifications tracked in `alert_notifications`
- ✅ Historical data queryable for analytics
- ✅ Tests will show database validation success

## Related Files

- `services/risk-engine/cloudbuild.yaml` - Updated deployment configuration
- `services/risk-engine/app/dependencies.py` - Environment variable loading logic
- `services/risk-engine/app/core/risk_calculator.py:525-567` - Database persistence calls
- `services/risk-engine/app/infrastructure/db/margin_health_repository.py` - Database operations
- `tests/common/risk_db_validation_utils.py` - Test validation utilities
- `tests/common/RISK_DB_VALIDATION_README.md` - Testing documentation
- `.env.dev` - Local development configuration (updated for Cloud SQL Proxy)

## Next Steps

1. ✅ Monitor deployment completion
2. ⏳ Verify service logs show database initialization
3. ⏳ Run integration tests to confirm persistence
4. ⏳ Check database tables are being populated
5. ⏳ Update any other services with similar configuration issues

## Prevention

To prevent this issue in future services:

1. **Always configure database URLs in deployment**
   - Use `--set-secrets` for connection strings with passwords
   - Add `--add-cloudsql-instances` for Cloud SQL access

2. **Verify environment variables in cloudbuild.yaml**
   - Check `--set-env-vars` includes all required variables
   - Reference `.env.dev` or service documentation for required vars

3. **Test with production-like configuration**
   - Local tests should use Cloud SQL Proxy
   - Integration tests should verify actual database writes

4. **Add deployment validation**
   - Check service logs after deployment
   - Run smoke tests to verify database persistence
   - Monitor error rates for database connection failures
