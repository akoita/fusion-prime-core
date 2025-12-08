# Deployment Workflows Architecture

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     DEPLOYMENT ENTRY POINTS                      │
└─────────────────────────────────────────────────────────────────┘

1. AUTO-DEPLOY (Push/Tag)              2. MANUAL DEPLOY
   ├─ Push to dev branch                  ├─ Main workflow (deploy.yml)
   ├─ Push to staging branch              ├─ Service-specific workflows
   └─ Create version tag (v*)             │  ├─ deploy-settlement.yml
                                          │  ├─ deploy-risk-engine.yml
                                          │  ├─ deploy-compliance.yml
                                          │  ├─ deploy-relayer.yml
                                          │  └─ deploy-contracts.yml
                                          └─ Flexible service selection
           │                                        │
           └────────────────┬───────────────────────┘
                            ▼
        ┌───────────────────────────────────────────┐
        │        DEPLOY.YML (Orchestrator)          │
        │                                           │
        │  ┌─────────────────────────────────────┐ │
        │  │  1. Setup & Configuration           │ │
        │  │     - Detect environment            │ │
        │  │     - Parse service selection       │ │
        │  │     - Generate deployment matrix    │ │
        │  └─────────────────────────────────────┘ │
        │                    │                      │
        │                    ▼                      │
        │  ┌─────────────────────────────────────┐ │
        │  │  2. Deploy Services (Parallel)      │ │
        │  │     - Matrix strategy (max 4)       │ │
        │  │     - Calls reusable workflow       │ │
        │  └─────────────────────────────────────┘ │
        │                    │                      │
        │                    ▼                      │
        │  ┌─────────────────────────────────────┐ │
        │  │  3. Validate Deployment             │ │
        │  │     - Health checks                 │ │
        │  │     - Service URLs                  │ │
        │  └─────────────────────────────────────┘ │
        │                    │                      │
        │                    ▼                      │
        │  ┌─────────────────────────────────────┐ │
        │  │  4. Summary                         │ │
        │  │     - Results table                 │ │
        │  │     - Status report                 │ │
        │  └─────────────────────────────────────┘ │
        └───────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────────┐
        │  _REUSABLE-DEPLOY-SERVICE.YML (Worker)    │
        │                                           │
        │  Input: service, environment, tag         │
        │                                           │
        │  ┌─────────────────────────────────────┐ │
        │  │  Per-Service Deployment              │ │
        │  │  ├─ Checkout code                    │ │
        │  │  ├─ Setup tools (Python/Foundry)     │ │
        │  │  ├─ Authenticate to GCP              │ │
        │  │  ├─ Deploy service                   │ │
        │  │  │  └─ Calls deploy-unified.sh       │ │
        │  │  ├─ Get service URL                  │ │
        │  │  └─ Health check                     │ │
        │  └─────────────────────────────────────┘ │
        │                                           │
        │  Output: service_url, deployment_status   │
        └───────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────────┐
        │    DEPLOY-UNIFIED.SH (Script)             │
        │                                           │
        │  ├─ Load environment config               │
        │  ├─ Build service (Cloud Build)           │
        │  ├─ Deploy to Cloud Run                   │
        │  └─ Run health checks                     │
        └───────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────────┐
        │         GOOGLE CLOUD PLATFORM             │
        │                                           │
        │  ├─ Cloud Run (Services)                  │
        │  ├─ Cloud Build (Image building)          │
        │  ├─ Artifact Registry (Images)            │
        │  └─ Cloud SQL, Pub/Sub, etc.              │
        └───────────────────────────────────────────┘
```

## 🎯 Design Principles

### 1. **Unification**
- Single source of truth: `_reusable-deploy-service.yml`
- All workflows use the same deployment logic
- Consistent behavior across all services

### 2. **Modularity**
- Deploy any service independently
- Combine services in any configuration
- Parallel deployment support

### 3. **Simplicity**
- Auto-deploy on branch push (zero configuration)
- Manual deploy with dropdown menus
- Sensible defaults

### 4. **Flexibility**
- Service-specific workflows for targeted deployments
- Main workflow for orchestrated deployments
- Support for partial deployments

## 📊 Deployment Matrix

```
Service Selection → Deployment Strategy

"all"                    → Parallel: contracts + settlement + risk-engine + compliance + relayer
"backend"                → Parallel: settlement + risk-engine + compliance
"settlement"             → Single: settlement
"settlement,risk-engine" → Parallel: settlement + risk-engine
"contracts"              → Single: contracts
```

## 🔄 Workflow Execution Flow

### Example: Deploy "settlement,risk-engine" to staging

```
1. Trigger (Manual dispatch)
   └─ User selects: environment=staging, services=settlement,risk-engine

2. Setup Job
   ├─ Parse input → ["settlement", "risk-engine"]
   ├─ Generate tag → staging-20250125-abc123
   └─ Create matrix → ["settlement", "risk-engine"]

3. Deploy-Services Job (Parallel)
   ├─ Deploy Settlement
   │  ├─ Call _reusable-deploy-service.yml
   │  ├─ Build image → settlement-service:staging-20250125-abc123
   │  ├─ Deploy to Cloud Run
   │  ├─ Get URL → https://settlement-service-XXX.run.app
   │  └─ Health check → ✅ Passed
   │
   └─ Deploy Risk Engine
      ├─ Call _reusable-deploy-service.yml
      ├─ Build image → risk-engine:staging-20250125-abc123
      ├─ Deploy to Cloud Run
      ├─ Get URL → https://risk-engine-XXX.run.app
      └─ Health check → ✅ Passed

4. Validate Job
   ├─ Check settlement → ✅ Healthy
   ├─ Check risk-engine → ✅ Healthy
   └─ Generate health table

5. Summary Job
   └─ Display results → ✅ Deployment Successful
```

## 🛠️ Maintenance

### Adding a New Service

1. **Update deploy-unified.sh**
   ```bash
   # Add service mapping
   case "$service" in
     "new-service")
       service_dir="services/new-service"
       image_name="new-service"
       ;;
   esac
   ```

2. **Create service workflow** (optional)
   ```yaml
   # .github/workflows/deploy-new-service.yml
   name: Deploy New Service
   uses: ./.github/workflows/_reusable-deploy-service.yml
   ```

3. **Update documentation**
   - Add to service list in README.md
   - Update QUICK_REFERENCE.md

### Modifying Deployment Logic

**✅ Single place to update:**
- Edit `_reusable-deploy-service.yml`
- Changes apply to all workflows automatically

**❌ Don't modify:**
- Individual service workflows (they just call the reusable workflow)
- Main deploy.yml logic (unless changing orchestration)

## 📈 Benefits

### Before (Monolithic)
```yaml
❌ Single large workflow
❌ Can't deploy services separately
❌ Hard to maintain
❌ Slow (sequential deployment)
❌ Duplicate code
```

### After (Modular)
```yaml
✅ Reusable components
✅ Deploy any service independently
✅ Easy to maintain (single source of truth)
✅ Fast (parallel deployment)
✅ DRY principle
✅ Flexible combinations
```

## 🎓 Key Concepts

### Reusable Workflows
- Defined with `workflow_call` trigger
- Can be called from other workflows
- Supports inputs, secrets, and outputs
- Enables DRY deployment logic

### Matrix Strategy
- Deploy multiple services in parallel
- Dynamically generated from service selection
- Configurable parallelism (max 4 concurrent)
- Fail-fast disabled (continue on individual failures)

### Service Abstraction
- Each service is a string identifier
- Mapping to actual resources in deploy-unified.sh
- Allows flexible combinations
- Easy to add/remove services

## 🚀 Usage Patterns

### Pattern: Gradual Rollout
```
1. Deploy to dev → Test
2. Deploy to staging → Validate
3. Deploy to production → Release
```

### Pattern: Canary Deployment
```
1. Deploy single service to production
2. Monitor metrics
3. Deploy remaining services
```

### Pattern: Hotfix
```
1. Use service-specific workflow
2. Deploy only affected service
3. Skip build if image exists
```

## 📚 References

- **[Workflow README](.github/workflows/README.md)** - Complete documentation
- **[Quick Reference](.github/workflows/QUICK_REFERENCE.md)** - Quick commands
- **[Deployment Guide](DEPLOYMENT.md)** - Manual deployment
- **[Testing Guide](TESTING.md)** - Test strategy

---

**Architecture Version**: 2.0
**Last Updated**: 2025-01-25
**Status**: Production Ready ✅
