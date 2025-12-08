# GitHub Actions Workflows

Unified, modular deployment system for Fusion Prime.

## 🎯 Overview

The workflow system is designed with **unification and modularity** in mind:

- **Unified**: Single source of truth for deployment logic
- **Modular**: Deploy services individually or in any combination
- **Simple**: Easy to use for common scenarios
- **Flexible**: Advanced options for complex deployments

## 📁 Workflow Files

### Core Workflows

| Workflow | Purpose | Trigger |
|----------|---------|---------|
| **deploy.yml** | Main deployment orchestrator | Push, Tags, Manual |
| **ci.yml** | Continuous integration tests | Push, PR |
| **_reusable-deploy-service.yml** | Reusable service deployment | Called by other workflows |

### Service-Specific Workflows

| Workflow | Service | Use Case |
|----------|---------|----------|
| **deploy-settlement.yml** | Settlement Service | Hotfixes, targeted updates |
| **deploy-risk-engine.yml** | Risk Engine | Independent deployment |
| **deploy-compliance.yml** | Compliance Service | Independent deployment |
| **deploy-relayer.yml** | Event Relayer | Relayer updates |
| **deploy-contracts.yml** | Smart Contracts | Contract deployments |

## 🚀 Usage

### 1. Auto-Deployment (Simple)

**Dev Environment** - Automatic on every push:
```bash
git push origin dev
# ✅ Automatically deploys ALL services to dev
```

**Staging Environment** - Automatic on branch push:
```bash
git push origin staging
# ✅ Automatically deploys ALL services to staging
```

**Production** - Automatic on git tag:
```bash
git tag v1.0.0
git push --tags
# ✅ Automatically deploys ALL services to production
```

### 2. Manual Deployment (Flexible)

Go to **Actions** → **Deploy** → **Run workflow**

**Deploy All Services:**
```
Environment: dev
Services: all
Tag: (leave empty for auto)
```

**Deploy Single Service:**
```
Environment: staging
Services: settlement
Tag: hotfix-123
```

**Deploy Multiple Services:**
```
Environment: production
Services: settlement,risk-engine
Tag: v1.2.3
Skip Build: ✓ (use existing images)
```

**Deploy Backend Only:**
```
Environment: dev
Services: backend
# This deploys: settlement, risk-engine, compliance
```

### 3. Service-Specific Deployment (Modular)

Deploy individual services using dedicated workflows:

**Deploy Settlement Service:**
```
Actions → Deploy Settlement Service → Run workflow
Environment: dev
Tag: (optional)
Skip Build: ☐
```

**Deploy Smart Contracts:**
```
Actions → Deploy Smart Contracts → Run workflow
Environment: staging
Tag: contracts-v2
```

## 🏗️ Architecture

### Workflow Hierarchy

```
deploy.yml (Main Orchestrator)
├─ setup (Determine config)
├─ deploy-services (Matrix deployment)
│  └─ Uses: _reusable-deploy-service.yml (Per service)
│     ├─ Deploy settlement
│     ├─ Deploy risk-engine
│     ├─ Deploy compliance
│     ├─ Deploy relayer
│     └─ Deploy contracts
├─ validate (Health checks)
└─ summary (Results)

Individual Service Workflows
├─ deploy-settlement.yml
├─ deploy-risk-engine.yml
├─ deploy-compliance.yml
├─ deploy-relayer.yml
└─ deploy-contracts.yml
   └─ All use: _reusable-deploy-service.yml
```

### Reusable Workflow Benefits

✅ **DRY Principle** - Single deployment logic, used everywhere
✅ **Consistency** - Same process for all services
✅ **Maintainability** - Update once, applies everywhere
✅ **Testability** - Isolated, testable deployment steps

## 🎨 Deployment Patterns

### Pattern 1: Full Stack Deployment

Deploy everything at once (contracts + all services):

```yaml
# Via main deploy.yml
Services: all
# OR via git push/tag (automatic)
```

**Use Case:** Major releases, environment setup

### Pattern 2: Backend Services Only

Deploy backend services without contracts:

```yaml
Services: backend
# Deploys: settlement, risk-engine, compliance
```

**Use Case:** Service updates, no contract changes

### Pattern 3: Single Service Hotfix

Deploy one service quickly:

```yaml
# Option A: Via main workflow
Services: settlement
Skip Build: true

# Option B: Via service-specific workflow
Actions → Deploy Settlement Service
```

**Use Case:** Hotfixes, bug fixes, targeted updates

### Pattern 4: Partial Deployment

Deploy specific combination:

```yaml
Services: settlement,relayer
```

**Use Case:** Related services that need coordinated updates

### Pattern 5: Contracts Only

Deploy smart contracts independently:

```yaml
# Via deploy-contracts.yml
Actions → Deploy Smart Contracts
Environment: staging
```

**Use Case:** Contract upgrades, migrations

## 📋 Service Matrix

The system supports these services (can be deployed in any combination):

| Service | Key | Description |
|---------|-----|-------------|
| Settlement Service | `settlement` | Core settlement logic |
| Risk Engine | `risk-engine` | Risk calculations |
| Compliance Service | `compliance` | KYC/AML workflows |
| Event Relayer | `relayer` | Blockchain event processor |
| Smart Contracts | `contracts` | Solidity contracts |

**Shortcuts:**
- `all` = All services above
- `backend` = settlement + risk-engine + compliance

## ⚙️ Configuration

### Environment Variables (Repository Vars)

Set in **Settings** → **Secrets and variables** → **Actions** → **Variables**:

```
GCP_PROJECT_ID=fusion-prime
GCP_REGION=us-central1
ETHEREUM_RPC_URL=https://sepolia.infura.io/v3/...
CHAIN_ID=11155111
```

### Secrets (Repository Secrets)

Set in **Settings** → **Secrets and variables** → **Actions** → **Secrets**:

```
GCP_SA_KEY=<GCP service account JSON>
PRIVATE_KEY=<Ethereum private key>
ETHERSCAN_API_KEY=<Etherscan API key>
```

### Environment Protection

Set in **Settings** → **Environments**:

- **dev** - No protection, auto-deploy
- **staging** - Optional: require approval
- **production** - Require approval + restricted branches

## 🔍 Monitoring

### GitHub Actions UI

1. Go to **Actions** tab
2. Select workflow run
3. View:
   - Deployment configuration
   - Service URLs
   - Health check results
   - Deployment summary

### Job Outputs

Each deployment provides:
- ✅ Service URL
- ✅ Health status
- ✅ Deployment logs
- ✅ Summary table

### Validation

Automatic health checks after deployment:

```
| Service      | Status      | URL                    |
|--------------|-------------|------------------------|
| settlement   | ✅ Healthy  | https://...            |
| risk-engine  | ✅ Healthy  | https://...            |
| compliance   | ✅ Healthy  | https://...            |
| relayer      | ✅ Healthy  | https://...            |
```

## 🚨 Troubleshooting

### Deployment Failed

**Check:**
1. Workflow logs in Actions tab
2. Build step output
3. GCP credentials validity
4. Service configuration

**Common Issues:**
- **Build timeout** → Increase timeout or use `skip_build`
- **Health check failed** → Check service logs in GCP Cloud Run
- **Permission denied** → Verify GCP_SA_KEY has correct permissions

### Skip Build for Faster Deployment

If images already exist:

```yaml
Skip Build: true
```

This deploys existing images without rebuilding (much faster).

### Rollback

**Option 1: Redeploy previous tag**
```
Services: settlement
Tag: v1.0.0  # Previous working version
Skip Build: true
```

**Option 2: Via GCP Console**
```bash
gcloud run services update-traffic settlement-service \
  --to-revisions=settlement-service-00001-abc=100
```

## 📚 Examples

### Example 1: Hotfix Settlement Service

Scenario: Bug in settlement service, need quick fix

```
1. Fix code, commit to branch
2. Actions → Deploy Settlement Service → Run workflow
   Environment: dev
   Tag: hotfix-payment-bug
   Skip Build: ☐
3. Test in dev
4. Repeat for staging/production if successful
```

### Example 2: Multi-Service Update

Scenario: Update settlement and risk engine together

```
1. Commit changes
2. Actions → Deploy → Run workflow
   Environment: staging
   Services: settlement,risk-engine
   Tag: feature-new-calculations
3. Automatic parallel deployment
4. Health checks validate both services
```

### Example 3: Contract Deployment Only

Scenario: Deploy new contract version without touching services

```
1. Update contracts
2. Actions → Deploy Smart Contracts → Run workflow
   Environment: staging
   Tag: contracts-v2.0.0
3. Contracts deployed to blockchain
4. Services remain unchanged
```

### Example 4: Full Production Release

Scenario: Major release with everything

```
1. Merge to main branch
2. Create git tag:
   git tag v2.0.0
   git push --tags
3. Automatic deployment triggered:
   - Environment: production
   - Services: all
   - Tag: v2.0.0
4. All services + contracts deployed
5. Comprehensive validation
```

## 🎯 Best Practices

### 1. Use Auto-Deployment for Normal Flow

Let the system auto-deploy on branch push:
- ✅ Consistent process
- ✅ No manual steps
- ✅ Git-based versioning

### 2. Use Service-Specific Workflows for Hotfixes

Quick fixes to individual services:
- ✅ Faster deployment
- ✅ Reduced risk
- ✅ Clear intent

### 3. Test in Dev First

Always validate in dev before staging/production:
- ✅ Catch issues early
- ✅ Verify configuration
- ✅ Test integrations

### 4. Use Skip Build When Appropriate

If images already exist and working:
- ✅ Faster deployment
- ✅ Saves build minutes
- ✅ Useful for rollbacks

### 5. Tag Production Releases

Use semantic versioning for production:
- ✅ Clear version history
- ✅ Easy rollback reference
- ✅ Audit trail

## 🔗 Related Documentation

- **[DEPLOYMENT.md](../../DEPLOYMENT.md)** - Complete deployment guide
- **[TESTING.md](../../TESTING.md)** - Testing strategy
- **[scripts/deploy-unified.sh](../../scripts/deploy-unified.sh)** - Deployment script

## 📊 Workflow Metrics

**Typical Deployment Times:**
- Single service: ~3-5 minutes
- All services: ~8-12 minutes (parallel)
- Contracts only: ~2-3 minutes
- With skip_build: ~1-2 minutes

**Resource Usage:**
- Build: ~2-3 GitHub Actions minutes per service
- Deploy: ~1 minute per service
- Validate: ~1 minute total

---

**Last Updated**: 2025-01-25
**Maintained by**: DevOps Team
**Questions?** Open an issue or check the documentation
