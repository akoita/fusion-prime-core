# 🚀 Fusion Prime - Deployment Guide

**Purpose**: Comprehensive deployment guide for all environments and services
**Target Users**: Developers, DevOps engineers, system administrators
**Time to Complete**: 5 minutes (dev) to 30 minutes (production)
**Last Updated**: 2025-01-25

---

## 🎯 Quick Start

### Unified Deployment Command

```bash
# Deploy all services to dev
./scripts/deploy-unified.sh --env dev --services all

# Deploy specific services to staging
./scripts/deploy-unified.sh --env staging --services settlement,risk-engine --tag v1.0.0

# Deploy with contracts (auto-uploads to GCS registry)
./scripts/deploy-unified.sh --env dev --services all --contracts

# Dry run (test without deploying)
./scripts/deploy-unified.sh --env production --services all --tag v1.0.0 --dry-run
```

**One script, works everywhere**: Same for manual CLI and GitHub Actions CI/CD.

---

## 📋 Navigation

- **[Quick Commands](#quick-commands)** - Common deployment tasks
- **[Local Development](#local-development)** - Docker Compose setup
- **[Remote Deployment](#remote-deployment)** - GCP + Blockchain
- **[GitHub Actions](#github-actions-cicd)** - Automated deployments
- **[Troubleshooting](#troubleshooting)** - Common issues

---

## ⚡ Quick Commands

### Manual Deployment

```bash
# All environments
./scripts/deploy-unified.sh --env dev --services all
./scripts/deploy-unified.sh --env staging --services all --tag v1.0.0
./scripts/deploy-unified.sh --env production --services all --tag v1.0.0

# Specific services
./scripts/deploy-unified.sh --env dev --services settlement
./scripts/deploy-unified.sh --env staging --services settlement,risk-engine

# With smart contracts (auto-uploads to GCS registry)
./scripts/deploy-unified.sh --env dev --services all --contracts

# Options
--dry-run           # Test without deploying
--skip-build        # Use existing images
--skip-deploy       # Build only, don't deploy
```

### GitHub Actions (Automated)

```bash
# Automatic deployments
git push origin dev              # → deploys to dev
git push origin staging          # → deploys to staging
git tag v1.0.0 && git push origin v1.0.0  # → deploys to production

# Manual trigger
gh workflow run deploy.yml -f environment=dev -f services=all
```

### Health Checks

```bash
# Check deployed services
gcloud run services list --region=us-central1

# Test health endpoints
curl https://settlement-service-xxx.run.app/health
curl https://risk-engine-xxx.run.app/health/
curl https://compliance-xxx.run.app/health/
```

---

## 🔧 Contract Registry System

**Purpose**: Centralized management of smart contract resources (addresses, ABIs, metadata)
**Features**: Automatic upload, download, service updates, environment detection
**Storage**: GCS bucket with organized structure by environment and chain ID

### Contract Management Commands

```bash
# Upload contract artifacts to GCS (after manual deployment)
./scripts/gcp-contract-registry.sh upload --env dev --project fusion-prime-dev --chain-id 11155111

# Download contract artifacts from GCS
./scripts/gcp-contract-registry.sh download --env dev --project fusion-prime-dev --chain-id 11155111

# List available contract deployments
./scripts/gcp-contract-registry.sh list --project fusion-prime-dev

# Get contract addresses (for environment variables)
./scripts/gcp-contract-registry.sh get-addresses --project fusion-prime-dev --chain-id 11155111

# Get deployment metadata
./scripts/gcp-contract-registry.sh get-metadata --env dev --project fusion-prime-dev --chain-id 11155111

# Update Cloud Run services with contract addresses
./scripts/update-services-contracts.sh --project fusion-prime-dev
```

### Automatic Contract Upload

The `deploy-unified.sh` script automatically uploads contract artifacts to GCS after deployment:

```bash
# This automatically uploads contracts to GCS registry
./scripts/deploy-unified.sh --env dev --services all --contracts
```

### Contract Registry Structure

```
gs://{project}-contract-registry/
├── contracts/
│   ├── dev/
│   │   ├── 11155111/          # Sepolia testnet
│   │   │   ├── deployment.json
│   │   │   ├── metadata.json
│   │   │   ├── EscrowFactory.json
│   │   │   └── Escrow.json
│   │   └── 31337/             # Anvil local
│   ├── staging/
│   │   └── 11155111/
│   └── production/
│       └── 1/                 # Ethereum mainnet
```

### Service Integration

Services automatically load contract resources using the Contract Registry library:

```python
from services.shared.contract_registry import ContractRegistry

# Auto-detects environment and loads contract resources
registry = ContractRegistry()
factory_address = registry.get_contract_address('EscrowFactory')
factory_abi = registry.get_contract_abi('EscrowFactory')
```

**Loading Priority:**
1. **GCS URLs** (from environment variables)
2. **Local files** (fallback for local development)
3. **Contract Registry** (GCS lookup)

---

## 🏠 Local Development

**Purpose**: Development, testing, and CI/CD validation
**Cost**: $0 (runs on your machine)
**Time**: 30 minutes first time, 5 minutes thereafter
**Prerequisites**: Docker, Foundry, Python 3.11+, Node.js 18+

### Quick Start

```bash
# Clone and setup
git clone <repository>
cd fusion-prime
make setup

# Start local environment
make dev

# Run tests
./scripts/test.sh local
```

### Architecture

- **Anvil**: Local Ethereum node (instant blocks, free)
- **Docker Compose**: Backend services (settlement, relayer, risk, compliance)
- **SQLite**: Local database
- **Local Pub/Sub**: Message queue simulation

### Services

| Service | URL | Purpose |
|---------|-----|---------|
| **Settlement Service** | `http://localhost:8000` | Core settlement logic |
| **Risk Engine Service** | `http://localhost:8001` | Risk calculations |
| **Compliance Service** | `http://localhost:8002` | KYC/AML workflows |
| **Event Relayer** | Background job | Blockchain event processing |
| **Database** | `sqlite:///./settlement.db` | Local SQLite |
| **Blockchain** | `http://localhost:8545` | Anvil node |

### Environment Variables

```bash
# Required for local development
export DATABASE_URL="sqlite:///./settlement.db"
export PUBSUB_EMULATOR_HOST="localhost:8085"
export GCP_PROJECT="fusion-prime-dev"
export REDIS_URL="redis://localhost:6379"
```

### Testing

```bash
# Run all tests
./scripts/test.sh local

# Run specific test suites
python -m pytest tests/local/ -v
python -m pytest tests/local/test_e2e.py -v
```

---

---

## 🌐 Remote Deployment

**Purpose**: Deploy to GCP Cloud Run + Blockchain (dev/staging/production)
**Cost**: ~$50/month (dev/staging), varies (production)
**Time**: 15-20 minutes
**Prerequisites**: GCP project, blockchain RPC access

### Environment Overview

| Environment | Blockchain | Auto-Deploy | Purpose |
|-------------|------------|-------------|---------|
| **dev** | Sepolia Testnet | Push to `dev` | Development testing |
| **staging** | Sepolia Testnet | Push to `staging` | Pre-production validation |
| **production** | Ethereum Mainnet | Tag `v*` | Live traffic |

### Deploy to Remote Environment

**Step 1**: Configure environment variables

> 📋 **Configuration Management**: Fusion Prime uses a hierarchical configuration system. See [ENVIRONMENTS.md](./ENVIRONMENTS.md) for complete details.

```bash
# Required environment variables (override hardcoded values)
export GCP_PROJECT_ID="fusion-prime"                    # Override from environments.yaml
export GCP_REGION="us-central1"                        # Override from environments.yaml
export ETHEREUM_RPC_URL="https://sepolia.infura.io/v3/YOUR_KEY"  # Override RPC URL
export CHAIN_ID=11155111                               # Override chain ID

# Required secrets (never hardcoded)
export PRIVATE_KEY="0x..."                             # For contract deployment
export ETHERSCAN_API_KEY="..."                         # For contract verification

# Contract Registry (auto-configured by deployment script)
export CONTRACT_REGISTRY_BUCKET="fusion-prime-contract-registry"
export CONTRACT_REGISTRY_CHAIN_ID="11155111"
export ESCROW_FACTORY_ABI_URL="gs://fusion-prime-contract-registry/contracts/dev/11155111/EscrowFactory.json"
export ESCROW_ABI_URL="gs://fusion-prime-contract-registry/contracts/dev/11155111/Escrow.json"

# Optional overrides
export INFURA_KEY="your-infura-key"                    # If using Infura
export DB_PASSWORD="your-db-password"                  # If using Cloud SQL
```

**Configuration Sources (in priority order):**
1. **Environment Variables** (highest priority)
2. **GitHub Secrets** (CI/CD)
3. **Secret Manager** (GCP)
4. **environments.yaml** (lowest priority)

**Step 2**: Deploy
```bash
# Deploy all services to dev (auto-uploads contracts to GCS)
./scripts/deploy-unified.sh --env dev --services all --contracts

# Deploy to staging with specific version (auto-uploads contracts to GCS)
./scripts/deploy-unified.sh --env staging --services all --tag v1.0.0 --contracts

# Production deployment (use caution!)
./scripts/deploy-unified.sh --env production --services all --tag v1.0.0 --contracts --dry-run
# Review dry-run output, then remove --dry-run
```

**Step 2a**: Manual Contract Management (if needed)
```bash
# Upload contracts after manual deployment
./scripts/gcp-contract-registry.sh upload --env dev --project fusion-prime-dev --chain-id 11155111

# Update services with contract addresses
./scripts/update-services-contracts.sh --project fusion-prime-dev
```

**Step 3**: Validate
```bash
# Check services
gcloud run services list --region=$GCP_REGION

# Health checks
curl $(gcloud run services describe settlement-service --region=$GCP_REGION --format="value(status.url)")/health
```

### Configuration Management

#### 🔧 **Configuration Sources**

Fusion Prime uses a **hierarchical configuration system**:

1. **`scripts/config/environments.yaml`** - Hardcoded defaults
2. **Environment Variables** - Override defaults
3. **Secret Manager** - Sensitive values
4. **GitHub Secrets** - CI/CD credentials

#### 🔒 **Hardcoded Values (in `environments.yaml`)**

These values are **fixed** and should not be changed:

| Environment | GCP Project | Region | Blockchain | Chain ID |
|-------------|-------------|--------|------------|----------|
| **dev** | `fusion-prime` | `us-central1` | `anvil` | `31337` |
| **staging** | `fusion-prime` | `us-central1` | `sepolia` | `11155111` |
| **production** | `fusion-prime` | `us-central1` | `mainnet` | `1` |

#### ⚙️ **Configurable Values (Environment Variables)**

Override hardcoded values using environment variables:

```bash
# Override GCP project
export GCP_PROJECT_ID="my-custom-project"

# Override region
export GCP_REGION="europe-west1"

# Override RPC endpoint
export ETHEREUM_RPC_URL="https://custom-rpc.com"

# Override chain ID
export CHAIN_ID="5"
```

#### 🔐 **Required Secrets (Never Hardcoded)**

These values must be provided and are never hardcoded:

```bash
# Store secrets in Secret Manager
gcloud secrets create db-password --data-file=- <<< "your-db-password"
gcloud secrets create infura-key --data-file=- <<< "your-infura-key"
gcloud secrets create private-key --data-file=- <<< "your-deployer-private-key"

# Or set in GitHub Secrets (for CI/CD)
# GCP_SA_KEY, PRIVATE_KEY, ETHERSCAN_API_KEY, INFURA_KEY
```

#### 📋 **Service Configuration**

Each service gets configuration from multiple sources:

```bash
# Settlement service config
gcloud secrets create settlement-service-config-test \
  --data-file=- <<EOF
{
  "database_url": "postgresql://user:pass@host:5432/db",
  "pubsub_project": "fusion-prime-testnet",
  "redis_url": "redis://host:6379"
}
EOF

# Risk engine config
gcloud secrets create risk-engine-config-test \
  --data-file=- <<EOF
{
  "database_url": "postgresql://user:pass@host:5432/db",
  "risk_data_provider": "coingecko",
  "api_key": "your-api-key"
}
EOF
```

#### 🔍 **Configuration Validation**

The deployment script validates configuration before deploying:

```bash
# Check configuration without deploying
./scripts/deploy-unified.sh --env dev --services all --dry-run

# This validates:
# - Environment variables loaded
# - Secrets accessible
# - GCP project accessible
# - RPC endpoint reachable
# - Database connection
```

### Testing

```bash
# Run testnet tests
./scripts/test.sh testnet

# Run specific testnet tests
python -m pytest tests/remote/testnet/ -v
```

---

## 🏭 Production Deployment

**Purpose**: Full-scale deployment with mainnet integration
**Cost**: Varies (production GCP resources)
**Time**: 4 hours first time, 1 hour for updates
**Prerequisites**: Production GCP project, mainnet access, security review

### Prerequisites

1. **Security Review**
   - [ ] Security audit completed
   - [ ] Penetration testing passed
   - [ ] Compliance review approved
   - [ ] Incident response plan ready

2. **Infrastructure Setup**
   ```bash
   # Production infrastructure
   cd infra/terraform/production
   terraform init
   terraform apply
   ```

### Deploy Services

```bash
# Deploy all services to production
make deploy-production

# Or deploy with specific version
make deploy-production VERSION=v1.0.0
```

### Configuration

Production configuration with enhanced security:

```bash
# Settlement service production config
gcloud secrets create settlement-service-config-prod \
  --data-file=- <<EOF
{
  "database_url": "postgresql://user:pass@host:5432/db",
  "pubsub_project": "fusion-prime-prod",
  "redis_url": "redis://host:6379",
  "monitoring": {
    "enabled": true,
    "alerting": true
  },
  "security": {
    "rate_limiting": true,
    "authentication": "oauth2"
  }
}
EOF
```

### Monitoring

```bash
# Check service health
gcloud run services list --region=us-central1

# View logs
gcloud logging read "resource.type=cloud_run_revision" --limit=50

# Check metrics
gcloud monitoring dashboards list
```

---

## 🔧 Service-Specific Deployment

### Settlement Service

**Purpose**: Core settlement logic and escrow management
**Deployment**: Cloud Run service
**Configuration**: Secret Manager

```bash
# Deploy settlement service
gcloud builds submit --config=services/settlement/cloudbuild.yaml \
  --substitutions=_SERVICE=settlement,_CONFIG_SECRET=settlement-service-config

# Check deployment
gcloud run services describe settlement-service --region=us-central1
```

### Risk Engine Service

**Purpose**: Risk calculations and portfolio analytics
**Deployment**: Cloud Run service
**Configuration**: Secret Manager

```bash
# Deploy risk engine service
gcloud builds submit --config=services/risk-engine/cloudbuild.yaml \
  --substitutions=_SERVICE=risk-engine,_CONFIG_SECRET=risk-engine-config

# Check deployment
gcloud run services describe risk-engine-service --region=us-central1
```

### Compliance Service

**Purpose**: KYC/AML workflows and identity verification
**Deployment**: Cloud Run service
**Configuration**: Secret Manager

```bash
# Deploy compliance service
gcloud builds submit --config=services/compliance/cloudbuild.yaml \
  --substitutions=_SERVICE=compliance,_CONFIG_SECRET=compliance-config

# Check deployment
gcloud run services describe compliance-service --region=us-central1
```

### Event Relayer

**Purpose**: Blockchain event processing and Pub/Sub publishing
**Deployment**: Cloud Run job with automated scheduling
**Configuration**: Environment variables

```bash
# Deploy event relayer as Cloud Run job
gcloud run jobs create event-relayer \
  --image gcr.io/fusion-prime/event-relayer:latest \
  --region us-central1 \
  --memory 1Gi \
  --cpu 1 \
  --parallelism 1 \
  --task-count 1 \
  --max-retries 3 \
  --task-timeout 3600

# Execute job manually
gcloud run jobs execute event-relayer --region=us-central1
```

**Cloud Scheduler (Automated Execution):**

The relayer can be configured to run automatically using Cloud Scheduler:

```bash
# Setup automated relayer execution (every 5 minutes)
./scripts/setup-relayer-scheduler.sh

# Custom schedule (every 10 minutes)
./scripts/setup-relayer-scheduler.sh --schedule "*/10 * * * *"

# Custom schedule (hourly)
./scripts/setup-relayer-scheduler.sh --schedule "0 * * * *"

# Delete scheduler
./scripts/setup-relayer-scheduler.sh --delete
```

**Automated Setup During Deployment:**

When deploying the relayer using `deploy-unified.sh`, the Cloud Scheduler is automatically configured:

```bash
# This automatically sets up the scheduler
./scripts/deploy-unified.sh --env dev --services relayer
```

**Scheduler Status:**

```bash
# Check scheduler status
gcloud scheduler jobs describe relayer-scheduler --location=us-central1

# List recent executions
gcloud run jobs executions list --job=escrow-event-relayer --region=us-central1

# View execution logs
gcloud logging read "resource.type=cloud_run_job" --limit=50
```

---

## 🔍 Troubleshooting

### Common Issues

#### 1. Service Health Check Failures

**Symptoms**: Services not starting, health checks failing
**Solution**:
```bash
# Check service logs
gcloud logging read "resource.type=cloud_run_revision" --limit=100

# Check service configuration
gcloud run services describe settlement-service --region=us-central1

# Restart service
gcloud run services update settlement-service --region=us-central1
```

#### 2. Database Connection Issues

**Symptoms**: Database connection errors, timeout issues
**Solution**:
```bash
# Check Cloud SQL instance
gcloud sql instances describe fusion-prime-db

# Check VPC connector
gcloud compute networks vpc-access connectors list --region=us-central1

# Test database connection
gcloud sql connect fusion-prime-db --user=postgres
```

#### 3. Secret Manager Access Issues

**Symptoms**: Permission denied errors when accessing secrets
**Solution**:
```bash
# Check IAM permissions
gcloud secrets get-iam-policy settlement-service-config

# Grant necessary permissions
gcloud secrets add-iam-policy-binding settlement-service-config \
  --member="serviceAccount:settlement-service@fusion-prime.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

#### 4. Build Failures

**Symptoms**: Cloud Build failures, image push errors
**Solution**:
```bash
# Check build logs
gcloud builds log [BUILD_ID]

# Check Artifact Registry
gcloud artifacts repositories list --location=us-central1

# Retry build
gcloud builds submit --config=cloudbuild.yaml
```

### Performance Issues

#### 1. Slow Service Startup

**Symptoms**: Services taking >30 seconds to start
**Solution**:
- Increase memory allocation
- Optimize Docker images
- Check dependency loading

#### 2. High Memory Usage

**Symptoms**: Services hitting memory limits
**Solution**:
- Increase memory allocation
- Optimize code for memory usage
- Check for memory leaks

#### 3. Database Performance

**Symptoms**: Slow database queries, connection timeouts
**Solution**:
- Check database metrics
- Optimize queries
- Consider read replicas

---

## 📊 Monitoring and Observability

### Event Relayer Management

```bash
# Setup automated relayer (Cloud Scheduler)
./scripts/setup-relayer-scheduler.sh

# Execute relayer manually (one-time)
gcloud run jobs execute escrow-event-relayer --region=us-central1

# Check scheduler status
gcloud scheduler jobs describe relayer-scheduler --location=us-central1

# List recent executions
gcloud run jobs executions list --job=escrow-event-relayer --region=us-central1 --limit=5
```

### Health Checks

```bash
# Check all services
curl http://localhost:8000/health  # Settlement
curl http://localhost:8001/health/  # Risk Engine
curl http://localhost:8002/health/  # Compliance

# Check Cloud Run services
gcloud run services list --region=us-central1
```

### Logging

```bash
# View service logs
gcloud logging read "resource.type=cloud_run_revision" --limit=100

# Filter by service
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=settlement-service" --limit=50
```

### Metrics

```bash
# Check Cloud Run metrics
gcloud monitoring metrics list --filter="resource.type=cloud_run_revision"

# View dashboards
gcloud monitoring dashboards list
```

---

## 🔄 Rollback Procedures

### Service Rollback

```bash
# List service revisions
gcloud run revisions list --service=settlement-service --region=us-central1

# Rollback to previous revision
gcloud run services update-traffic settlement-service \
  --to-revisions=settlement-service-00001-abc=100 \
  --region=us-central1
```

## 🗄️ Database Migration Process

### Overview
Fusion Prime uses **Cloud SQL PostgreSQL** with GCP-native migration tools for production. This section covers the recommended migration workflow following GCP best practices.

> 📖 **Full Documentation:** See `DATABASE_SETUP.md` and `docs/CLOUD_SQL_MIGRATION_GUIDE.md` for complete details.

### Production Migration (Recommended)

**Quick 4-Step Process:**

```bash
# 1. Create migration SQL file
cat > /tmp/migration.sql << 'EOF'
CREATE TABLE IF NOT EXISTS my_table (
    id VARCHAR(128) PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
EOF

# 2. Upload to GCS
gsutil cp /tmp/migration.sql gs://fusion-prime-migrations/

# 3. Grant Cloud SQL service account access (first time only)
SA=$(gcloud sql instances describe fusion-prime-db-a504713e \
  --project=fusion-prime \
  --format="value(serviceAccountEmailAddress)")
gsutil iam ch serviceAccount:${SA}:objectViewer gs://fusion-prime-migrations

# 4. Import migration
gcloud sql import sql fusion-prime-db-a504713e \
  gs://fusion-prime-migrations/migration.sql \
  --database=settlement_db \
  --user=settlement_user \
  --project=fusion-prime \
  --quiet
```

### Pre-Deployment Checklist

Before deploying any database changes:

- [ ] **Backup database**
  ```bash
  gcloud sql backups create \
    --instance=fusion-prime-db-a504713e \
    --project=fusion-prime \
    --description="Pre-migration backup $(date +%Y-%m-%d)"
  ```

- [ ] **Test in staging first**
  ```bash
  # Apply to staging instance
  gcloud sql import sql STAGING_INSTANCE gs://fusion-prime-migrations/migration.sql \
    --database=settlement_db --project=fusion-prime-staging

  # Run integration tests
  ./scripts/test/remote.sh all
  ```

- [ ] **Prepare rollback script**
  ```bash
  cat > /tmp/rollback.sql << 'EOF'
  DROP TABLE IF EXISTS my_table CASCADE;
  EOF
  gsutil cp /tmp/rollback.sql gs://fusion-prime-migrations/
  ```

- [ ] **Notify team** of maintenance window

### Environment-Specific Setup

#### Local Development (Docker Compose)
```bash
# Auto-migration on startup
docker-compose up -d settlement-service

# Check logs
docker-compose logs settlement-service | grep "Database tables"
```

#### Development with Alembic
```bash
cd services/settlement

# Create new migration
poetry run alembic revision --autogenerate -m "Add new column"

# Apply locally
poetry run alembic upgrade head
```
```

**Create custom migration:**
```bash
cd services/settlement
poetry run alembic revision -m "Custom database changes"
```

### Migration Management

**Check migration status:**
```bash
cd services/settlement
poetry run alembic current
poetry run alembic history
```

**Run specific migration:**
```bash
cd services/settlement
poetry run alembic upgrade <revision_id>
```

**Rollback migrations:**
```bash
cd services/settlement
poetry run alembic downgrade -1
poetry run alembic downgrade <revision_id>
```

### Database Rollback

**Alembic rollback:**
```bash
cd services/settlement
poetry run alembic downgrade -1
```

**Emergency SQL rollback:**
```sql
-- Connect to database and run manually
DROP TABLE IF EXISTS webhook_subscriptions;
DROP TABLE IF EXISTS settlement_commands;
```

**Cloud SQL backup restore:**
```bash
# List database backups
gcloud sql backups list --instance=fusion-prime-db

# Restore from backup
gcloud sql backups restore [BACKUP_ID] --instance=fusion-prime-db
```

---

## 🔄 Script Migration Guide

**Recent Changes**: Several deployment scripts have been deprecated and removed to simplify the deployment process.

### Deprecated Scripts (Removed)

| Old Script | Replacement | Reason |
|------------|-------------|---------|
| `update-cloud-deployment.sh` | `update-services-contracts.sh` | Superseded by contract registry system |
| `update-contract-address.sh` | `deploy-unified.sh --contracts` | Manual approach replaced by automation |
| `update-contract-addresses.sh` | `deploy-unified.sh --contracts` | Redundant with unified deployment |
| `update-env-test.sh` | Copy from `env.dev.example` | One-time setup script |
| `upload-contracts.sh` | `gcp-contract-registry.sh upload` | Redundant wrapper script |

### Migration Commands

```bash
# OLD: Manual contract address updates
./scripts/update-cloud-deployment.sh 0x123...
./scripts/update-contract-address.sh 0x123...
./scripts/update-contract-addresses.sh --env dev

# NEW: Automated contract management
./scripts/deploy-unified.sh --env dev --services all --contracts
./scripts/update-services-contracts.sh --project fusion-prime-dev
./scripts/gcp-contract-registry.sh upload --env dev --project fusion-prime-dev
```

### Benefits of New System

1. **Automated**: Contract addresses automatically extracted and uploaded
2. **Centralized**: All contract resources managed in GCS registry
3. **Consistent**: Same process for all environments
4. **Reliable**: Built-in error handling and validation
5. **Maintainable**: Single source of truth for contract management

---

## 📚 Related Documentation

- **[QUICKSTART.md](./QUICKSTART.md)** - Local development setup
- **[TESTING.md](./TESTING.md)** - Testing strategy and execution
- **[ENVIRONMENTS.md](./ENVIRONMENTS.md)** - Environment configuration
- **[docs/gcp-deployment.md](./docs/gcp-deployment.md)** - GCP deployment details
- **[docs/architecture/](./docs/architecture/)** - Architecture patterns
- **[docs/SMART_CONTRACT_STRATEGY.md](./docs/SMART_CONTRACT_STRATEGY.md)** - Smart contract resource management
- **[docs/GCP_CONTRACT_MANAGEMENT.md](./docs/GCP_CONTRACT_MANAGEMENT.md)** - Contract registry system
- **[docs/SERVICE_ABI_ACCESS.md](./docs/SERVICE_ABI_ACCESS.md)** - Service ABI access patterns

---

## 🆘 Support

### Getting Help

1. **Check logs**: `gcloud logging read "resource.type=cloud_run_revision"`
2. **Check service status**: `gcloud run services list`
3. **Review documentation**: See related docs above
4. **Contact team**: Create issue in repository

### Emergency Procedures

1. **Service down**: Check health endpoints and logs
2. **Database issues**: Check Cloud SQL status and backups
3. **Security incident**: Follow incident response plan
4. **Performance issues**: Check metrics and scale services

---

**Last Updated**: 2025-01-26
**Next Review**: After major deployment changes

---

## 🤖 GitHub Actions CI/CD

### Workflows

**CI Workflow** (`.github/workflows/ci.yml`):
- Runs on: Push, Pull Request
- Tests: Smart contracts, Python services, security, quality
- Time: 10-15 minutes

**Deploy Workflow** (`.github/workflows/deploy.yml`):
- Auto-deploys on push to dev/staging or version tags
- Uses same `deploy-unified.sh` script as manual deployment
- Includes health check validation

### Automatic Deployments

```bash
# Push to dev → auto-deploys to dev environment
git push origin dev

# Push to staging → auto-deploys to staging environment
git push origin staging

# Tag and push → auto-deploys to production
git tag v1.0.0
git push origin v1.0.0
```

### Manual Trigger

```bash
# Trigger deployment manually
gh workflow run deploy.yml \
  -f environment=dev \
  -f services=all \
  -f deploy_contracts=true

# Check workflow status
gh run list --workflow=deploy.yml
gh run watch
```

### Required Secrets

Set in GitHub repository settings (Settings → Secrets and variables → Actions):

**Secrets**:
- `GCP_SA_KEY` - Service account JSON
- `PRIVATE_KEY` - Deployer private key (for contracts)
- `ETHERSCAN_API_KEY` - Contract verification

**Variables**:
- `GCP_PROJECT_ID` - GCP project ID
- `GCP_REGION` - GCP region (default: us-central1)
- `ETHEREUM_RPC_URL` - Blockchain RPC endpoint
- `CHAIN_ID` - Target chain ID (11155111 for Sepolia, 1 for Mainnet)
