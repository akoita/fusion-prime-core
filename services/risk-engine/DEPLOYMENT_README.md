# Risk Engine Service - Deployment Guide

## Database Setup

The Risk Engine Service has its own dedicated Cloud SQL PostgreSQL database for microservice architecture.

### Database Configuration

- **Database Instance**: `fusion-prime-risk-db` (Cloud SQL)
- **Database Name**: `risk_engine_db`
- **User**: `risk_engine_user`
- **Tier**: `db-g1-small` (1.7GB RAM)
- **Disk Size**: 10 GB

### Schema Setup

The database schema includes:
- `risk_calculations` - Stores portfolio risk metrics
- `risk_alerts` - Stores risk alerts for users
- `margin_requirements` - Stores margin calculation results
- `stress_test_results` - Stores stress test scenario results

### Migration Steps

1. **Provision the database** (via Terraform):
   ```bash
   cd infra/terraform/project
   terraform apply
   ```

2. **Run migrations**:
   ```bash
   cd services/risk-engine
   # Set database URL from Secret Manager
   export DATABASE_URL="postgresql://risk_engine_user:PASSWORD@PRIVATE_IP:5432/risk_engine_db"

   # Run Alembic migrations
   alembic upgrade head
   ```

3. **Or use SQL script directly**:
   ```bash
   psql $DATABASE_URL -f infrastructure/db/schema.sql
   ```

## Environment Variables

The Risk Engine service requires these environment variables:

```bash
# Database connection (from Secret Manager)
DATABASE_URL=postgresql://risk_engine_user:PASSWORD@PRIVATE_IP:5432/risk_engine_db

# Service configuration
HOST=0.0.0.0
PORT=8080

# Observability
SERVICE_NAME=risk-engine
LOG_LEVEL=info

# BigQuery (optional, for analytics)
BIGQUERY_PROJECT=fusion-prime
BIGQUERY_DATASET=analytics

# Caching (optional)
CACHE_URL=redis://localhost:6379
```

## Deployment

The Risk Engine connects to its own database and can optionally read escrow data from the Settlement Service database using a shared VPC connection.

### Production Deployment

1. **Build the container image**:
   ```bash
   docker build -t risk-engine:latest -f services/risk-engine/Dockerfile .
   ```

2. **Push to Artifact Registry**:
   ```bash
   gcloud auth configure-docker us-central1-docker.pkg.dev
   docker tag risk-engine:latest us-central1-docker.pkg.dev/fusion-prime/services/risk-engine:latest
   docker push us-central1-docker.pkg.dev/fusion-prime/services/risk-engine:latest
   ```

3. **Deploy to Cloud Run**:
   ```bash
   gcloud run deploy risk-engine \
     --image us-central1-docker.pkg.dev/fusion-prime/services/risk-engine:latest \
     --region us-central1 \
     --platform managed \
     --set-env-vars DATABASE_URL=$(gcloud secrets versions access latest --secret=risk-engine-db-connection-string) \
     --vpc-connector fusion-prime-vpc-connector \
     --min-instances 0 \
     --max-instances 10 \
     --memory 512Mi \
     --cpu 1
   ```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Risk Engine Service                   │
│                                                          │
│  ┌─────────────────┐      ┌─────────────────┐        │
│  │ Risk Calculator  │───→  │  Analytics Engine│        │
│  │                  │      │                  │        │
│  └────────┬─────────┘      └────────┬─────────┘        │
│           │                          │                  │
│           ↓                          ↓                  │
│  ┌──────────────────────────────────────────┐         │
│  │     Risk Engine Database                   │         │
│  │  (Cloud SQL PostgreSQL)                    │         │
│  │  - risk_calculations                       │         │
│  │  - risk_alerts                             │         │
│  │  - margin_requirements                     │         │
│  │  - stress_test_results                     │         │
│  └──────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────┘
                             │
                             │ (VPC connection)
                             ↓
┌─────────────────────────────────────────────────────────┐
│           Settlement Service Database                    │
│  (Read-only access for escrow data)                     │
│  - escrows                                                │
│  - settlement_commands                                     │
└─────────────────────────────────────────────────────────┘
```

## Database Connection

The Risk Engine connects to its own database for storing risk calculations and metrics. For portfolio analysis, it reads escrow data from the Settlement Service database via VPC peering (read-only access).

### Database Security

- Private IP connectivity only (no public IP)
- SSL/TLS encrypted connections
- Service account authentication
- Secrets stored in Secret Manager

## Health Checks

The Risk Engine provides health check endpoints:

- `GET /health` - Service health check
- `GET /health/risk` - Risk calculator health
- `GET /health/analytics` - Analytics engine health

## Monitoring

- Logs: Cloud Logging
- Metrics: Cloud Monitoring
- Traces: Cloud Trace
- Alerts: Configured via Cloud Monitoring alerting policies

## Next Steps

1. Complete Compliance Service database setup
2. Build Risk Dashboard React frontend
3. Deploy all Sprint 03 components
4. End-to-end integration testing
