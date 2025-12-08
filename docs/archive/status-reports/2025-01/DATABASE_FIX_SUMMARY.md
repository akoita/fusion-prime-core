# Database Configuration Fix - October 25, 2025

## Issue Summary

The settlement service integration test `test_settlement_command_ingest` was failing with a 500 Internal Server Error due to missing database configuration and schema.

### Root Causes Identified

1. **Missing DATABASE_URL Secret**: The `settlement-db-connection-string` secret didn't exist in Secret Manager
2. **Incorrect Password**: The settlement_user password in Cloud SQL didn't match what was expected
3. **Missing Database Schema**: The `settlement_commands` and `webhook_subscriptions` tables weren't created
4. **Insufficient Permissions**: Service account lacked necessary Cloud SQL and Secret Manager permissions

## Solution Implemented

### 1. Created Database Secrets

**Password Secret:**
```bash
PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
# Result: 9d6OSSfwW1RE02NcDfeVmOtfy

gcloud secrets create settlement-db-password --data-file=-
```

**Connection String Secret:**
```bash
gcloud secrets create settlement-db-connection-string --data-file=-
# Value: postgresql+asyncpg://settlement_user:9d6OSSfwW1RE02NcDfeVmOtfy@/settlement_db?host=/cloudsql/fusion-prime:us-central1:fusion-prime-db-a504713e
```

### 2. Configured IAM Permissions

```bash
# Cloud SQL Client access
gcloud projects add-iam-policy-binding fusion-prime \
  --member="serviceAccount:settlement-service@fusion-prime.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"

# Secret Manager access
gcloud secrets add-iam-policy-binding settlement-db-connection-string \
  --member="serviceAccount:settlement-service@fusion-prime.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 3. Updated Cloud Run Configuration

```bash
# Added DATABASE_URL from Secret Manager
gcloud run services update settlement-service \
  --region=us-central1 \
  --update-secrets=DATABASE_URL=settlement-db-connection-string:latest \
  --add-cloudsql-instances=fusion-prime:us-central1:fusion-prime-db-a504713e
```

### 4. Created Database Schema

Used GCS + Cloud SQL Import approach (recommended for production):

```bash
# Upload migration SQL
gsutil cp /tmp/create_tables.sql gs://fusion-prime-migrations/

# Grant Cloud SQL service account access
SA=$(gcloud sql instances describe fusion-prime-db-a504713e --format="value(serviceAccountEmailAddress)")
gsutil iam ch serviceAccount:${SA}:objectViewer gs://fusion-prime-migrations

# Import schema
gcloud sql import sql fusion-prime-db-a504713e \
  gs://fusion-prime-migrations/create_tables.sql \
  --database=settlement_db \
  --user=settlement_user \
  --quiet
```

## Tables Created

### settlement_commands
```sql
CREATE TABLE IF NOT EXISTS settlement_commands (
    command_id VARCHAR(128) PRIMARY KEY,
    workflow_id VARCHAR(128) NOT NULL,
    account_ref VARCHAR(128) NOT NULL,
    payer VARCHAR(128),
    payee VARCHAR(128),
    asset_symbol VARCHAR(64),
    amount_numeric NUMERIC(38, 18),
    status VARCHAR(32) NOT NULL,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### webhook_subscriptions
```sql
CREATE TABLE IF NOT EXISTS webhook_subscriptions (
    subscription_id VARCHAR(128) PRIMARY KEY,
    url VARCHAR(512) NOT NULL,
    secret VARCHAR(256) NOT NULL,
    event_types TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    description VARCHAR(512),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Test Results

### Before Fix
```
FAILED test_system_integration.py::TestSystemIntegration::test_settlement_service_connectivity
Error: 500 Internal Server Error
Cause: Table "settlement_commands" does not exist
```

### After Fix
```
✅ All tests passed
✅ test_settlement_service_connectivity PASSED
✅ Cloud SQL PostgreSQL database operational
```

## Current Production Configuration

### Cloud SQL Instance
- **Name:** fusion-prime-db-a504713e
- **Region:** us-central1
- **Database:** settlement_db
- **User:** settlement_user
- **Password:** `9d6OSSfwW1RE02NcDfeVmOtfy` (in Secret Manager)

### Service Account
- **Email:** settlement-service@fusion-prime.iam.gserviceaccount.com
- **Roles:**
  - Cloud SQL Client
  - Secret Manager Secret Accessor

### Secrets
- `settlement-db-password` - Database user password
- `settlement-db-connection-string` - Full PostgreSQL connection string

## Migration Tools Created

### 1. Cloud Migration Script
- **File:** `scripts/migrate_cloud.py`
- **Purpose:** Python script for Cloud Run-based migrations
- **Usage:** Runs in Cloud Run Job with Cloud SQL socket access

### 2. Migration Docker Image
- **File:** `scripts/Dockerfile.migration`
- **Image:** `gcr.io/fusion-prime/settlement-migration:latest`
- **Purpose:** Containerized migration runner

### 3. Cloud Run Migration Job
- **Name:** `settlement-migration`
- **Region:** us-central1
- **Execution:** On-demand via `gcloud run jobs execute`

## Documentation Updated

1. **DATABASE_SETUP.md** - Complete rewrite with GCP best practices
   - Prerequisites section added
   - Production migration process documented
   - Troubleshooting guide expanded
   - Quick reference commands added

2. **docs/CLOUD_SQL_MIGRATION_GUIDE.md** - New quick start guide
   - 4-step production migration process
   - Common tasks and troubleshooting
   - Pre-production checklist

3. **DEPLOYMENT.md** - Migration section updated
   - Simplified to reference main documentation
   - Added pre-deployment checklist
   - Aligned with GCP best practices

## Best Practices Established

1. **Use GCS + Cloud SQL Import for production migrations**
   - Auditability
   - Rollback capability
   - Version control
   - No local dependencies

2. **Always backup before migrations**
   ```bash
   gcloud sql backups create --instance=INSTANCE_NAME --description="Pre-migration"
   ```

3. **Test in staging first**
   - Apply to staging instance
   - Run full integration test suite
   - Verify rollback procedure

4. **Store credentials in Secret Manager**
   - Never hardcode passwords
   - Use Secret Manager for all sensitive data
   - Grant minimal IAM permissions

5. **Use versioned migration files**
   - Name with timestamps or sequential numbers
   - Include both up and down migrations
   - Store in GCS for audit trail

## Related Files

- `DATABASE_SETUP.md` - Full migration documentation
- `docs/CLOUD_SQL_MIGRATION_GUIDE.md` - Quick start guide
- `DEPLOYMENT.md` - Deployment procedures
- `scripts/migrate_cloud.py` - Cloud migration runner
- `scripts/Dockerfile.migration` - Migration container
- `services/settlement/app/main.py` - Auto-creation fallback
- `services/settlement/infrastructure/db/models.py` - Database models

## Lessons Learned

1. **Cloud Run requires explicit database configuration**
   - Cannot rely on environment file defaults
   - Must use Secret Manager for production

2. **SQLite fallback can mask configuration issues**
   - Services may start successfully but use wrong database
   - Always verify database connection in logs

3. **Cloud SQL socket path must match region, not zone**
   - Use `PROJECT:REGION:INSTANCE`, not `PROJECT:ZONE:INSTANCE`
   - Example: `fusion-prime:us-central1:instance` not `fusion-prime:us-central1-a:instance`

4. **GCS + Import is more reliable than Cloud Run Jobs**
   - Simpler execution model
   - Better logging and error messages
   - No container startup overhead

## Next Steps

1. **Automate migrations in CI/CD** - Add Cloud Build step for migrations
2. **Set up staging database** - Create separate instance for pre-production testing
3. **Implement Alembic versioning** - Track schema versions for complex migrations
4. **Add migration monitoring** - Alert on failed migrations
5. **Document rollback procedures** - Test rollback for each migration type

## References

- [Cloud SQL Best Practices](https://cloud.google.com/sql/docs/postgres/best-practices)
- [Secret Manager](https://cloud.google.com/secret-manager/docs)
- [Cloud Run Service Identity](https://cloud.google.com/run/docs/securing/service-identity)
