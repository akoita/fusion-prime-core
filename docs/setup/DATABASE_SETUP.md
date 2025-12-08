# Database Migration System for Fusion Prime

## Overview

Fusion Prime uses **Cloud SQL PostgreSQL** for production databases with migrations managed through GCP tooling and Alembic for development. This document provides comprehensive guidance for database setup, migrations, and maintenance following GCP best practices.

## Architecture

### Services with Database Support
- ✅ **Settlement Service** - PostgreSQL with async support (asyncpg)
- ✅ **Risk Engine Service** - PostgreSQL ready
- ✅ **Compliance Service** - PostgreSQL ready

### Database Schema
- `settlement_commands` - Stores settlement command records
- `webhook_subscriptions` - Stores webhook subscription records

## Prerequisites

### 1. Cloud SQL Instance
Ensure you have a Cloud SQL PostgreSQL instance running:
```bash
gcloud sql instances list --project=fusion-prime
```

### 2. Database Secrets
Create the required secrets in Secret Manager:

**Database Password:**
```bash
# Generate a secure password
PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)

# Store in Secret Manager
echo "$PASSWORD" | gcloud secrets create settlement-db-password \
  --data-file=- \
  --project=fusion-prime
```

**Connection String:**
```bash
# Create the connection string secret
PASSWORD=$(gcloud secrets versions access latest --secret=settlement-db-password --project=fusion-prime)

echo "postgresql+asyncpg://settlement_user:${PASSWORD}@/settlement_db?host=/cloudsql/PROJECT_ID:REGION:INSTANCE_NAME" | \
  gcloud secrets create settlement-db-connection-string \
  --data-file=- \
  --project=fusion-prime
```

### 3. IAM Permissions
Grant necessary permissions to service accounts:

```bash
# Grant Cloud SQL Client role
gcloud projects add-iam-policy-binding fusion-prime \
  --member="serviceAccount:settlement-service@fusion-prime.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"

# Grant Secret Manager access
gcloud secrets add-iam-policy-binding settlement-db-connection-string \
  --member="serviceAccount:settlement-service@fusion-prime.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project=fusion-prime
```

## 🚀 Production Migration Process (Recommended)

### Method 1: GCS + Cloud SQL Import (Production)

This is the **recommended approach** for Cloud SQL migrations following GCP best practices.

**Step 1: Create Migration SQL File**
```bash
cat > /tmp/migration.sql << 'EOF'
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

CREATE TABLE IF NOT EXISTS webhook_subscriptions (
    subscription_id VARCHAR(128) PRIMARY KEY,
    url VARCHAR(512) NOT NULL,
    secret VARCHAR(256) NOT NULL,
    event_types TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    description VARCHAR(512),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
EOF
```

**Step 2: Upload to GCS**
```bash
# Create GCS bucket for migrations (if not exists)
gsutil mb -p fusion-prime gs://fusion-prime-migrations

# Upload migration file
gsutil cp /tmp/migration.sql gs://fusion-prime-migrations/
```

**Step 3: Grant Cloud SQL Service Account Access**
```bash
# Get the Cloud SQL service account
SA=$(gcloud sql instances describe INSTANCE_NAME \
  --project=fusion-prime \
  --format="value(serviceAccountEmailAddress)")

# Grant access to GCS bucket
gsutil iam ch serviceAccount:${SA}:objectViewer gs://fusion-prime-migrations
```

**Step 4: Import Migration**
```bash
gcloud sql import sql INSTANCE_NAME \
  gs://fusion-prime-migrations/migration.sql \
  --database=settlement_db \
  --user=settlement_user \
  --project=fusion-prime \
  --quiet
```

### Method 2: Cloud Run Migration Job (CI/CD)

For automated migrations in CI/CD pipelines:

**Step 1: Build Migration Image**
```bash
cd scripts
docker build -t gcr.io/fusion-prime/settlement-migration:latest -f Dockerfile.migration .
docker push gcr.io/fusion-prime/settlement-migration:latest
```

**Step 2: Create Cloud Run Job**
```bash
gcloud run jobs create settlement-migration \
  --image=gcr.io/fusion-prime/settlement-migration:latest \
  --region=us-central1 \
  --project=fusion-prime \
  --set-cloudsql-instances=PROJECT_ID:REGION:INSTANCE_NAME \
  --set-secrets=DATABASE_URL=settlement-db-connection-string:latest \
  --service-account=settlement-service@fusion-prime.iam.gserviceaccount.com \
  --max-retries=0 \
  --task-timeout=10m
```

**Step 3: Execute Migration**
```bash
gcloud run jobs execute settlement-migration \
  --region=us-central1 \
  --project=fusion-prime \
  --wait
```

## 🔧 Development Migration Process

### Method 3: Local Development with Docker Compose

For local development using Docker Compose:

```bash
# Start services
docker-compose up -d postgres settlement-service

# Migrations run automatically on service startup
# Check logs
docker-compose logs settlement-service | grep "Database tables"
```

### Method 4: Alembic (Development Only)

For iterative development and schema changes:

```bash
cd services/settlement

# Create new migration
poetry run alembic revision --autogenerate -m "Add new column"

# Apply migration locally
poetry run alembic upgrade head

# Check migration status
poetry run alembic current
```

## ⚠️ Important Notes

### Service Account Permissions Required
- `roles/cloudsql.client` - Connect to Cloud SQL via Unix socket
- `roles/secretmanager.secretAccessor` - Read database credentials
- `roles/storage.objectViewer` - Read migration files from GCS (for Cloud SQL service account)

### Connection String Format
- **Production (Cloud Run):** `postgresql+asyncpg://user:pass@/dbname?host=/cloudsql/PROJECT:REGION:INSTANCE`
- **Local (Cloud SQL Proxy):** `postgresql+asyncpg://user:pass@localhost:5432/dbname`
- **Docker Compose:** `postgresql+asyncpg://user:pass@postgres:5432/dbname`

### Automatic Table Creation
The Settlement Service includes automatic table creation on startup via SQLAlchemy's `Base.metadata.create_all()`. However, for production, **always use explicit migrations** through GCS import or Cloud Run Jobs for:
- Auditability
- Rollback capability
- Change tracking
- Team visibility

## Troubleshooting

### Common Issues

**1. "relation does not exist" (Table not found)**
```bash
# Check if tables were created
gcloud sql connect INSTANCE_NAME --user=settlement_user --database=settlement_db
\dt

# If tables don't exist, run migration using Method 1 (GCS + Import)
```

**2. "password authentication failed"**
```bash
# Reset the password and update secrets
PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)

# Update Cloud SQL user password
gcloud sql users set-password settlement_user \
  --instance=INSTANCE_NAME \
  --password="$PASSWORD" \
  --project=fusion-prime

# Update both secrets
echo "$PASSWORD" | gcloud secrets versions add settlement-db-password --data-file=-
echo "postgresql+asyncpg://settlement_user:${PASSWORD}@/settlement_db?host=/cloudsql/PROJECT:REGION:INSTANCE" | \
  gcloud secrets versions add settlement-db-connection-string --data-file=-
```

**3. "Permission denied on secret"**
```bash
# Grant service account access to secret
gcloud secrets add-iam-policy-binding SECRET_NAME \
  --member="serviceAccount:SERVICE_ACCOUNT@PROJECT.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

**4. "Unable to open database file" (SQLite error)**
- This means the service is using the SQLite fallback instead of PostgreSQL
- Ensure `DATABASE_URL` environment variable is properly set in Cloud Run
- Check Secret Manager configuration

**5. "Connection refused" or "No such file or directory"**
- Verify Cloud SQL instance connection annotation in Cloud Run:
  ```bash
  gcloud run services describe SERVICE_NAME --format="value(spec.template.metadata.annotations)"
  ```
- Should include: `run.googleapis.com/cloudsql-instances: PROJECT:REGION:INSTANCE`

### Migration Rollback

**For SQL-based migrations:**
```bash
# Create rollback SQL file
cat > /tmp/rollback.sql << 'EOF'
DROP TABLE IF EXISTS webhook_subscriptions CASCADE;
DROP TABLE IF EXISTS settlement_commands CASCADE;
EOF

# Upload and execute
gsutil cp /tmp/rollback.sql gs://fusion-prime-migrations/
gcloud sql import sql INSTANCE_NAME \
  gs://fusion-prime-migrations/rollback.sql \
  --database=settlement_db \
  --user=settlement_user \
  --project=fusion-prime
```

**For Alembic migrations (development):**
```bash
cd services/settlement
poetry run alembic downgrade -1  # Rollback one migration
poetry run alembic downgrade <revision_id>  # Rollback to specific version
```

## Best Practices

### 1. Always Test Migrations in Staging First
```bash
# Apply to staging instance first
gcloud sql import sql STAGING_INSTANCE \
  gs://fusion-prime-migrations/migration.sql \
  --database=settlement_db \
  --project=fusion-prime-staging

# Verify
# Run integration tests
./scripts/test/remote.sh all

# Then apply to production
```

### 2. Backup Before Migrations
```bash
# Create on-demand backup
gcloud sql backups create \
  --instance=INSTANCE_NAME \
  --project=fusion-prime \
  --description="Pre-migration backup $(date +%Y-%m-%d)"
```

### 3. Use Versioned Migration Files
```bash
# Name migrations with timestamps
001_create_initial_schema.sql
002_add_webhook_subscriptions.sql
003_add_audit_columns.sql
```

### 4. Include Rollback Scripts
For each migration, create a corresponding rollback:
```
migrations/
  ├── 001_add_column_up.sql
  ├── 001_add_column_down.sql
  ├── 002_create_index_up.sql
  └── 002_create_index_down.sql
```

### 5. Integrate with CI/CD
```yaml
# Example Cloud Build step
- name: 'gcr.io/cloud-builders/gcloud'
  id: 'run-migrations'
  entrypoint: 'bash'
  args:
    - '-c'
    - |
      gsutil cp migrations/*.sql gs://fusion-prime-migrations/
      gcloud sql import sql $$INSTANCE_NAME \
        gs://fusion-prime-migrations/migration.sql \
        --database=settlement_db \
        --project=fusion-prime
```

## Database Schema

### Settlement Commands Table
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

**Purpose:** Tracks settlement commands throughout their lifecycle (received → validated → executed → settled).

### Webhook Subscriptions Table
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

**Purpose:** Stores webhook subscriptions for event notifications.

## Current Production Configuration

### Cloud SQL Instance
- **Instance Name:** `fusion-prime-db-a504713e`
- **Database Version:** PostgreSQL 16
- **Region:** `us-central1-a`
- **Connection Name:** `fusion-prime:us-central1:fusion-prime-db-a504713e`

### Database Credentials
- **Database:** `settlement_db`
- **User:** `settlement_user`
- **Password:** Stored in Secret Manager (`settlement-db-password`)
- **Connection String:** Stored in Secret Manager (`settlement-db-connection-string`)

### Service Accounts
- **Settlement Service:** `settlement-service@fusion-prime.iam.gserviceaccount.com`
- **Cloud SQL Service Account:** Auto-generated by Cloud SQL instance

## Quick Reference Commands

### Check Database Status
```bash
# List Cloud SQL instances
gcloud sql instances list --project=fusion-prime

# Check database connection from Cloud Run
gcloud logging read "resource.type=cloud_run_revision AND textPayload=~\"Database tables\"" --limit=5
```

### Verify Migration
```bash
# Connect to database (requires psql installed)
gcloud sql connect fusion-prime-db-a504713e --user=settlement_user --database=settlement_db

# List tables
\dt

# Check table structure
\d settlement_commands
\d webhook_subscriptions
```

### Monitor Migrations
```bash
# Watch Cloud SQL operations
gcloud sql operations list --instance=fusion-prime-db-a504713e --project=fusion-prime

# Check GCS migration files
gsutil ls gs://fusion-prime-migrations/
```

## Environment Variables

### Cloud Run Service Configuration
```bash
# Required environment variables
DATABASE_URL=<from Secret Manager: settlement-db-connection-string>
GCP_PROJECT=fusion-prime
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
```

### Required Annotations
```yaml
# Cloud Run service YAML
metadata:
  annotations:
    run.googleapis.com/cloudsql-instances: fusion-prime:us-central1:fusion-prime-db-a504713e
```

## Testing

### Verify Database Connectivity
```bash
# Run integration tests
./scripts/test/remote.sh all

# Check specific database test
pytest tests/remote/testnet/test_system_integration.py::TestSystemIntegration::test_settlement_service_connectivity -v
```

### Manual Testing
```bash
# Test command ingestion
curl -X POST https://settlement-service-PROJECT_ID.us-central1.run.app/commands/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "command_id": "test-'$(date +%s)'",
    "workflow_id": "test-workflow",
    "account_ref": "test-account",
    "asset_symbol": "ETH",
    "amount": "0.001"
  }'
```

## Related Files

- `services/settlement/app/main.py` - Service startup with table auto-creation
- `services/settlement/infrastructure/db/models.py` - SQLAlchemy database models
- `services/settlement/alembic/` - Alembic migration configuration
- `scripts/migrate_cloud.py` - Cloud migration runner script
- `scripts/Dockerfile.migration` - Docker image for migration jobs
- `infra/cloud-run/settlement-service.yaml` - Cloud Run service configuration

## Resources

- [Cloud SQL Best Practices](https://cloud.google.com/sql/docs/postgres/best-practices)
- [Cloud SQL IAM Database Authentication](https://cloud.google.com/sql/docs/postgres/authentication)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
