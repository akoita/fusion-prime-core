# Risk Engine Pub/Sub Deployment Guide

**Date**: 2025-10-29
**Purpose**: Deploy Risk Engine with Pub/Sub escrow event synchronization

---

## Prerequisites

✅ **Already Completed:**
1. Pub/Sub subscription `risk-events-consumer` created in GCP
2. Pub/Sub consumer code implemented in Risk Engine
3. Escrow repository and database operations ready
4. Environment configuration updated (.env.dev)

---

## Deployment Steps

### Step 1: Build and Push Docker Image

```bash
cd services/risk-engine

# Build the Docker image
docker build -t us-central1-docker.pkg.dev/fusion-prime/services/risk-engine-service:latest .

# Push to Artifact Registry
docker push us-central1-docker.pkg.dev/fusion-prime/services/risk-engine-service:latest
```

### Step 2: Deploy to Cloud Run

```bash
gcloud run deploy risk-engine \
  --image us-central1-docker.pkg.dev/fusion-prime/services/risk-engine-service:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8000 \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 10 \
  --timeout 300 \
  --concurrency 100 \
  --service-account risk-service@fusion-prime.iam.gserviceaccount.com \
  --vpc-connector fusion-prime-connector \
  --set-env-vars "\
GCP_PROJECT=fusion-prime,\
GCP_REGION=us-central1,\
RISK_SUBSCRIPTION=risk-events-consumer,\
RISK_DATABASE_URL=postgresql+asyncpg://risk_user:PASSWORD@/risk_db?host=/cloudsql/fusion-prime:us-central1:fp-risk-db-1d929830,\
PRICE_ORACLE_SERVICE_URL=https://price-oracle-service-961424092563.us-central1.run.app,\
ENVIRONMENT=production"
```

**Note**: Replace `PASSWORD` with the actual database password from Secret Manager.

### Step 3: Grant Pub/Sub Permissions

```bash
# Grant Risk Engine service account subscriber role (already done via Terraform)
gcloud pubsub subscriptions add-iam-policy-binding risk-events-consumer \
  --member=serviceAccount:risk-service@fusion-prime.iam.gserviceaccount.com \
  --role=roles/pubsub.subscriber \
  --project=fusion-prime
```

### Step 4: Verify Deployment

```bash
# Check service is running
gcloud run services describe risk-engine \
  --region=us-central1 \
  --project=fusion-prime

# Check logs for Pub/Sub consumer initialization
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=risk-engine \
  AND textPayload=~'Initializing Pub/Sub consumer'" \
  --limit 10 \
  --project=fusion-prime \
  --format=json
```

---

## Alternative: Using Cloud Build

If you prefer automated builds via Cloud Build:

### Fix cloudbuild.yaml

The current `cloudbuild.yaml` has unused substitution variables. Update it:

```yaml
# Remove these from substitutions section:
substitutions:
  # DELETE: _SERVICE_NAME, _REGION, _PORT (not used)
  TAG: "latest"
  SHORT_SHA: "latest"
```

Then deploy:

```bash
gcloud builds submit services/risk-engine \
  --config=services/risk-engine/cloudbuild.yaml \
  --project=fusion-prime
```

---

## Environment Variables Required

| Variable | Value | Description |
|----------|-------|-------------|
| `GCP_PROJECT` | fusion-prime | GCP project ID |
| `GCP_REGION` | us-central1 | GCP region |
| `RISK_SUBSCRIPTION` | risk-events-consumer | Pub/Sub subscription name |
| `RISK_DATABASE_URL` | postgresql+asyncpg://... | Risk Engine database connection |
| `PRICE_ORACLE_SERVICE_URL` | https://... | Price Oracle service endpoint |
| `ENVIRONMENT` | production | Runtime environment |

---

## Verification

### 1. Check Pub/Sub Consumer Started

```bash
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=risk-engine \
  AND (textPayload=~'Pub/Sub consumer' OR textPayload=~'Risk Engine Service ready')" \
  --limit 20 \
  --project=fusion-prime
```

**Expected output**:
```
Initializing Pub/Sub consumer for escrow events
Risk Engine Service ready
```

### 2. Test Escrow Event Processing

Create a test escrow on Sepolia testnet, then check if Risk Engine processes it:

```bash
# Check for event processing logs
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=risk-engine \
  AND textPayload=~'Received Pub/Sub message'" \
  --limit 10 \
  --project=fusion-prime \
  --format=json
```

**Expected log entries**:
```json
{
  "textPayload": "Received Pub/Sub message",
  "event_type": "EscrowDeployed",
  "escrow_address": "0x..."
}
{
  "textPayload": "Escrow event EscrowDeployed synced to risk_db"
}
{
  "textPayload": "Risk recalculation triggered for 2 user(s)"
}
```

### 3. Verify Database Sync

Connect to risk_db and verify escrows are syncing:

```sql
-- Count escrows in risk_db
SELECT COUNT(*) FROM escrows;

-- Check recent escrows
SELECT address, payer, payee, status, created_at
FROM escrows
ORDER BY created_at DESC
LIMIT 10;

-- Compare with settlement_db
-- Should have similar counts
```

---

## Monitoring

### Key Metrics to Monitor

1. **Pub/Sub Subscription Metrics**:
   - Unacked message count (should be ~0)
   - Oldest unacked message age (should be low)
   - Ack latency
   - Delivery attempts

2. **Cloud Run Metrics**:
   - Request count (HTTP traffic)
   - Request latency
   - Instance count
   - CPU/Memory utilization

3. **Application Logs**:
   - Event processing success rate
   - Database sync errors
   - Risk calculation triggers

### Monitoring Dashboard

```bash
# Create a monitoring dashboard (optional)
gcloud monitoring dashboards create \
  --config-from-file=monitoring/risk-engine-dashboard.json \
  --project=fusion-prime
```

---

## Troubleshooting

### Issue: Consumer Not Starting

**Symptoms**: No Pub/Sub logs in Cloud Run

**Solutions**:
1. Check service account permissions:
   ```bash
   gcloud pubsub subscriptions get-iam-policy risk-events-consumer
   ```
2. Verify VPC connector is attached
3. Check environment variables are set

### Issue: Events Not Being Processed

**Symptoms**: Events published but not appearing in logs

**Solutions**:
1. Check subscription has messages:
   ```bash
   gcloud pubsub subscriptions pull risk-events-consumer --limit=1
   ```
2. Verify subscription is attached to correct topic
3. Check application logs for errors

### Issue: Database Connection Errors

**Symptoms**: "Failed to persist escrow event"

**Solutions**:
1. Verify Cloud SQL connection:
   ```bash
   gcloud sql instances describe fp-risk-db-1d929830
   ```
2. Check database credentials in Secret Manager
3. Verify VPC connector configuration

---

## Rollback Procedure

If deployment fails:

```bash
# List previous revisions
gcloud run revisions list \
  --service=risk-engine \
  --region=us-central1

# Rollback to previous revision
gcloud run services update-traffic risk-engine \
  --to-revisions=PREVIOUS_REVISION=100 \
  --region=us-central1
```

---

## Post-Deployment Checklist

- [ ] Service deployed successfully
- [ ] Pub/Sub consumer initialized in logs
- [ ] Environment variables configured
- [ ] Database connection working
- [ ] First escrow event processed
- [ ] Escrow synced to risk_db
- [ ] Risk recalculation triggered
- [ ] Monitoring dashboard set up
- [ ] Alerts configured

---

## Next Steps

After successful deployment:

1. **Monitor Event Processing**:
   - Watch Cloud Run logs for 24 hours
   - Verify escrow sync accuracy

2. **Implement Risk Recalculation**:
   - Currently `escrow_event_handler()` only logs
   - Implement actual risk calculator calls
   - Consider async task queue for heavy calculations

3. **Add Margin Health Checks**:
   - Trigger margin health calculations on escrow changes
   - Publish margin alerts to `alerts.margin.v1` topic

4. **Performance Tuning**:
   - Adjust instance count based on load
   - Optimize database queries
   - Add caching if needed

---

## Support

For issues or questions:
- Check logs: `gcloud logging read --project=fusion-prime`
- Review metrics: GCP Console > Monitoring
- Documentation: `RISK_ENGINE_PUBSUB_IMPLEMENTATION.md`
