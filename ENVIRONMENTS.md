# 🌍 Fusion Prime - Environment Configuration

**Purpose**: Complete environment setup and configuration guide
**Target Users**: Developers, DevOps engineers, system administrators
**Time to Complete**: 15 minutes per environment

---

## 🎯 Quick Navigation

- **[Environment Overview](#-environment-overview)** - Three-tier architecture
- **[Local Development](#-local-development)** - Docker Compose setup
- **[Testnet Deployment](#-testnet-deployment)** - GCP test environment
- **[Production Deployment](#-production-deployment)** - GCP production environment
- **[Environment Variables](#-environment-variables)** - Configuration reference
- **[Troubleshooting](#-troubleshooting)** - Common issues and solutions

---

## 📊 Environment Overview

Fusion Prime uses a **four-tier deployment strategy** to ensure safe, tested code reaches production.

| Environment | Blockchain | Cloud | Purpose | Cost | Speed |
|-------------|------------|-------|---------|------|-------|
| **local** | Anvil (chain ID: 31337) | Docker Compose | Development & Testing | $0 | Instant |
| **dev** | Sepolia Testnet (11155111) | GCP Dev Project | Integration & CI/CD | ~$1/day | 12s blocks |
| **staging** | Sepolia Testnet (11155111) | GCP Staging Project | Pre-production Validation | ~$2/day | 12s blocks |
| **production** | Ethereum Mainnet (1) | GCP Prod Project | Live Traffic | $$$$ | 12s blocks |

### Environment Flow

```
local (Docker) → dev (GCP + Testnet) → staging (GCP + Testnet) → production (GCP + Mainnet)
     ↓                  ↓                       ↓                         ↓
  Developer          CI/CD                 UAT/QA                  Live Users
  Testing         Auto-deploy           Final checks              Real traffic
```

---

## 🏠 Local Development

**Purpose**: Development, unit tests, integration tests, rapid iteration
**Cost**: $0 (runs on your machine)
**Time**: 15 minutes setup

### Infrastructure

- **Blockchain**: Anvil (local Ethereum node)
  - Instant block times
  - Pre-funded test accounts
  - Full debugging capabilities
  - Reset state anytime
- **Services**: Docker Compose
  - PostgreSQL database
  - Pub/Sub emulator
  - Redis cache
  - All backend microservices

### Setup

```bash
# 1. Copy environment template
cp env.local.example .env.local

# 2. Start local environment
make dev

# 3. Verify services
curl http://localhost:8000/health  # Settlement
curl http://localhost:8001/health/ # Risk Engine
curl http://localhost:8002/health/ # Compliance
```

### Configuration

**File**: `.env.local`
```bash
# Blockchain
RPC_URL=http://localhost:8545
CHAIN_ID=31337
ENVIRONMENT=local

# Services
SETTLEMENT_SERVICE_URL=http://localhost:8000
RISK_ENGINE_SERVICE_URL=http://localhost:8001
COMPLIANCE_SERVICE_URL=http://localhost:8002

# Database
DATABASE_URL=sqlite:///./settlement.db
PUBSUB_EMULATOR_HOST=localhost:8085
REDIS_URL=redis://localhost:6379

# GCP (local)
GCP_PROJECT=fusion-prime-dev
REGION=us-central1
```

### When to Use

- ✅ Always first - before any remote deployment
- ✅ Unit tests and integration tests
- ✅ Feature development and debugging
- ✅ Local experimentation

---

## 🔧 Dev Environment

**Purpose**: Integration testing and CI/CD automation
**Cost**: ~$50/month (GCP free tier + testnet fees)
**Time**: 2 hours setup

### Infrastructure

- **Blockchain**: Sepolia testnet
  - Real blockchain with test tokens
  - 12-second block times
  - Free testnet ETH from faucets
- **Cloud**: GCP dev project
  - Cloud Run services
  - Cloud SQL database
  - Pub/Sub messaging
  - Secret Manager

### Setup

```bash
# 1. Create GCP project
gcloud projects create fusion-prime-dev
gcloud config set project fusion-prime-dev

# 2. Deploy infrastructure
cd infra/terraform/environments/dev
terraform init
terraform apply

# 3. Deploy services
make deploy-dev
```

### Configuration

**File**: `.env.dev`
```bash
# Blockchain
ETH_RPC_URL=https://sepolia.g.alchemy.com/v2/YOUR_ALCHEMY_KEY
CHAIN_ID=11155111
ENVIRONMENT=dev

# Smart Contracts
ESCROW_FACTORY_ADDRESS=0x0F146104422a920E90627f130891bc948298d6F8

# GCP Services
SETTLEMENT_SERVICE_URL=https://settlement-service-dev-961424092563.us-central1.run.app
DATABASE_URL=postgresql://settlement_user:YOUR_PASSWORD@/settlement_db?host=/cloudsql/fusion-prime-dev:us-central1:fusion-prime-db

# GCP Project
GCP_PROJECT=fusion-prime-dev
REGION=us-central1
```

### When to Use

- ✅ After merging to dev branch
- ✅ CI/CD automated deployments
- ✅ Integration testing with real blockchain
- ✅ API contract validation
- ✅ Performance testing

---

## 🎭 Staging Environment

**Purpose**: Pre-production validation and UAT
**Cost**: ~$75/month (production-like resources)
**Time**: 2 hours setup

### Infrastructure

- **Blockchain**: Sepolia testnet (same as dev)
  - Mirrors production setup
  - Final validation before mainnet
- **Cloud**: GCP staging project
  - Production-scale resources
  - Cloud Run with HA
  - Production Cloud SQL tier
  - Full monitoring

### Setup

```bash
# 1. Create GCP project
gcloud projects create fusion-prime-staging
gcloud config set project fusion-prime-staging

# 2. Deploy infrastructure
cd infra/terraform/environments/staging
terraform init
terraform apply

# 3. Deploy services
make deploy-staging
```

### Configuration

**File**: `.env.staging`
```bash
# Blockchain
ETH_RPC_URL=https://sepolia.g.alchemy.com/v2/YOUR_ALCHEMY_KEY
CHAIN_ID=11155111
ENVIRONMENT=staging

# Smart Contracts
ESCROW_FACTORY_ADDRESS=0x0F146104422a920E90627f130891bc948298d6F8

# GCP Services
SETTLEMENT_SERVICE_URL=https://settlement-service-staging-961424092563.us-central1.run.app
DATABASE_URL=postgresql://settlement_user:YOUR_PASSWORD@/settlement_db?host=/cloudsql/fusion-prime-staging:us-central1:fusion-prime-db

# GCP Project
GCP_PROJECT=fusion-prime-staging
REGION=us-central1
```

### When to Use

- ✅ Before production deployment
- ✅ User acceptance testing (UAT)
- ✅ Final validation with production-like load
- ✅ Stakeholder demos
- ✅ Security audits

---

## 🏭 Production Environment

**Purpose**: Live traffic with mainnet integration
**Cost**: Varies (production GCP resources + mainnet gas)
**Time**: 4 hours setup

### Infrastructure

- **Blockchain**: Ethereum mainnet
  - Real ETH and tokens
  - 12-second block times
  - Production-grade security
- **Cloud**: GCP production project
  - High-availability Cloud Run
  - Production Cloud SQL
  - Enterprise Pub/Sub
  - Advanced monitoring

### Setup

```bash
# 1. Create production GCP project
gcloud projects create fusion-prime-production
gcloud config set project fusion-prime-production

# 2. Deploy production infrastructure
cd infra/terraform/environments/production
terraform init
terraform apply

# 3. Deploy services
make deploy-production
```

### Configuration

**File**: `.env.production`
```bash
# Blockchain
ETH_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_ALCHEMY_KEY
CHAIN_ID=1
ENVIRONMENT=production

# Smart Contracts
ESCROW_FACTORY_ADDRESS=0x[PRODUCTION_ADDRESS]

# GCP Services
SETTLEMENT_SERVICE_URL=https://settlement-service-prod.us-central1.run.app
DATABASE_URL=postgresql://settlement_user:YOUR_PASSWORD@/settlement_db?host=/cloudsql/fusion-prime-prod:us-central1:fusion-prime-db-prod

# GCP Project
GCP_PROJECT=fusion-prime-prod
REGION=us-central1
```

### When to Use

- ✅ Live user traffic
- ✅ Production workloads
- ✅ Revenue-generating operations
- ✅ After successful staging validation
- ✅ After security audit approval

---

## 🔧 Environment Configuration Management

### Configuration Sources

Fusion Prime uses a **hierarchical configuration system** with multiple sources:

1. **`scripts/config/environments.yaml`** - Central configuration file (hardcoded defaults)
2. **Environment variables** - Override defaults for specific deployments
3. **Secret Manager** - Sensitive values (passwords, API keys)
4. **GitHub Secrets** - CI/CD deployment credentials

### Configuration Hierarchy

```
Environment Variables (highest priority)
    ↓
GitHub Secrets (CI/CD)
    ↓
Secret Manager (GCP)
    ↓
environments.yaml (lowest priority)
```

### Hardcoded vs Configurable Values

#### 🔒 **Hardcoded in `environments.yaml`**
These values are **fixed** and should not be changed without updating the configuration file:

| Environment | GCP Project | Region | Blockchain | Chain ID |
|-------------|-------------|--------|------------|----------|
| **dev** | `fusion-prime` | `us-central1` | `anvil` | `31337` |
| **staging** | `fusion-prime` | `us-central1` | `sepolia` | `11155111` |
| **production** | `fusion-prime` | `us-central1` | `mainnet` | `1` |

#### ⚙️ **Configurable via Environment Variables**
These values can be **overridden** using environment variables:

| Variable | Purpose | Override Example |
|----------|---------|------------------|
| `GCP_PROJECT_ID` | Override GCP project | `export GCP_PROJECT_ID="my-project"` |
| `GCP_REGION` | Override GCP region | `export GCP_REGION="europe-west1"` |
| `ETHEREUM_RPC_URL` | Override RPC endpoint | `export ETHEREUM_RPC_URL="https://..."` |
| `CHAIN_ID` | Override chain ID | `export CHAIN_ID="5"` |

#### 🔐 **Required Secrets (Must be provided)**
These values are **never hardcoded** and must be provided:

| Secret | Purpose | Where to Set |
|--------|---------|--------------|
| `INFURA_KEY` | RPC provider API key | GitHub Secrets / Secret Manager |
| `DB_PASSWORD` | Database password | Secret Manager |
| `PRIVATE_KEY` | Contract deployer key | GitHub Secrets |
| `ETHERSCAN_API_KEY` | Contract verification | GitHub Secrets |

### Required Variables

| Variable | local | dev | staging | production | Description | Required |
|----------|-------|-----|---------|------------|-------------|----------|
| `ETH_RPC_URL` | `http://localhost:8545` | Sepolia RPC | Sepolia RPC | Mainnet RPC | Blockchain RPC endpoint | ✅ |
| `CHAIN_ID` | `31337` | `11155111` | `11155111` | `1` | Blockchain chain ID | ✅ |
| `ENVIRONMENT` | `local` | `dev` | `staging` | `production` | Environment identifier | ✅ |
| `DATABASE_URL` | SQLite/PostgreSQL | Cloud SQL | Cloud SQL | Cloud SQL | Database connection string | ✅ |
| `GCP_PROJECT` | `fusion-prime-local` | `fusion-prime-dev` | `fusion-prime-staging` | `fusion-prime-production` | GCP project ID | ✅ |
| `INFURA_KEY` | N/A | Required | Required | Required | RPC provider API key | ✅ |
| `DB_PASSWORD` | N/A | Required | Required | Required | Database password | ✅ |
| `PRIVATE_KEY` | Optional | Required | Required | Required | Contract deployer key | ⚠️ |

### Service URLs

| Service | local | dev | staging | production |
|---------|-------|-----|---------|------------|
| **Settlement** | `http://localhost:8000` | `https://settlement-dev.run.app` | `https://settlement-staging.run.app` | `https://settlement-prod.run.app` |
| **Risk Engine** | `http://localhost:8001` | `https://risk-dev.run.app` | `https://risk-staging.run.app` | `https://risk-prod.run.app` |
| **Compliance** | `http://localhost:8002` | `https://compliance-dev.run.app` | `https://compliance-staging.run.app` | `https://compliance-prod.run.app` |

### Database Configuration

| Environment | Type | Connection | Backup | HA |
|-------------|------|------------|--------|-----|
| **local** | PostgreSQL (Docker) | localhost:5432 | Manual | No |
| **dev** | Cloud SQL | Managed | Daily | No |
| **staging** | Cloud SQL | Managed | Daily | Yes |
| **production** | Cloud SQL | Managed | Continuous | Yes |

---

## 📋 Configuration Management Guide

### Quick Configuration Checklist

Before deploying, ensure you have:

- [ ] **GCP Project**: Created and configured
- [ ] **RPC Provider**: API key for blockchain access
- [ ] **Database**: Cloud SQL instance (for remote environments)
- [ ] **Secrets**: Stored in Secret Manager or GitHub Secrets
- [ ] **Service Account**: GCP service account with proper permissions

### Environment-Specific Setup

#### 🏠 **Local Development**
```bash
# 1. Copy environment template
cp env.local.example .env.local

# 2. No additional configuration needed
# Uses hardcoded values from environments.yaml
```

#### 🔧 **Dev Environment**
```bash
# 1. Set required environment variables
export GCP_PROJECT_ID="fusion-prime-dev"
export ETHEREUM_RPC_URL="https://sepolia.infura.io/v3/YOUR_INFURA_KEY"
export CHAIN_ID="11155111"

# 2. Store secrets in Secret Manager
gcloud secrets create db-password --data-file=- <<< "your-db-password"
gcloud secrets create infura-key --data-file=- <<< "your-infura-key"

# 3. Deploy
./scripts/deploy-unified.sh --env dev --services all
```

#### 🎭 **Staging Environment**
```bash
# 1. Set environment variables
export GCP_PROJECT_ID="fusion-prime-staging"
export ETHEREUM_RPC_URL="https://sepolia.infura.io/v3/YOUR_INFURA_KEY"
export CHAIN_ID="11155111"

# 2. Store secrets
gcloud secrets create db-password --data-file=- <<< "your-staging-db-password"
gcloud secrets create infura-key --data-file=- <<< "your-infura-key"

# 3. Deploy
./scripts/deploy-unified.sh --env staging --services all --tag v1.0.0
```

#### 🏭 **Production Environment**
```bash
# 1. Set environment variables
export GCP_PROJECT_ID="fusion-prime-production"
export ETHEREUM_RPC_URL="https://mainnet.infura.io/v3/YOUR_INFURA_KEY"
export CHAIN_ID="1"

# 2. Store secrets (use production values)
gcloud secrets create db-password --data-file=- <<< "your-production-db-password"
gcloud secrets create infura-key --data-file=- <<< "your-infura-key"
gcloud secrets create private-key --data-file=- <<< "your-deployer-private-key"

# 3. Deploy (with caution!)
./scripts/deploy-unified.sh --env production --services all --tag v1.0.0 --dry-run
# Review output, then remove --dry-run
```

### Configuration File Structure

The `scripts/config/environments.yaml` file contains:

```yaml
environments:
  dev:
    name: "Development"
    gcp_project: "fusion-prime"           # Hardcoded
    region: "us-central1"                 # Hardcoded
    blockchain:
      network: "anvil"                    # Hardcoded
      rpc_url: "http://localhost:8545"     # Hardcoded
      chain_id: 31337                     # Hardcoded
    services:
      settlement:
        memory: "1Gi"                     # Hardcoded
        cpu: "1"                          # Hardcoded
        min_instances: 0                  # Hardcoded
        max_instances: 3                  # Hardcoded
    environment_vars:
      ENVIRONMENT: "development"         # Hardcoded
      LOG_LEVEL: "DEBUG"                  # Hardcoded
```

### Override Configuration

To override hardcoded values, use environment variables:

```bash
# Override GCP project
export GCP_PROJECT_ID="my-custom-project"

# Override region
export GCP_REGION="europe-west1"

# Override RPC URL
export ETHEREUM_RPC_URL="https://custom-rpc.com"

# Override chain ID
export CHAIN_ID="5"
```

### Secret Management

#### For Manual Deployment
```bash
# Store secrets in GCP Secret Manager
gcloud secrets create db-password --data-file=- <<< "your-password"
gcloud secrets create infura-key --data-file=- <<< "your-api-key"
gcloud secrets create private-key --data-file=- <<< "your-private-key"
```

#### For CI/CD Deployment
Set these secrets in GitHub repository settings:

- `GCP_SA_KEY` - Service account JSON
- `PRIVATE_KEY` - Deployer private key
- `ETHERSCAN_API_KEY` - Contract verification key
- `INFURA_KEY` - RPC provider API key

### Configuration Validation

The deployment script validates configuration before deploying:

```bash
# Check configuration
./scripts/deploy-unified.sh --env dev --services all --dry-run

# This will show:
# - Environment variables loaded
# - Secrets accessible
# - GCP project accessible
# - RPC endpoint reachable
```

### Troubleshooting Configuration

#### Missing Environment Variables
```bash
# Check what's loaded
./scripts/deploy-unified.sh --env dev --services all --dry-run

# Common issues:
# - GCP_PROJECT_ID not set
# - ETHEREUM_RPC_URL not set
# - CHAIN_ID not set
```

#### Missing Secrets
```bash
# Check secret access
gcloud secrets versions access latest --secret="db-password"
gcloud secrets versions access latest --secret="infura-key"

# Grant access if needed
gcloud secrets add-iam-policy-binding db-password \
  --member="serviceAccount:your-service@project.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

#### RPC Connection Issues
```bash
# Test RPC connection
curl -X POST -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
  $ETHEREUM_RPC_URL

# Check chain ID
curl -X POST -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}' \
  $ETHEREUM_RPC_URL
```

---

## 🚀 Environment Setup Commands

### Local Development

```bash
# Start local environment (one command!)
./scripts/setup/start_local_testing.sh

# Or use make commands
make dev

# Run tests
export TEST_ENVIRONMENT=local
pytest tests/ -v

# Stop services
docker compose down
```

### Dev Environment

```bash
# Deploy to dev (auto-triggered on push to dev branch)
git push origin dev

# Or manual deploy
make deploy-dev

# Run dev tests
export TEST_ENVIRONMENT=dev
pytest tests/remote/testnet/ -v

# Check service status
gcloud run services list --project=fusion-prime-dev --region=us-central1
```

### Staging Environment

```bash
# Deploy to staging (auto-triggered on push to staging branch)
git push origin staging

# Or manual deploy
make deploy-staging

# Run staging tests
export TEST_ENVIRONMENT=staging
pytest tests/remote/testnet/ -v

# Check service status
gcloud run services list --project=fusion-prime-staging --region=us-central1
```

### Production Environment

```bash
# Deploy to production (requires approval)
git tag v1.0.0
git push origin v1.0.0

# Or manual deploy (requires admin)
make deploy-production

# Run production smoke tests
export TEST_ENVIRONMENT=production
pytest tests/remote/production/ -v --smoke-only

# Monitor services
gcloud monitoring dashboards list --project=fusion-prime-production
```

---

## 🔍 Troubleshooting

### Common Issues

#### 1. Environment File Not Found

**Symptoms**: Services can't find environment variables
**Solution**:
```bash
# Check if environment file exists
ls -la .env.*

# Copy template if missing
cp env.local.example .env.local
```

#### 2. Database Connection Issues

**Symptoms**: Database connection errors
**Solution**:
```bash
# Check database URL format
echo $DATABASE_URL

# Test connection
python -c "import psycopg2; psycopg2.connect('$DATABASE_URL')"
```

#### 3. Service Health Check Failures

**Symptoms**: Services not responding to health checks
**Solution**:
```bash
# Check service logs
gcloud logging read "resource.type=cloud_run_revision" --limit=50

# Check service configuration
gcloud run services describe settlement-service --region=us-central1
```

#### 4. Blockchain Connection Issues

**Symptoms**: RPC connection failures
**Solution**:
```bash
# Test RPC connection
curl -X POST -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
  $RPC_URL

# Check chain ID
curl -X POST -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}' \
  $RPC_URL
```

### Environment-Specific Issues

#### local

- **Docker issues**: `docker compose down && docker compose up -d`
- **Port conflicts**: Check if ports 8000-8002, 5432, 6379, 8085, 8545 are available
- **Contracts not deployed**: Run `python tests/scripts/deploy_contracts.py`
- **Relayer not working**: Check `docker compose logs event-relayer`

#### dev

- **RPC rate limits**: Use multiple RPC providers (Alchemy, Infura)
- **Testnet ETH**: Get from faucets (https://sepoliafaucet.com)
- **GCP quotas**: Check project quotas and billing
- **CI/CD failures**: Check GitHub Actions logs

#### staging

- **Service health**: Ensure all services pass health checks
- **Load testing**: Use production-like load
- **Database migrations**: Test thoroughly before production
- **UAT sign-off**: Required before production deployment

#### production

- **Security**: All secrets in Secret Manager, no plaintext
- **Monitoring**: SLO alerts configured and tested
- **Backup**: Automated backups with tested restore procedures
- **Mainnet gas**: Monitor gas prices and optimize transactions
- **Rate limiting**: Configure and test API rate limits

---

## 📚 Related Documentation

- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Complete deployment guide
- **[QUICKSTART.md](./QUICKSTART.md)** - Local development setup
- **[TESTING.md](./TESTING.md)** - Testing strategy
- **[docs/gcp-deployment.md](./docs/gcp-deployment.md)** - GCP deployment details

---

## 🆘 Support

### Getting Help

1. **Check environment**: Verify all required variables are set
2. **Check logs**: Review service logs for errors
3. **Check connectivity**: Test database and RPC connections
4. **Review documentation**: See related docs above

### Emergency Procedures

1. **Service down**: Check health endpoints and restart services
2. **Database issues**: Check Cloud SQL status and restore from backup
3. **Blockchain issues**: Check RPC provider status and switch if needed
4. **Configuration issues**: Verify environment variables and secrets

---

**Last Updated**: 2025-01-24
**Next Review**: After environment changes
