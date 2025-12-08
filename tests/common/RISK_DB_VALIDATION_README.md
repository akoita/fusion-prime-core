# Risk Database Validation Guide

This guide explains how to use the Risk Engine database validation utilities to verify that margin health data is actually persisted to the database.

## Overview

The validation utilities support **two modes**:

1. **API-Based Validation** (Default) - Validates via HTTP endpoints
2. **Direct Database Validation** (Enhanced) - Queries database tables directly

## Quick Start: API-Based Validation

This works out of the box, no setup required:

```python
from tests.common.risk_db_validation_utils import validate_margin_health_persistence

# Validates via API calls
health_data = validate_margin_health_persistence(
    risk_engine_url="https://risk-engine-961424092563.us-central1.run.app",
    user_id="test-user-001",
    collateral_positions={"ETH": 10.0},
    borrow_positions={"USDC": 15000.0},
    expected_health_score_min=0,
)
```

**Output:**
```
📊 Validating database persistence...
✅ Health calculation successful
   Health score: 233.33%
   Status: HEALTHY
⚠️  Database persistence validation requires dedicated query endpoints.
    Currently validating via health calculation API response.
```

## Enhanced: Direct Database Validation

For **full database validation**, you need to connect directly to Cloud SQL.

### Prerequisites

1. **Google Cloud SDK** installed
2. **Cloud SQL Proxy** installed:
   ```bash
   curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.linux.amd64
   chmod +x cloud-sql-proxy
   sudo mv cloud-sql-proxy /usr/local/bin/
   ```

3. **Service Account Key** with Cloud SQL Client role

### Setup Steps

#### 1. Start Cloud SQL Proxy

```bash
# Terminal 1: Start proxy for risk_db
cloud-sql-proxy fusion-prime:us-central1:fusion-prime-risk-db \
  --port 5433
```

Keep this running in a separate terminal.

#### 2. Update Database URL

In your `.env.dev`, update the `RISK_DATABASE_URL` to use the proxy:

```bash
# Before (for Cloud Run)
RISK_DATABASE_URL=postgresql+asyncpg://risk_user:PASSWORD@/cloudsql/fusion-prime:us-central1:fusion-prime-risk-db/risk_db

# After (for local testing with proxy)
RISK_DATABASE_URL=postgresql+asyncpg://risk_user:PASSWORD@localhost:5433/risk_db
```

#### 3. Run Tests with Direct Database Validation

```bash
# Set environment
export TEST_ENVIRONMENT=dev

# Run tests - they'll now query the database directly
python -m pytest tests/test_margin_health_integration.py -v
```

### Using Direct Database Query Functions

Once Cloud SQL Proxy is running, you can use these functions:

```python
import asyncio
from tests.common.risk_db_validation_utils import (
    get_risk_db_table_counts,
    query_margin_health_snapshots_from_db,
    query_margin_events_from_db,
    query_alert_notifications_from_db,
)

async def check_database():
    # Get table counts
    counts = await get_risk_db_table_counts()
    print(f"Snapshots: {counts['margin_health_snapshots']}")
    print(f"Events: {counts['margin_events']}")
    print(f"Notifications: {counts['alert_notifications']}")

    # Query specific user's snapshots
    snapshots = await query_margin_health_snapshots_from_db(
        user_id="test-user-001",
        limit=10
    )

    for snapshot in snapshots:
        print(f"Health: {snapshot['health_score']}%")
        print(f"Status: {snapshot['status']}")
        print(f"Time: {snapshot['created_at']}")

# Run async function
asyncio.run(check_database())
```

## Validation Functions

### 1. validate_margin_health_persistence()

**Purpose**: Validates that health calculation works and data persists

**What it validates:**
- ✅ Health score calculation
- ✅ Status determination (HEALTHY, WARNING, MARGIN_CALL, LIQUIDATION)
- ✅ USD price conversion
- ⚠️ Database persistence (when direct DB available)

**Usage:**
```python
health_data = validate_margin_health_persistence(
    risk_engine_url="https://risk-engine.run.app",
    user_id="test-user-001",
    collateral_positions={"ETH": 10.0, "BTC": 0.5},
    borrow_positions={"USDC": 15000.0},
    expected_health_score_min=0,
    timeout=30,
)
```

### 2. validate_escrow_synced_to_risk_db()

**Purpose**: Validates escrows are synced from settlement_db to risk_db

**What it validates:**
- ✅ Escrows table in risk_db is populated
- ✅ Portfolio risk calculations include escrow data
- ⚠️ Direct escrow record validation (when direct DB available)

### 3. validate_risk_calculation_uses_database()

**Purpose**: Checks if Risk Engine is connected to database

**What it validates:**
- ✅ Database connection status
- ✅ Table existence
- ✅ Basic query functionality

## Database Tables

The following tables are validated:

### margin_health_snapshots
Historical margin health calculations for users.

**Fields:**
- `snapshot_id` - Unique identifier
- `user_id` - User identifier
- `health_score` - Calculated health percentage
- `status` - HEALTHY | WARNING | MARGIN_CALL | LIQUIDATION
- `total_collateral_usd` - Total collateral in USD
- `total_borrow_usd` - Total borrows in USD
- `calculated_at` - Calculation timestamp
- `created_at` - Record creation timestamp

### margin_events
Margin events (warnings, calls, liquidations).

**Fields:**
- `event_id` - Unique identifier
- `user_id` - User identifier
- `event_type` - margin_warning | margin_call | liquidation_imminent
- `severity` - medium | high | critical
- `health_score` - Health score at event time
- `message` - Event message
- `published_to_pubsub` - "true" | "false"
- `created_at` - Event timestamp

### alert_notifications
Alert delivery tracking.

**Fields:**
- `notification_id` - Unique identifier
- `user_id` - User identifier
- `alert_type` - margin_call | liquidation | health_warning
- `severity` - medium | high | critical
- `channels` - ["email", "sms", "webhook"]
- `status` - sent | delivered | failed | pending
- `margin_event_id` - Link to margin event
- `sent_at` - Delivery timestamp
- `created_at` - Record creation timestamp

### escrows (risk_db copy)
Escrow data synced from settlement_db for risk calculations.

**Fields:**
- `address` - Escrow contract address
- `payer` - Payer address
- `payee` - Payee address
- `amount` - Amount in wei
- `status` - created | approved | completed | refunded
- `chain_id` - Blockchain chain ID
- `created_at` - Record creation timestamp

## Troubleshooting

### Error: "Database connection not available"

**Cause**: Cloud SQL Proxy not running or RISK_DATABASE_URL incorrect

**Solution:**
1. Check proxy is running: `ps aux | grep cloud-sql-proxy`
2. Verify connection: `psql -h localhost -p 5433 -U risk_user -d risk_db`
3. Check RISK_DATABASE_URL in .env.dev

### Error: "No such file or directory" (socket error)

**Cause**: RISK_DATABASE_URL using Unix socket path instead of TCP

**Solution**: Update to use localhost:5433:
```bash
postgresql+asyncpg://risk_user:PASSWORD@localhost:5433/risk_db
```

### Tests pass but show "⚠️  Database persistence validation requires..."

**Cause**: This is normal! It means API validation worked but direct DB not available.

**To enable full validation:**
1. Start Cloud SQL Proxy
2. Update RISK_DATABASE_URL
3. Re-run tests

## Next Steps

Once direct database validation is enabled, you can:

1. **Verify data persistence** - Confirm margin_health_snapshots are created
2. **Validate margin events** - Check margin_events table for alerts
3. **Track notifications** - Monitor alert_notifications table
4. **Test escrow sync** - Verify escrows table in risk_db

## Example: Full Validation Flow

```bash
# Terminal 1: Start Cloud SQL Proxy
cloud-sql-proxy fusion-prime:us-central1:fusion-prime-risk-db --port 5433

# Terminal 2: Update .env.dev
# Change RISK_DATABASE_URL to use localhost:5433

# Terminal 2: Run tests
export TEST_ENVIRONMENT=dev
python -m pytest tests/test_margin_health_integration.py::TestMarginHealthIntegration::test_calculate_margin_health_basic -v -s

# You'll see enhanced output:
# 📊 Validating database persistence...
# ✅ Health calculation successful
# ✅ Database query successful
# ✅ Found 1 snapshot in margin_health_snapshots table
#    Snapshot ID: snapshot-test-user-001-1234567890
#    Health Score: 233.33%
#    Status: HEALTHY
#    Created: 2025-10-31 12:00:00
```

## Benefits

### API-Based Validation (Default)
- ✅ Works immediately, no setup
- ✅ Tests business logic
- ✅ Validates API responses
- ⚠️ Can't verify database writes directly

### Direct Database Validation (Enhanced)
- ✅ Verifies actual database writes
- ✅ Validates data persistence
- ✅ Checks database schema
- ✅ Enables row-level inspection
- ⚠️ Requires Cloud SQL Proxy setup

## Recommendation

**For CI/CD pipelines**: Use API-based validation (default)

**For local development**: Use direct database validation to verify persistence

**For production debugging**: Use direct database queries to inspect actual data
