# Escrow Indexer Deployment Guide

## Quick Start

### 1. Prerequisites

1. **GCP Project**: `fusion-prime` (or your project ID)
2. **Pub/Sub Topic**: `settlement.events.v1` (created by relayer service)
3. **PostgreSQL Database**: Cloud SQL or managed PostgreSQL instance
4. **Relayer Service**: Must be running and publishing events

### 2. Create Database

#### Option A: Cloud SQL (Recommended for production)

```bash
# Create Cloud SQL instance
gcloud sql instances create escrow-indexer-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --project=fusion-prime

# Create database
gcloud sql databases create escrow_indexer \
  --instance=escrow-indexer-db \
  --project=fusion-prime

# Set password for postgres user
gcloud sql users set-password postgres \
  --instance=escrow-indexer-db \
  --password=YOUR_SECURE_PASSWORD \
  --project=fusion-prime

# Get connection name
gcloud sql instances describe escrow-indexer-db \
  --format='value(connectionName)' \
  --project=fusion-prime
# Output: fusion-prime:us-central1:escrow-indexer-db

# Create database URL secret
# For Cloud SQL with private IP:
DATABASE_URL="postgresql://postgres:YOUR_PASSWORD@/escrow_indexer?host=/cloudsql/fusion-prime:us-central1:escrow-indexer-db"

# For Cloud SQL with public IP:
PUBLIC_IP=$(gcloud sql instances describe escrow-indexer-db --format='value(ipAddresses[0].ipAddress)' --project=fusion-prime)
DATABASE_URL="postgresql://postgres:YOUR_PASSWORD@$PUBLIC_IP:5432/escrow_indexer"

echo -n "$DATABASE_URL" | gcloud secrets create escrow-indexer-db-url --data-file=-
```

#### Option B: External PostgreSQL

```bash
# Store database URL
echo -n "postgresql://user:password@host:5432/escrow_indexer" | \
  gcloud secrets create escrow-indexer-db-url --data-file=-
```

### 3. Deploy Service

```bash
cd services/escrow-indexer

# Deploy using automated script
./deploy.sh

# Or deploy manually:
gcloud builds submit --config cloudbuild.yaml
```

### 4. Verify Deployment

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe escrow-indexer \
  --region=us-central1 \
  --format='value(status.url)')

# Health check
curl $SERVICE_URL/health

# Check stats
curl $SERVICE_URL/api/v1/escrows/stats

# View logs
gcloud run logs read escrow-indexer --region=us-central1 --limit=50
```

## Testing

### 1. Wait for Events

The relayer must publish some events first. Create a test escrow:

```bash
# Use your frontend or directly call the EscrowFactory contract
# The relayer will detect the event and publish to Pub/Sub
# The indexer will process it and store in database
```

### 2. Query Indexed Data

```bash
# Get escrows by payer
curl "$SERVICE_URL/api/v1/escrows/by-payer/0xe6be859007336c4f108ee3b0ee6ae0d7927cabe2"

# Get escrows by payee
curl "$SERVICE_URL/api/v1/escrows/by-payee/0x6efc2ecb7a021c2249ae2cf253a7f9fa37ad71ba"

# Get all roles for an address
curl "$SERVICE_URL/api/v1/escrows/by-role/0x6efc2ecb7a021c2249ae2cf253a7f9fa37ad71ba"

# Get specific escrow
curl "$SERVICE_URL/api/v1/escrows/0x08ce4bb5f68277aac2c217943d606f9e326616c3"

# Get approvals
curl "$SERVICE_URL/api/v1/escrows/0x08ce4bb5f68277aac2c217943d606f9e326616c3/approvals"

# Get event history
curl "$SERVICE_URL/api/v1/escrows/0x08ce4bb5f68277aac2c217943d606f9e326616c3/events"
```

## Monitoring

### Check Subscriber Status

```bash
# Service health (includes subscriber stats)
curl $SERVICE_URL/health

# View detailed logs
gcloud run logs read escrow-indexer \
  --region=us-central1 \
  --limit=100 \
  --format=json

# Filter for errors
gcloud run logs read escrow-indexer \
  --region=us-central1 \
  --limit=100 | grep "ERROR"

# Filter for processed events
gcloud run logs read escrow-indexer \
  --region=us-central1 \
  --limit=100 | grep "Successfully processed"
```

### Check Pub/Sub Subscription

```bash
# View subscription details
gcloud pubsub subscriptions describe escrow-indexer-sub

# Check message backlog
gcloud pubsub subscriptions describe escrow-indexer-sub \
  --format='value(numUndeliveredMessages)'

# Pull a test message (without acking)
gcloud pubsub subscriptions pull escrow-indexer-sub \
  --limit=1 \
  --auto-ack=false
```

### Check Database

```bash
# Connect to Cloud SQL
gcloud sql connect escrow-indexer-db --user=postgres

# Run queries
SELECT COUNT(*) FROM escrows;
SELECT status, COUNT(*) FROM escrows GROUP BY status;
SELECT * FROM escrows ORDER BY created_at DESC LIMIT 10;
```

## Troubleshooting

### Service Not Receiving Events

1. Check relayer is running:
```bash
curl https://relayer-url/health
```

2. Check Pub/Sub topic has messages:
```bash
gcloud pubsub topics publish settlement.events.v1 \
  --message='{"test": true}' \
  --attribute="event_type=test"
```

3. Check subscription:
```bash
gcloud pubsub subscriptions pull escrow-indexer-sub --limit=1
```

### Database Connection Issues

1. Check secret exists:
```bash
gcloud secrets versions access latest --secret=escrow-indexer-db-url
```

2. Test database connection:
```bash
# From Cloud Shell
psql "$DATABASE_URL"
```

3. Check Cloud Run service account has access:
```bash
# Grant Secret Manager access
PROJECT_NUMBER=$(gcloud projects describe fusion-prime --format='value(projectNumber)')
SERVICE_ACCOUNT="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"

gcloud secrets add-iam-policy-binding escrow-indexer-db-url \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor"
```

### High Memory Usage

Increase memory allocation:
```bash
gcloud run services update escrow-indexer \
  --region=us-central1 \
  --memory=1Gi
```

### Slow Queries

Add database indexes (already included in schema):
```sql
CREATE INDEX IF NOT EXISTS idx_escrows_payer ON escrows(payer_address);
CREATE INDEX IF NOT EXISTS idx_escrows_payee ON escrows(payee_address);
CREATE INDEX IF NOT EXISTS idx_escrows_arbiter ON escrows(arbiter_address);
CREATE INDEX IF NOT EXISTS idx_escrows_payer_status ON escrows(payer_address, status);
```

## Scaling

### Horizontal Scaling

```bash
# Increase max instances
gcloud run services update escrow-indexer \
  --region=us-central1 \
  --max-instances=20

# Adjust concurrency
gcloud run services update escrow-indexer \
  --region=us-central1 \
  --concurrency=80
```

### Database Scaling

```bash
# Upgrade Cloud SQL tier
gcloud sql instances patch escrow-indexer-db \
  --tier=db-n1-standard-1
```

## Backup and Recovery

### Database Backups

```bash
# Enable automated backups
gcloud sql instances patch escrow-indexer-db \
  --backup-start-time=03:00

# Create manual backup
gcloud sql backups create \
  --instance=escrow-indexer-db

# List backups
gcloud sql backups list --instance=escrow-indexer-db
```

### Restore from Backup

```bash
# Restore
gcloud sql backups restore BACKUP_ID \
  --backup-instance=escrow-indexer-db \
  --backup-id=BACKUP_ID
```

## Cost Optimization

1. **Cloud Run**: Use minimum instances = 0 (default) to scale to zero when idle
2. **Cloud SQL**: Use `db-f1-micro` for development, upgrade for production
3. **Pub/Sub**: Subscription automatically deletes acknowledged messages
4. **Logs**: Adjust retention period to reduce storage costs

## Production Checklist

- [ ] Cloud SQL with automated backups enabled
- [ ] Database secret stored in Secret Manager
- [ ] Pub/Sub subscription created with appropriate retention
- [ ] Cloud Run service deployed with health checks
- [ ] Monitoring and alerting configured
- [ ] IAM permissions properly configured
- [ ] CORS configured for frontend domain
- [ ] Rate limiting considered (if needed)
- [ ] Database indexes created
- [ ] Tested with real events from relayer
