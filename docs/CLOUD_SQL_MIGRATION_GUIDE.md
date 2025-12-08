# Cloud SQL Migration Quick Start Guide

## TL;DR - Production Migration in 4 Steps

```bash
# 1. Create migration SQL file
cat > /tmp/migration.sql << 'EOF'
-- Your SQL DDL here
CREATE TABLE IF NOT EXISTS my_table (...);
EOF

# 2. Upload to GCS
gsutil cp /tmp/migration.sql gs://fusion-prime-migrations/

# 3. Grant Cloud SQL service account access (first time only)
SA=$(gcloud sql instances describe INSTANCE_NAME --format="value(serviceAccountEmailAddress)")
gsutil iam ch serviceAccount:${SA}:objectViewer gs://fusion-prime-migrations

# 4. Import migration
gcloud sql import sql INSTANCE_NAME \
  gs://fusion-prime-migrations/migration.sql \
  --database=settlement_db \
  --user=settlement_user \
  --project=fusion-prime \
  --quiet
```

## Current Production Setup

### Instance Details
- **Instance:** `fusion-prime-db-a504713e`
- **Region:** `us-central1`
- **Database:** `settlement_db`
- **User:** `settlement_user`
- **Password:** In Secret Manager (`settlement-db-password`)

### Access Command
```bash
# View current password
gcloud secrets versions access latest --secret=settlement-db-password --project=fusion-prime
```

### Connection String
```
postgresql+asyncpg://settlement_user:PASSWORD@/settlement_db?host=/cloudsql/fusion-prime:us-central1:fusion-prime-db-a504713e
```

## Common Tasks

### Reset Database Password
```bash
PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)

# Update Cloud SQL
gcloud sql users set-password settlement_user \
  --instance=fusion-prime-db-a504713e \
  --password="$PASSWORD" \
  --project=fusion-prime

# Update secrets
echo "$PASSWORD" | gcloud secrets versions add settlement-db-password --data-file=-
echo "postgresql+asyncpg://settlement_user:${PASSWORD}@/settlement_db?host=/cloudsql/fusion-prime:us-central1:fusion-prime-db-a504713e" | \
  gcloud secrets versions add settlement-db-connection-string --data-file=-

# Redeploy services to pick up new password
gcloud run services update settlement-service --region=us-central1 --update-env-vars="PASSWORD_UPDATED=$(date +%s)"
```

### Verify Tables Exist
```bash
# Option 1: Using gcloud (requires psql)
gcloud sql connect fusion-prime-db-a504713e --user=settlement_user --database=settlement_db
\dt

# Option 2: Check service logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=settlement-service AND textPayload=~\"Database tables\"" --limit=5
```

### Rollback Migration
```bash
# Create rollback SQL
cat > /tmp/rollback.sql << 'EOF'
DROP TABLE IF EXISTS table_name CASCADE;
EOF

# Upload and execute
gsutil cp /tmp/rollback.sql gs://fusion-prime-migrations/
gcloud sql import sql fusion-prime-db-a504713e \
  gs://fusion-prime-migrations/rollback.sql \
  --database=settlement_db \
  --user=settlement_user \
  --project=fusion-prime
```

## Troubleshooting

### "relation does not exist"
**Solution:** Run migration using the 4-step process above.

### "password authentication failed"
**Solution:** Reset password using "Reset Database Password" section.

### "Permission denied on secret"
```bash
gcloud secrets add-iam-policy-binding settlement-db-connection-string \
  --member="serviceAccount:settlement-service@fusion-prime.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### "Unable to open database file" (SQLite error)
**Cause:** Service is using SQLite fallback instead of PostgreSQL.

**Solution:** Ensure `DATABASE_URL` is set in Cloud Run:
```bash
gcloud run services update settlement-service \
  --region=us-central1 \
  --update-secrets=DATABASE_URL=settlement-db-connection-string:latest
```

## Pre-Production Checklist

- [ ] Backup database before migration
- [ ] Test migration in staging first
- [ ] Prepare rollback script
- [ ] Notify team of maintenance window
- [ ] Monitor service health post-migration

## Resources

- Full documentation: `DATABASE_SETUP.md`
- Service configuration: `infra/cloud-run/settlement-service.yaml`
- Database models: `services/settlement/infrastructure/db/models.py`
