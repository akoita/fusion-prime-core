# Database Migration Strategy

**Last Updated**: 2025-10-27
**Status**: Alembic Setup Complete - Ready for Migration Execution

---

## Overview

This document outlines the database migration strategy for Fusion Prime services using Alembic for version-controlled schema management.

## Background

### Previous Approach
- **Direct SQL migrations**: Used `scripts/run_sql_migrations.py` for manual SQL execution
- **SQLAlchemy auto-creation**: Some services relied on `Base.metadata.create_all()`
- **No version control**: Schema changes were not tracked in a version-controlled manner

### Current Issue
After standardizing database naming to `fp-<service>-db` pattern, all 5 Cloud SQL databases were recreated as empty instances. The 3 services that require databases (Settlement, Risk-Engine, Compliance) need their tables created.

---

## Migration Strategy: Alembic

### Why Alembic?

1. **Version Control**: All schema changes tracked as migration files in Git
2. **Repeatability**: Migrations can be applied consistently across environments
3. **Rollback Capability**: Alembic supports downgrade migrations
4. **Auto-generation**: Can generate migrations by comparing models to database schema
5. **Industry Standard**: Widely used with SQLAlchemy ORM

---

## Implementation Status

### ✅ Completed Setup

#### 1. Settlement Service - Already Configured
- Location: `services/settlement/`
- Configuration: `alembic.ini` ✓
- Environment: `alembic/env.py` ✓ (with DATABASE_URL support)
- Migrations: 2 existing migrations in `alembic/versions/`
  - `c81a6c877761_initial_migration.py`
  - `add_escrows_table_20251025.py`
- Status: **Ready to run migrations**

#### 2. Risk-Engine Service - Newly Configured
- Location: `services/risk-engine/`
- Configuration: `alembic.ini` ✓
- Environment: `alembic/env.py` ✓ (updated with DATABASE_URL support)
- Migrations Directory: `alembic/versions/` ✓ (created, empty)
- Status: **Ready to generate and run migrations**

#### 3. Compliance Service - Newly Configured
- Location: `services/compliance/`
- Configuration: `alembic.ini` ✓ (initialized)
- Environment: `alembic/env.py` ✓ (created with DATABASE_URL support)
- Migrations Directory: `alembic/versions/` ✓ (created, empty)
- Status: **Ready to generate and run migrations**

### Database URLs Configuration

All services configured to read database URLs from environment variables:

```python
# In alembic/env.py for all services
database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)
```

Environment variables defined in `.env.dev`:
- `SETTLEMENT_DATABASE_URL` - Settlement service database
- `RISK_DATABASE_URL` - Risk Engine service database
- `COMPLIANCE_DATABASE_URL` - Compliance service database

---

## Schema Summary

### Settlement Service (3 tables)

**File**: `services/settlement/infrastructure/db/models.py`

| Table | Primary Key | Description |
|-------|-------------|-------------|
| `settlement_commands` | `command_id` (String) | Settlement command records |
| `escrows` | `address` (String) | Escrow contract tracking |
| `webhook_subscriptions` | `subscription_id` (String) | Webhook configurations |

**Key Columns**:
- Settlement commands: workflow_id, account_ref, payer, payee, asset_symbol, amount_numeric, status
- Escrows: payer, payee, amount, chain_id, status, timestamps
- Webhooks: url, secret, event_types, enabled status

### Risk-Engine Service (1 table)

**File**: `services/risk-engine/infrastructure/db/models.py`

| Table | Primary Key | Description |
|-------|-------------|-------------|
| `escrows` | `address` (String) | Escrow risk assessment data |

**Key Columns**:
- payer, payee, amount, amount_numeric
- asset_symbol, chain_id
- status, risk_score
- timestamps (created_at, updated_at)

### Compliance Service (6 tables)

**File**: `services/compliance/infrastructure/db/models.py`

| Table | Primary Key | Description |
|-------|-------------|-------------|
| `kyc_cases` | `case_id` (String) | KYC verification cases |
| `aml_alerts` | `alert_id` (String) | AML monitoring alerts |
| `sanctions_checks` | `check_id` (String) | Sanctions screening results |
| `compliance_cases` | `case_id` (String) | General compliance cases |
| `compliance_checks` | `check_id` (String) | Compliance verification records |
| `watchlist_entries` | `entry_id` (String) | Watchlist monitoring |

**Key Features**:
- JSON columns for flexible data storage (document_data, personal_info, flags)
- Risk scoring (verification_score, risk_score)
- Detailed audit trails (created_at, updated_at, resolved_at)
- Status tracking for all entities

---

## Migration Execution Options

### Option 1: Local Execution with Cloud SQL Proxy (BLOCKED)

**Issue**: Cannot connect to Cloud SQL from local machine without Cloud SQL Proxy setup.

**Steps if using**:
```bash
# 1. Start Cloud SQL Proxy (requires setup)
cloud_sql_proxy -instances=fusion-prime:us-central1:fp-settlement-db-590d836a=tcp:5432

# 2. Run migrations for each service
cd services/risk-engine
export DATABASE_URL="${RISK_DATABASE_URL}"
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head

cd ../compliance
export DATABASE_URL="${COMPLIANCE_DATABASE_URL}"
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head

cd ../settlement
export DATABASE_URL="${SETTLEMENT_DATABASE_URL}"
alembic upgrade head  # Already has migrations
```

### Option 2: Cloud Run Migration Job (RECOMMENDED)

**Created Files**:
1. `scripts/run_alembic_migrations.sh` - Migration orchestration script
2. `Dockerfile.migrations` - Docker image for migration job

**Approach**:
- Deploy as one-time Cloud Run job
- Has Cloud SQL access via Unix sockets
- Retrieves connection strings from Secret Manager
- Generates migrations for Risk-Engine and Compliance (autogenerate)
- Runs all migrations sequentially

**Deployment** (needs correction - see Known Issues):
```bash
# Build image
docker build -f Dockerfile.migrations -t gcr.io/fusion-prime/database-migrations .
docker push gcr.io/fusion-prime/database-migrations

# Deploy job
gcloud run jobs deploy database-migrations \
  --image=gcr.io/fusion-prime/database-migrations \
  --region=us-central1 \
  --set-cloudsql-instances=\
fusion-prime:us-central1:fp-settlement-db-590d836a,\
fusion-prime:us-central1:fp-risk-db-1d929830,\
fusion-prime:us-central1:fp-compliance-db-0b9f2040 \
  --max-retries=0 \
  --task-timeout=600

# Execute job
gcloud run jobs execute database-migrations --region=us-central1 --wait
```

### Option 3: Cloud Shell Execution (ALTERNATIVE)

**Steps**:
1. Open Google Cloud Shell
2. Clone repository or upload files
3. Set environment variables from .env.dev
4. Run Alembic commands directly

**Advantages**:
- Built-in Cloud SQL access
- No Docker build required
- Quick for one-time migrations

**Commands**:
```bash
# In Cloud Shell
cd services/risk-engine
export DATABASE_URL="postgresql+asyncpg://risk_user:PASSWORD@/risk_db?host=/cloudsql/fusion-prime:us-central1:fp-risk-db-1d929830"
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

---

## Migration Workflow

### Step-by-Step Process

#### 1. Generate Migrations (for Risk-Engine and Compliance)

Alembic compares SQLAlchemy models to database schema and generates migration scripts:

```bash
cd services/risk-engine
export DATABASE_URL="${RISK_DATABASE_URL}"
alembic revision --autogenerate -m "Initial migration"
```

**Output**: Creates file like `alembic/versions/abc123_initial_migration.py`

**Generated Migration Contains**:
```python
def upgrade():
    op.create_table('escrows',
        sa.Column('address', sa.String(128), primary_key=True),
        sa.Column('payer', sa.String(128), nullable=False),
        # ... all columns defined in models.py
    )

def downgrade():
    op.drop_table('escrows')
```

#### 2. Review Generated Migrations

**Important**: Always review auto-generated migrations before running:
- Check column types are correct
- Verify indexes are created
- Ensure foreign keys are properly defined
- Confirm no data loss on downgrades

#### 3. Run Migrations

Apply migrations to create tables:

```bash
alembic upgrade head
```

**Output**:
```
INFO  [alembic.runtime.migration] Running upgrade -> abc123, Initial migration
INFO  [alembic.runtime.migration] Running upgrade abc123 -> def456, Add new column
```

#### 4. Verify Table Creation

Check that tables exist:

```sql
-- For each database
\dt  -- List tables in psql

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public';
```

---

## Migration Script Details

### `scripts/run_alembic_migrations.sh`

**Purpose**: Orchestrates migrations for all services

**Functionality**:
1. Retrieves database connection strings from Secret Manager
2. For each service (Settlement, Risk-Engine, Compliance):
   - Sets appropriate DATABASE_URL
   - Checks if migrations exist
   - Generates initial migration if needed (autogenerate)
   - Runs `alembic upgrade head`
3. Provides status output for each step

**Key Features**:
- Error handling (`set -e` - exits on any error)
- Sequential processing (one service at a time)
- Clear logging with section markers
- Secret Manager integration for secure credentials

**Usage**:
```bash
./scripts/run_alembic_migrations.sh
```

---

## Known Issues and Resolutions

### Issue 1: Special Characters in Database Passwords

**Problem**: Passwords contain special characters (`<`, `>`, `&`, `(`, `)`) that break shell parsing when sourcing `.env.dev`

**Impact**: Cannot source `.env.dev` file directly

**Resolution**:
- Migration script reads from Secret Manager directly
- Avoids shell parsing issues
- Uses `gcloud secrets versions access` command

### Issue 2: Cloud SQL Connection from Local Machine

**Problem**: Cannot connect to Cloud SQL databases from local development machine

**Error**: `Connection refused` on port 5432

**Resolution**: Use Cloud Run job or Cloud Shell with built-in Cloud SQL access

### Issue 3: Cloud Run Jobs --dockerfile Flag

**Problem**: `gcloud run jobs deploy` with `--source` doesn't support `--dockerfile` flag

**Error**: `unrecognized arguments: --dockerfile=Dockerfile.migrations`

**Resolution**: Build Docker image separately:
```bash
# Option A: Cloud Build
gcloud builds submit --tag gcr.io/fusion-prime/database-migrations -f Dockerfile.migrations .

# Option B: Local Docker + Push
docker build -f Dockerfile.migrations -t gcr.io/fusion-prime/database-migrations .
docker push gcr.io/fusion-prime/database-migrations

# Then deploy with --image
gcloud run jobs deploy database-migrations \
  --image=gcr.io/fusion-prime/database-migrations \
  --region=us-central1 \
  ...
```

---

## Future Migration Workflow

### Adding New Tables

1. **Update SQLAlchemy models** in `services/<service>/infrastructure/db/models.py`
2. **Generate migration**:
   ```bash
   cd services/<service>
   export DATABASE_URL="<service-database-url>"
   alembic revision --autogenerate -m "Add new_table"
   ```
3. **Review generated migration** in `alembic/versions/`
4. **Test locally** (if possible) or in dev environment
5. **Commit migration file** to Git
6. **Deploy**: Run `alembic upgrade head` in target environment

### Modifying Existing Tables

1. **Update model definition**
2. **Generate migration**: `alembic revision --autogenerate -m "Modify table_name"`
3. **Review migration carefully** - ensure no data loss
4. **Test with sample data**
5. **Consider data migration** if needed:
   ```python
   # In migration file
   from alembic import op

   def upgrade():
       # Schema change
       op.add_column('table_name', sa.Column('new_col', sa.String()))

       # Data migration
       op.execute("UPDATE table_name SET new_col = 'default'")
   ```

### Rolling Back Migrations

If migration causes issues:
```bash
# Downgrade one version
alembic downgrade -1

# Downgrade to specific version
alembic downgrade abc123

# Downgrade all
alembic downgrade base
```

---

## Best Practices

### 1. Always Review Auto-generated Migrations
- Alembic may not detect all changes correctly
- Foreign keys and indexes need manual verification
- Data type changes require careful review

### 2. Test Migrations in Development First
- Never run untested migrations in production
- Verify both upgrade and downgrade paths
- Test with representative data

### 3. Backup Before Major Migrations
```bash
# Export Cloud SQL database
gcloud sql export sql INSTANCE_NAME gs://bucket/backup.sql \
  --database=DATABASE_NAME
```

### 4. Use Descriptive Migration Messages
```bash
# Good
alembic revision --autogenerate -m "Add user_preferences table with JSON config"

# Bad
alembic revision --autogenerate -m "Update"
```

### 5. Keep Migrations Small and Focused
- One logical change per migration
- Easier to review and rollback
- Better Git history

### 6. Version Control Everything
- Commit migration files immediately
- Include in pull requests
- Document breaking changes

---

## Verification Checklist

After running migrations:

- [ ] All tables created in each database
- [ ] Table schemas match model definitions
- [ ] Indexes created correctly
- [ ] Foreign keys established (if any)
- [ ] Primary keys defined
- [ ] Alembic version table (`alembic_version`) exists
- [ ] Services can connect and query databases
- [ ] No errors in application logs

---

## Summary

**Current State**:
- ✅ Alembic configured for all 3 services
- ✅ DATABASE_URL environment variable support
- ✅ Migration scripts and Dockerfile created
- ⏳ Migration execution pending (awaiting Cloud Run job deployment)

**Next Steps**:
1. Build Docker image for migration job
2. Deploy Cloud Run job
3. Execute migrations
4. Verify table creation
5. Test service connectivity

**Long-term**:
- Use Alembic for all future schema changes
- Maintain migration files in Git
- Test migrations in dev before production
- Document any manual data migrations

---

## References

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Cloud SQL Proxy Documentation](https://cloud.google.com/sql/docs/postgres/sql-proxy)
- [Cloud Run Jobs Documentation](https://cloud.google.com/run/docs/create-jobs)
- Project Files:
  - Settlement models: `services/settlement/infrastructure/db/models.py`
  - Risk-Engine models: `services/risk-engine/infrastructure/db/models.py`
  - Compliance models: `services/compliance/infrastructure/db/models.py`
  - Migration script: `scripts/run_alembic_migrations.sh`
  - Migration Dockerfile: `Dockerfile.migrations`
