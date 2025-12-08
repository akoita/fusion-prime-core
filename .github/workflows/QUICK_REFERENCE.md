# GitHub Actions - Quick Reference

## 🚀 Quick Deploy Commands

### Via GitHub UI

1. **Go to Actions tab** → Select workflow → **Run workflow**
2. **Choose options** → Click **Run workflow**

### Deploy All Services
```
Workflow: Deploy
Environment: dev
Services: all
```

### Deploy Single Service
```
Workflow: Deploy Settlement Service
Environment: staging
Tag: hotfix-123
```

### Deploy Specific Services
```
Workflow: Deploy
Environment: production
Services: settlement,risk-engine
Skip Build: ✓ (for faster deployment)
```

## 📋 Available Services

| Service ID | Description |
|------------|-------------|
| `settlement` | Settlement Service |
| `risk-engine` | Risk Engine Service |
| `compliance` | Compliance Service |
| `relayer` | Event Relayer |
| `contracts` | Smart Contracts |
| `backend` | All backend services (shortcut) |
| `all` | Everything |

## 🎯 Common Scenarios

### Scenario: Hotfix in Production

```bash
# Option 1: Via service-specific workflow
Actions → Deploy Settlement Service
Environment: production
Tag: hotfix-critical-bug
Skip Build: ☐

# Option 2: Via main workflow
Actions → Deploy
Environment: production
Services: settlement
Tag: hotfix-critical-bug
```

### Scenario: Deploy to Dev for Testing

```bash
# Just push to dev branch
git checkout dev
git push origin dev
# ✅ Auto-deploys everything
```

### Scenario: Rollback to Previous Version

```bash
Actions → Deploy
Environment: production
Services: settlement
Tag: v1.0.0  # Previous working version
Skip Build: ✓  # Use existing image
```

### Scenario: Deploy Contracts Only

```bash
Actions → Deploy Smart Contracts
Environment: staging
Tag: contracts-v2.0.0
```

### Scenario: Backend Services Update

```bash
Actions → Deploy
Environment: staging
Services: backend  # settlement + risk-engine + compliance
Tag: backend-update-v1.1
```

## ⚡ Speed Tips

### Fastest Deployment (1-2 minutes)
```
Services: settlement
Skip Build: ✓
```

### Parallel Deployment (8-12 minutes)
```
Services: all
# All services build/deploy in parallel
```

### Sequential Specific Services (5-8 minutes)
```
Services: settlement,risk-engine
```

## 🔍 Monitoring

### Check Deployment Status

1. **Actions tab** → Click on running workflow
2. View real-time logs
3. Check deployment summary

### Health Check Results

Automatic after deployment:
- ✅ Green = Healthy
- ❌ Red = Failed
- ⚠️ Yellow = Warning

### Service URLs

Available in deployment summary:
```
settlement: https://settlement-service-XXX.run.app
risk-engine: https://risk-engine-XXX.run.app
compliance: https://compliance-XXX.run.app
```

## 🚨 Emergency Procedures

### Service Down After Deployment

**Quick rollback:**
```bash
# Via GitHub Actions
Actions → Deploy → Run workflow
Services: [failing-service]
Tag: [previous-working-version]
Skip Build: ✓
```

**Via GCP (faster):**
```bash
gcloud run services update-traffic settlement-service \
  --to-revisions=[previous-revision]=100 \
  --region=us-central1
```

### Deployment Stuck

**Cancel workflow:**
1. Actions tab → Running workflow
2. Click **Cancel workflow**

**Retry:**
1. Actions → Re-run failed jobs
2. Or run new workflow

### Build Timeout

**Solution:**
```
Skip Build: ✓  # Use existing image
```

Or increase timeout in workflow file.

## 📞 Getting Help

1. **Check workflow logs** in Actions tab
2. **Review documentation** in `.github/workflows/README.md`
3. **Check GCP logs** via Cloud Console
4. **Open issue** in repository

## 🎓 Learning Resources

| Resource | Link |
|----------|------|
| Full Documentation | [.github/workflows/README.md](README.md) |
| Deployment Guide | [DEPLOYMENT.md](../../DEPLOYMENT.md) |
| Testing Guide | [TESTING.md](../../TESTING.md) |
| Deployment Script | [scripts/deploy-unified.sh](../../scripts/deploy-unified.sh) |

---

**Pro Tip:** Use service-specific workflows for quick deployments, main workflow for coordinated releases.
