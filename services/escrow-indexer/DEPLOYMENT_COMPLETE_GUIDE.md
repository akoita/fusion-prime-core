# Complete Deployment Guide - Escrow Indexer

End-to-end guide for deploying the Escrow Indexer with Terraform, scripts, and backfill.

## Overview

This guide covers:
1. Infrastructure provisioning with Terraform
2. Database setup and schema initialization
3. Service deployment to Cloud Run
4. Historical data backfill
5. Frontend integration

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ INFRASTRUCTURE (Terraform)                                   │
│                                                               │
│  Cloud SQL PostgreSQL ─┐                                     │
│  Pub/Sub Subscription  ├─► Cloud Run Service (escrow-indexer)│
│  Secret Manager        │                                      │
│  VPC Connector        ─┘                                      │
└───────────────────────────────────────────────────────────────┘
                              │
                              ▼
                      ┌───────────────┐
                      │ REST API      │
                      │ /api/v1/...   │
                      └───────────────┘
                              │
                              ▼
                      ┌───────────────┐
                      │ Frontend      │
                      │ (React/Vite)  │
                      └───────────────┘
```

## Step 1: Terraform Infrastructure

### 1.1 Prerequisites

```bash
# Required tools
- Terraform >= 1.5
- gcloud CLI
- Authenticated to GCP: gcloud auth login

# Required GCP APIs
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  pubsub.googleapis.com \
  secretmanager.googleapis.com \
  vpcaccess.googleapis.com \
  compute.googleapis.com \
  --project=fusion-prime
```

### 1.2 Deploy Infrastructure

```bash
cd infra/terraform/project/escrow-indexer

# Initialize Terraform
terraform init

# Copy and customize variables
cp terraform.tfvars.example terraform.tfvars
vim terraform.tfvars  # Edit for your environment

# Plan deployment
terraform plan

# Apply (creates all infrastructure)
terraform apply
```

**What gets created:**
- ✅ Cloud SQL PostgreSQL instance (`escrow-indexer-db`)
- ✅ Database (`escrow_indexer`)
- ✅ Database user with auto-generated password
- ✅ Secrets in Secret Manager
- ✅ Pub/Sub subscription (`escrow-indexer-sub`)
- ✅ Dead Letter Queue for failed messages
- ✅ Cloud Run service configuration
- ✅ IAM roles and service accounts
- ✅ Monitoring alerts (production)

### 1.3 Get Outputs

```bash
# Get service URL (will be deployed in next step)
terraform output service_url

# Get database connection info
terraform output database_connection_name
terraform output database_private_ip
```

## Step 2: Build and Deploy Container

### 2.1 Build Container Image

```bash
cd services/escrow-indexer

# Build image
docker build -t gcr.io/fusion-prime/escrow-indexer:latest .

# Push to Container Registry
docker push gcr.io/fusion-prime/escrow-indexer:latest
```

### 2.2 Deploy to Cloud Run

```bash
# Cloud Run service is already configured by Terraform
# Just deploy the image
gcloud run deploy escrow-indexer \
  --image gcr.io/fusion-prime/escrow-indexer:latest \
  --region us-central1 \
  --project fusion-prime

# Or use Cloud Build for CI/CD
gcloud builds submit --config cloudbuild.yaml
```

### 2.3 Verify Deployment

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe escrow-indexer \
  --region=us-central1 \
  --format='value(status.url)')

# Health check
curl $SERVICE_URL/health

# Expected response:
# {
#   "status": "healthy",
#   "service": "escrow-indexer",
#   "database": "connected",
#   "subscriber": {
#     "messages_processed": 0,
#     "messages_failed": 0
#   }
# }
```

## Step 3: Database Setup

The database schema is automatically created on first startup, but you can also initialize it manually.

### 3.1 Automatic Initialization

The schema is created automatically when the service starts for the first time.

```bash
# Check logs
gcloud run logs read escrow-indexer --region=us-central1 --limit=20

# Look for:
# "Initializing database tables..."
# "✅ Database tables created successfully"
```

### 3.2 Manual Initialization (Optional)

```bash
cd services/escrow-indexer

# Run setup script
./scripts/setup_database.sh

# Or manually with Python
export DATABASE_URL="postgresql://user:pass@host:5432/escrow_indexer"
python -c "from infrastructure.db import init_db; init_db()"
```

## Step 4: Backfill Historical Escrows

Index existing escrows that were created before the indexer was deployed.

### 4.1 Prepare Backfill

```bash
cd services/escrow-indexer

# Set required environment variables
export RPC_URL="https://sepolia.infura.io/v3/YOUR_KEY"
export ESCROW_FACTORY_ADDRESS="0x311E63dfcEfe7f2c202715ef0DF01CDA82f58914"

# Get DATABASE_URL from Secret Manager
export DATABASE_URL=$(gcloud secrets versions access latest \
  --secret=escrow-indexer-connection-string \
  --project=fusion-prime)
```

### 4.2 Test with Dry Run

```bash
# Dry run to see what would be indexed
./scripts/backfill.sh 0 latest --dry-run

# Or with Python directly
python scripts/backfill.py \
  --from-block 0 \
  --to-block latest \
  --dry-run
```

### 4.3 Run Backfill

```bash
# Backfill all historical escrows
./scripts/backfill.sh

# Or specify block range
./scripts/backfill.sh 7000000 7500000

# Or with Python
python scripts/backfill.py \
  --from-block 7000000 \
  --to-block latest \
  --batch-size 1000
```

**Output:**
```
🚀 Starting escrow backfill...
Connecting to blockchain...
✅ Connected to blockchain (Chain ID: 11155111)
Processing blocks 7000000 to 7001000...
  Found 3 EscrowDeployed events
  ✅ Indexed: 0x08ce4bb5f68277aac2c217943d606f9e326616c3
  ✅ Indexed: 0xe55c48bc7f0a417f92faa8a34c2f69ccc8c89acb
  ✅ Indexed: 0xe138b63ff09f56a8ea17db8db9cd01a54e7c6bb8
...
Backfill Summary:
  Blocks scanned: 500000
  Events found: 15
  Events indexed: 15
  Events skipped (already indexed): 0
```

### 4.4 Verify Backfill

```bash
# Check stats
curl $SERVICE_URL/api/v1/escrows/stats

# Expected response:
# {
#   "success": true,
#   "stats": {
#     "total_escrows": 15,
#     "by_status": {
#       "created": 5,
#       "approved": 7,
#       "released": 2,
#       "refunded": 1
#     }
#   }
# }

# Test query by payee
curl "$SERVICE_URL/api/v1/escrows/by-payee/0x6efc2ecb7a021c2249ae2cf253a7f9fa37ad71ba"
```

## Step 5: Monitor and Verify

### 5.1 Monitor Pub/Sub

```bash
# Check subscription status
gcloud pubsub subscriptions describe escrow-indexer-sub

# Check message backlog (should be 0 or low)
gcloud pubsub subscriptions describe escrow-indexer-sub \
  --format='value(numUndeliveredMessages)'

# Check DLQ (should be 0)
gcloud pubsub subscriptions describe escrow-indexer-dlq-sub \
  --format='value(numUndeliveredMessages)'
```

### 5.2 Monitor Service

```bash
# Watch logs
gcloud run logs tail escrow-indexer --region=us-central1

# Check metrics in Cloud Console
# https://console.cloud.google.com/run/detail/us-central1/escrow-indexer/metrics

# Test creating new escrow
# Use your frontend to create a test escrow
# Watch logs for:
# "📨 Received EscrowDeployed event"
# "✅ Successfully processed EscrowDeployed"
```

### 5.3 Test API

```bash
# Get all endpoints
SERVICE_URL=$(gcloud run services describe escrow-indexer \
  --region=us-central1 \
  --format='value(status.url)')

# Stats
curl "$SERVICE_URL/api/v1/escrows/stats"

# By payer
curl "$SERVICE_URL/api/v1/escrows/by-payer/0xe6be859007336c4f108ee3b0ee6ae0d7927cabe2"

# By payee
curl "$SERVICE_URL/api/v1/escrows/by-payee/0x6efc2ecb7a021c2249ae2cf253a7f9fa37ad71ba"

# By arbiter
curl "$SERVICE_URL/api/v1/escrows/by-arbiter/0x5e85f268274b9e89eceb77a513e45f7ea68d3a5b"

# By role (all three)
curl "$SERVICE_URL/api/v1/escrows/by-role/0x6efc2ecb7a021c2249ae2cf253a7f9fa37ad71ba"

# Specific escrow
curl "$SERVICE_URL/api/v1/escrows/0x08ce4bb5f68277aac2c217943d606f9e326616c3"

# Approvals
curl "$SERVICE_URL/api/v1/escrows/0x08ce4bb5f68277aac2c217943d606f9e326616c3/approvals"

# Events (audit trail)
curl "$SERVICE_URL/api/v1/escrows/0x08ce4bb5f68277aac2c217943d606f9e326616c3/events"
```

## Step 6: Frontend Integration

Update the frontend to use the indexer API instead of scanning the blockchain.

### 6.1 Add API Base URL

```typescript
// frontend/risk-dashboard/src/config/api.ts
export const API_CONFIG = {
  ESCROW_INDEXER_URL: import.meta.env.VITE_ESCROW_INDEXER_URL ||
    'https://escrow-indexer-xxxxx-uc.a.run.app'
}
```

### 6.2 Create API Client

```typescript
// frontend/risk-dashboard/src/lib/escrow-api.ts
import { API_CONFIG } from '@/config/api'

export async function getEscrowsByRole(address: string) {
  const response = await fetch(
    `${API_CONFIG.ESCROW_INDEXER_URL}/api/v1/escrows/by-role/${address}`
  )
  return response.json()
}
```

### 6.3 Update Hook

```typescript
// frontend/risk-dashboard/src/hooks/contracts/useEscrowsByRole.ts
import { getEscrowsByRole } from '@/lib/escrow-api'

export function useEscrowsByRole(userAddress?: Address) {
  return useQuery({
    queryKey: ['escrows-by-role', userAddress],
    queryFn: () => getEscrowsByRole(userAddress),
    enabled: !!userAddress
  })
}
```

## Troubleshooting

### Database Connection Issues

```bash
# Check Cloud SQL status
gcloud sql instances describe escrow-indexer-db

# Check VPC connector
gcloud compute networks vpc-access connectors describe \
  fusion-prime-vpc-connector --region us-central1

# Check Cloud Run logs
gcloud run logs read escrow-indexer --limit=50 | grep -i "database"
```

### Pub/Sub Not Receiving Messages

```bash
# Verify relayer is running and publishing
gcloud run services describe relayer --region us-central1

# Check topic exists
gcloud pubsub topics describe settlement.events.v1

# Check subscription permissions
gcloud pubsub subscriptions get-iam-policy escrow-indexer-sub
```

### Backfill Issues

```bash
# Check RPC_URL is valid
curl $RPC_URL -X POST -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# Check factory address is correct
cast code $ESCROW_FACTORY_ADDRESS --rpc-url $RPC_URL

# Run with verbose logging
python scripts/backfill.py --from-block 0 --to-block 1000 --dry-run
```

## Maintenance

### Update Service

```bash
# Rebuild and deploy
docker build -t gcr.io/fusion-prime/escrow-indexer:v1.1.0 .
docker push gcr.io/fusion-prime/escrow-indexer:v1.1.0

gcloud run deploy escrow-indexer \
  --image gcr.io/fusion-prime/escrow-indexer:v1.1.0 \
  --region us-central1
```

### Scale Database

```bash
cd infra/terraform/project/escrow-indexer

# Edit terraform.tfvars to change tier
# tier = "db-n1-standard-1"  # Production

terraform apply
```

### Backup Database

```bash
# Manual backup
gcloud sql backups create \
  --instance=escrow-indexer-db \
  --description="Pre-upgrade backup"

# List backups
gcloud sql backups list --instance=escrow-indexer-db
```

## Cost Optimization

### Development
- Use `environment = "dev"` in terraform.tfvars
- Cloud SQL: db-f1-micro (~$7/month)
- Cloud Run: Scale to zero (~$0/month)
- Total: ~$7/month

### Production
- Use `environment = "prod"` in terraform.tfvars
- Cloud SQL: db-n1-standard-1 with replica (~$100/month)
- Cloud Run: Min 1 instance (~$15/month)
- Total: ~$115-120/month

## Next Steps

1. ✅ Infrastructure deployed
2. ✅ Service running
3. ✅ Database populated
4. 🔄 Integrate with frontend
5. 📊 Set up monitoring dashboard
6. 🚨 Configure alerting
7. 📝 Document API for team

## Support

For issues:
1. Check service logs: `gcloud run logs read escrow-indexer`
2. Check Pub/Sub: `gcloud pubsub subscriptions describe escrow-indexer-sub`
3. Check database: `gcloud sql instances describe escrow-indexer-db`
4. Review Terraform state: `terraform show`
