# Sprint 04 Services Deployment Guide

**Created**: 2025-11-02
**Status**: 📋 Deployment Instructions

---

## 🎯 Overview

This guide covers deploying the three new Sprint 04 services to the dev environment:
1. Fiat Gateway Service
2. Cross-Chain Integration Service
3. API Key Service

---

## 📋 Prerequisites

### Required GCP Resources
- [x] Artifact Registry repository: `fusion-prime-services`
- [x] Cloud Run API enabled
- [x] Secret Manager API enabled
- [ ] Database instances (see below)
- [ ] Secrets created in Secret Manager

### Database Setup

#### Fiat Gateway Database
```bash
# Create Cloud SQL instance (if not exists)
gcloud sql instances create fp-fiat-gateway-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --project=$PROJECT_ID

# Create database
gcloud sql databases create fiat_gateway \
  --instance=fp-fiat-gateway-db \
  --project=$PROJECT_ID

# Get connection string and store in Secret Manager
CONN_STR=$(gcloud sql instances describe fp-fiat-gateway-db \
  --format="value(connectionName)")
echo "$CONN_STR" | gcloud secrets create fp-fiat-gateway-db-connection-string \
  --data-file=- --project=$PROJECT_ID
```

#### Cross-Chain Integration Database
```bash
# Create Cloud SQL instance (if not exists)
gcloud sql instances create fp-cross-chain-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --project=$PROJECT_ID

# Create database
gcloud sql databases create cross_chain \
  --instance=fp-cross-chain-db \
  --project=$PROJECT_ID

# Get connection string and store in Secret Manager
CONN_STR=$(gcloud sql instances describe fp-cross-chain-db \
  --format="value(connectionName)")
echo "$CONN_STR" | gcloud secrets create fp-cross-chain-db-connection-string \
  --data-file=- --project=$PROJECT_ID
```

### Secrets Setup

#### For Fiat Gateway Service
```bash
# Circle API Key
echo "your-circle-api-key" | gcloud secrets create fp-circle-api-key \
  --data-file=- --project=$PROJECT_ID

# Circle Wallet ID
echo "your-circle-wallet-id" | gcloud secrets create fp-circle-wallet-id \
  --data-file=- --project=$PROJECT_ID

# Stripe Secret Key
echo "your-stripe-secret-key" | gcloud secrets create fp-stripe-secret-key \
  --data-file=- --project=$PROJECT_ID

# Stripe Webhook Secret
echo "your-stripe-webhook-secret" | gcloud secrets create fp-stripe-webhook-secret \
  --data-file=- --project=$PROJECT_ID
```

#### For Cross-Chain Integration Service
```bash
# Axelar API Key (optional, for enhanced rate limits)
echo "your-axelar-api-key" | gcloud secrets create fp-axelar-api-key \
  --data-file=- --project=$PROJECT_ID

# CCIP RPC URL
echo "https://ccip.chain.link" | gcloud secrets create fp-ccip-rpc-url \
  --data-file=- --project=$PROJECT_ID
```

---

## 🚀 Deployment Steps

### 1. Deploy Fiat Gateway Service

```bash
cd services/fiat-gateway

# Run database migrations first
# (Connect via Cloud SQL Proxy or run from Cloud Build)
alembic upgrade head

# Deploy via Cloud Build
gcloud builds submit --config=cloudbuild.yaml --project=$PROJECT_ID

# Verify deployment
gcloud run services describe fiat-gateway-service \
  --region=us-central1 --project=$PROJECT_ID
```

**Health Check**: `https://fiat-gateway-service-<hash>-uc.a.run.app/health`

---

### 2. Deploy Cross-Chain Integration Service

```bash
cd services/cross-chain-integration

# Deploy via Cloud Build
gcloud builds submit --config=cloudbuild.yaml --project=$PROJECT_ID

# Verify deployment
gcloud run services describe cross-chain-integration-service \
  --region=us-central1 --project=$PROJECT_ID
```

**Health Check**: `https://cross-chain-integration-service-<hash>-uc.a.run.app/health`

**Note**: This service requires database setup if using persistent storage for messages.

---

### 3. Deploy API Key Service

```bash
cd infra/api-gateway/api-key-service

# Deploy via Cloud Build
gcloud builds submit --config=cloudbuild.yaml --project=$PROJECT_ID

# Verify deployment
gcloud run services describe api-key-service \
  --region=us-central1 --project=$PROJECT_ID
```

**Health Check**: `https://api-key-service-<hash>-uc.a.run.app/health`

---

## ✅ Post-Deployment Verification

### Test Each Service

#### Fiat Gateway Service
```bash
# Health check
curl https://fiat-gateway-service-<hash>-uc.a.run.app/health

# List transactions (should return empty array initially)
curl https://fiat-gateway-service-<hash>-uc.a.run.app/api/v1/transactions
```

#### Cross-Chain Integration Service
```bash
# Health check
curl https://cross-chain-integration-service-<hash>-uc.a.run.app/health

# List messages
curl https://cross-chain-integration-service-<hash>-uc.a.run.app/api/v1/messages
```

#### API Key Service
```bash
# Health check
curl https://api-key-service-<hash>-uc.a.run.app/health

# Create test API key
curl -X POST https://api-key-service-<hash>-uc.a.run.app/api/v1/keys \
  -H "Content-Type: application/json" \
  -d '{"key_name": "Test Key", "tier": "free"}'
```

---

## 🔧 Troubleshooting

### Service Fails to Start
- Check Cloud Run logs: `gcloud logging read "resource.type=cloud_run_revision" --limit 50`
- Verify secrets exist: `gcloud secrets list`
- Check database connectivity if using Cloud SQL

### Database Connection Issues
- Ensure Cloud SQL instance exists
- Verify connection string in Secret Manager
- Check Cloud SQL Proxy if using private IP
- Verify VPC connector is configured

### Missing Secrets
- Create secrets before deployment
- Verify secret names match cloudbuild.yaml
- Check IAM permissions for Cloud Run service account

---

## 📊 Deployment Status

After deployment, update service URLs in:
- `docs/DEPLOYMENT_STATUS.md`
- Frontend environment variables
- API Gateway configuration

---

## 🎯 Next Steps

After successful deployment:
1. ✅ Run integration tests (Option 2)
2. ✅ Update deployment status docs
3. ✅ Configure API Gateway endpoints
4. ✅ Deploy Developer Portal (optional)

---

## 💡 Quick Deploy Script

```bash
#!/bin/bash
PROJECT_ID="your-project-id"

# Deploy all services
cd services/fiat-gateway && gcloud builds submit --config=cloudbuild.yaml --project=$PROJECT_ID
cd ../cross-chain-integration && gcloud builds submit --config=cloudbuild.yaml --project=$PROJECT_ID
cd ../../infra/api-gateway/api-key-service && gcloud builds submit --config=cloudbuild.yaml --project=$PROJECT_ID

echo "✅ All services deployed!"
```
