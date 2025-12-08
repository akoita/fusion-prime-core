# 🔧 Fusion Prime - Configuration Management Guide

**Purpose**: Complete guide to environment configuration, secrets management, and deployment settings
**Target Users**: Developers, DevOps engineers, system administrators
**Last Updated**: 2025-01-25

---

## 🎯 Quick Navigation

- **[Configuration Overview](#-configuration-overview)** - How configuration works
- **[Environment Setup](#-environment-setup)** - Step-by-step configuration
- **[Secrets Management](#-secrets-management)** - Handling sensitive data
- **[Deployment Configuration](#-deployment-configuration)** - CI/CD and manual deployment
- **[Troubleshooting](#-troubleshooting)** - Common configuration issues

---

## 📊 Configuration Overview

### Configuration Hierarchy

Fusion Prime uses a **hierarchical configuration system** with multiple sources:

```
Environment Variables (highest priority)
    ↓
.env files (manual loading)
    ↓
GitHub Secrets (CI/CD)
    ↓
Secret Manager (GCP)
    ↓
environments.yaml (lowest priority)
```

### Configuration Sources

| Source | Purpose | When Used | Examples |
|--------|---------|-----------|----------|
| **`scripts/config/environments.yaml`** | Hardcoded defaults | Always | GCP project, region, blockchain settings |
| **Environment Variables** | Override defaults | Manual deployment | `GCP_PROJECT_ID`, `ETHEREUM_RPC_URL` |
| **Secret Manager** | Sensitive values | GCP deployment | Database passwords, API keys |
| **`.env` files** | Manual loading | Local development, testing | `source .env.local` |
| **GitHub Secrets** | CI/CD credentials | Automated deployment | Service account keys, private keys |

---

## 📁 `.env` Files Usage

### **`.env` Files Are NOT Deprecated**

The `.env` files are **still actively used** for local development and testing, but they work alongside the new configuration system.

### **Available `.env` Files:**

| File | Purpose | When to Use |
|------|---------|-------------|
| **`env.local.example`** | Local development template | Copy to `.env.local` for local dev |
| **`env.dev.example`** | Dev environment template | Copy to `.env.dev` for dev environment |
| **`env.production.example`** | Production template | Copy to `.env.production` for production |
| **`env.multi-chain.example`** | Multi-chain testing | Copy to `.env` for multi-chain tests |
| **`contracts/env.example`** | Contract deployment | Copy to `contracts/.env` for contract deployment |

### **How to Use `.env` Files:**

#### **Local Development:**
```bash
# 1. Copy template
cp env.local.example .env.local

# 2. Edit values as needed
nano .env.local

# 3. Load manually when needed
source .env.local

# 4. Or use the loader script
source load_env.sh
```

#### **Dev Environment:**
```bash
# 1. Copy template
cp env.dev.example .env.dev

# 2. Edit values as needed
nano .env.dev

# 3. Load manually when needed
source .env.dev

# 4. Or use Python loader
python -c "from dotenv import load_dotenv; load_dotenv('.env.dev')"
```

#### **Testing:**
```bash
# Load test environment (use dev environment for testing)
source .env.dev

# Or use Python loader
python -c "from dotenv import load_dotenv; load_dotenv('.env.dev')"
```

#### **Production:**
```bash
# Load production environment
source .env.production

# Or use the loader script
source load_env.sh
```

### **Important Notes:**

1. **Deployment Scripts Don't Auto-Load `.env` Files** - You must set environment variables manually:
   ```bash
   # Manual deployment (no .env loading)
   export GCP_PROJECT_ID="fusion-prime-dev"
   export ETHEREUM_RPC_URL="https://sepolia.infura.io/v3/YOUR_KEY"
   ./scripts/deploy-unified.sh --env dev --services all
   ```

2. **`.env` Files Are for Manual Loading** - They don't automatically load during deployment

3. **Use `.env` Files for Local Development** - They're perfect for local testing and development

4. **Never Commit `.env` Files** - They contain secrets and should be in `.gitignore`

---

## 🏗️ Environment Setup

### Quick Start Checklist

Before deploying, ensure you have:

- [ ] **GCP Project**: Created and configured
- [ ] **RPC Provider**: API key for blockchain access
- [ ] **Database**: Cloud SQL instance (for remote environments)
- [ ] **Secrets**: Stored in Secret Manager or GitHub Secrets
- [ ] **Service Account**: GCP service account with proper permissions

### Environment-Specific Configuration

#### 🏠 **Local Development**

**Configuration**: Uses hardcoded values from `environments.yaml`
**Secrets**: None required (uses local services)

```bash
# 1. Copy environment template
cp env.local.example .env.local

# 2. No additional configuration needed
# Uses hardcoded values from environments.yaml:
# - GCP Project: fusion-prime
# - Region: us-central1
# - Blockchain: anvil (localhost:8545)
# - Chain ID: 31337
```

#### 🔧 **Dev Environment**

**Configuration**: Override defaults with environment variables
**Secrets**: Store in Secret Manager

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

**Configuration**: Override defaults with environment variables
**Secrets**: Store in Secret Manager

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

**Configuration**: Override defaults with environment variables
**Secrets**: Store in Secret Manager (use production values)

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

---

## 🔐 Secrets Management

### Secret Types

| Secret | Purpose | Where to Store | Required For |
|--------|---------|----------------|--------------|
| `db-password` | Database password | Secret Manager | Remote environments |
| `infura-key` | RPC provider API key | Secret Manager / GitHub Secrets | Remote environments |
| `private-key` | Contract deployer key | GitHub Secrets | Contract deployment |
| `etherscan-api-key` | Contract verification | GitHub Secrets | Contract verification |

### Storing Secrets

#### For Manual Deployment

```bash
# Store secrets in GCP Secret Manager
gcloud secrets create db-password --data-file=- <<< "your-db-password"
gcloud secrets create infura-key --data-file=- <<< "your-infura-key"
gcloud secrets create private-key --data-file=- <<< "your-private-key"

# Grant access to service accounts
gcloud secrets add-iam-policy-binding db-password \
  --member="serviceAccount:settlement-service@project.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

#### For CI/CD Deployment

Set these secrets in GitHub repository settings (Settings → Secrets and variables → Actions):

**Required Secrets:**
- `GCP_SA_KEY` - Service account JSON
- `PRIVATE_KEY` - Deployer private key
- `ETHERSCAN_API_KEY` - Contract verification key
- `INFURA_KEY` - RPC provider API key

**Optional Variables:**
- `GCP_PROJECT_ID` - GCP project ID
- `GCP_REGION` - GCP region (default: us-central1)
- `ETHEREUM_RPC_URL` - Blockchain RPC endpoint
- `CHAIN_ID` - Target chain ID

### Secret Access

```bash
# Check secret access
gcloud secrets versions access latest --secret="db-password"
gcloud secrets versions access latest --secret="infura-key"

# Grant access if needed
gcloud secrets add-iam-policy-binding db-password \
  --member="serviceAccount:your-service@project.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## ⚙️ Configuration Files

### `scripts/config/environments.yaml`

This file contains **hardcoded defaults** for each environment:

```yaml
environments:
  dev:
    name: "Development"
    gcp_project: "fusion-prime"           # Hardcoded
    region: "us-central1"                  # Hardcoded
    blockchain:
      network: "anvil"                     # Hardcoded
      rpc_url: "http://localhost:8545"  # Hardcoded
      chain_id: 31337                      # Hardcoded
    services:
      settlement:
        memory: "1Gi"                      # Hardcoded
        cpu: "1"                           # Hardcoded
        min_instances: 0                    # Hardcoded
        max_instances: 3                    # Hardcoded
    environment_vars:
      ENVIRONMENT: "development"           # Hardcoded
      LOG_LEVEL: "DEBUG"                   # Hardcoded
```

### Environment Variable Overrides

Override hardcoded values using environment variables:

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

### Service Configuration

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

---

## 🚀 Deployment Configuration

### Manual Deployment

```bash
# 1. Set environment variables
export GCP_PROJECT_ID="fusion-prime-dev"
export ETHEREUM_RPC_URL="https://sepolia.infura.io/v3/YOUR_KEY"
export CHAIN_ID="11155111"

# 2. Store secrets
gcloud secrets create db-password --data-file=- <<< "your-password"
gcloud secrets create infura-key --data-file=- <<< "your-key"

# 3. Deploy
./scripts/deploy-unified.sh --env dev --services all
```

### CI/CD Deployment

**Automatic deployments** triggered by Git actions:

```bash
# Push to dev → auto-deploys to dev environment
git push origin dev

# Push to staging → auto-deploys to staging environment
git push origin staging

# Tag and push → auto-deploys to production
git tag v1.0.0
git push origin v1.0.0
```

**Manual trigger** via GitHub Actions:

```bash
# Trigger deployment manually
gh workflow run deploy.yml \
  -f environment=dev \
  -f services=all \
  -f deploy_contracts=true
```

### Configuration Validation

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

---

## 🔍 Troubleshooting

### Common Configuration Issues

#### 1. Missing Environment Variables

**Symptoms**: Services fail to start, configuration errors
**Solution**:
```bash
# Check what's loaded
./scripts/deploy-unified.sh --env dev --services all --dry-run

# Common issues:
# - GCP_PROJECT_ID not set
# - ETHEREUM_RPC_URL not set
# - CHAIN_ID not set
```

#### 2. Missing Secrets

**Symptoms**: Permission denied errors when accessing secrets
**Solution**:
```bash
# Check secret access
gcloud secrets versions access latest --secret="db-password"
gcloud secrets versions access latest --secret="infura-key"

# Grant access if needed
gcloud secrets add-iam-policy-binding db-password \
  --member="serviceAccount:your-service@project.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

#### 3. RPC Connection Issues

**Symptoms**: Blockchain connection failures
**Solution**:
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

#### 4. GCP Project Issues

**Symptoms**: GCP project not found, permission denied
**Solution**:
```bash
# Check GCP project
gcloud config get-value project
gcloud projects describe fusion-prime-dev

# Set correct project
gcloud config set project fusion-prime-dev

# Check authentication
gcloud auth list
gcloud auth application-default login
```

### Configuration Debugging

#### Check Environment Variables
```bash
# Print all environment variables
env | grep -E "(GCP_|ETH_|CHAIN_|DB_)"

# Check specific variables
echo "GCP_PROJECT_ID: $GCP_PROJECT_ID"
echo "ETHEREUM_RPC_URL: $ETHEREUM_RPC_URL"
echo "CHAIN_ID: $CHAIN_ID"
```

#### Check Secret Access
```bash
# List secrets
gcloud secrets list

# Check secret access
gcloud secrets versions access latest --secret="db-password"
gcloud secrets versions access latest --secret="infura-key"
```

#### Check GCP Resources
```bash
# Check GCP project
gcloud projects describe $GCP_PROJECT_ID

# Check Cloud Run services
gcloud run services list --region=$GCP_REGION

# Check Cloud SQL instances
gcloud sql instances list
```

---

## 📚 Related Documentation

- **[ENVIRONMENTS.md](../ENVIRONMENTS.md)** - Environment setup guide
- **[DEPLOYMENT.md](../DEPLOYMENT.md)** - Deployment procedures
- **[TESTING.md](../TESTING.md)** - Testing configuration
- **[QUICKSTART.md](../QUICKSTART.md)** - Quick start guide

---

## 🆘 Support

### Getting Help

1. **Check configuration**: Verify all required variables are set
2. **Check secrets**: Ensure secrets are accessible
3. **Check connectivity**: Test database and RPC connections
4. **Review documentation**: See related docs above

### Emergency Procedures

1. **Configuration issues**: Check environment variables and secrets
2. **Secret access**: Verify IAM permissions
3. **RPC issues**: Check RPC provider status and switch if needed
4. **GCP issues**: Check project permissions and billing

---

**Last Updated**: 2025-01-25
**Next Review**: After configuration changes
