# Git Commit Plan - Safe Deployment

## 🚨 **Files to EXCLUDE from commit (Sensitive/Generated)**

### **Environment Files with Secrets**
- `.env.dev` ❌ (contains private keys and API keys)
- `.env.testnet` ❌ (contains sensitive data)
- `.env.local` ❌ (modified, contains local secrets)
- `.env.test.backup` ❌ (backup of sensitive file)

### **Generated/Compiled Files**
- `contracts/out/` ❌ (compiled contracts)
- `contracts/cache/` ❌ (Foundry cache)
- `contracts/broadcast/` ❌ (deployment artifacts with addresses)
- `contracts/deployments/*.json` ❌ (deployment artifacts)
- `*.pyc` ❌ (Python bytecode)
- `**/__pycache__/` ❌ (Python cache)

### **Test Files (Temporary)**
- `test-deploy.sh` ❌
- `test-deploy-minimal.sh` ❌
- `test-env-filter.sh` ❌
- `test-final-fix.sh` ❌
- `debug-deploy.sh` ❌
- `simple-deploy.sh` ❌
- `load_env.sh` ❌

### **Factory Address File**
- `.factory_address` ❌ (contains deployed contract address)

## ✅ **Files to INCLUDE in commit (Safe/Necessary)**

### **Core Scripts & Configuration**
- `scripts/deploy-unified.sh` ✅ (main deployment script)
- `scripts/gcp-contract-registry.sh` ✅ (contract registry management)
- `scripts/update-services-contracts.sh` ✅ (service update script)
- `scripts/test-contract-registry.sh` ✅ (validation script)
- `scripts/lib/` ✅ (shared library functions)
- `scripts/setup/` ✅ (setup scripts)
- `scripts/test/` ✅ (test scripts)
- `scripts/README.md` ✅ (updated documentation)
- `scripts/DEPRECATED_SCRIPTS.md` ✅ (deprecation documentation)

### **Documentation**
- `DEPLOYMENT.md` ✅ (updated with contract registry)
- `ENVIRONMENTS.md` ✅ (environment configuration)
- `README.md` ✅ (updated documentation)
- `TESTING.md` ✅ (updated testing guide)
- `docs/` ✅ (all new documentation)

### **Service Code**
- `services/shared/` ✅ (contract registry library)
- `services/relayer/` ✅ (updated relayer service)
- `services/settlement/` ✅ (updated settlement service)
- `services/risk-engine/` ✅ (updated risk engine)
- `services/compliance/` ✅ (updated compliance service)

### **Configuration Files**
- `docker-compose.yml` ✅ (updated with contract registry)
- `cloudbuild.yaml` ✅ (updated build configuration)
- `env.*.example` ✅ (example environment files)
- `scripts/config/environments.yaml` ✅ (environment configuration)

### **Test Infrastructure**
- `tests/` ✅ (updated test structure)
- `examples/` ✅ (integration examples)

### **GitHub Workflows**
- `.github/workflows/` ✅ (CI/CD workflows)

## 🗑️ **Files to DELETE (Deprecated)**

### **Deprecated Scripts**
- `scripts/update-cloud-deployment.sh` ❌ (deleted)
- `scripts/update-contract-address.sh` ❌ (deleted)
- `scripts/update-contract-addresses.sh` ❌ (deleted)
- `scripts/update-env-test.sh` ❌ (deleted)
- `scripts/upload-contracts.sh` ❌ (deleted)

### **Deprecated Test Files**
- `tests/local/` ❌ (old test structure)
- `tests/remote/` ❌ (old test structure)

### **Deprecated Documentation**
- `CI_CD_STATUS.md` ❌ (deleted)
- `DEV_STAGING_PRODUCTION_STRATEGY.md` ❌ (deleted)
- `ENVIRONMENT_DEPLOYMENT.md` ❌ (deleted)
- `INFRASTRUCTURE_DEPLOYMENT.md` ❌ (deleted)

## 📋 **Commit Strategy**

### **Step 1: Clean up sensitive files**
```bash
# Remove sensitive files from git tracking
git rm --cached .env.dev .env.testnet .env.local .env.test.backup
git rm --cached .factory_address

# Remove test files
rm test-*.sh debug-deploy.sh simple-deploy.sh load_env.sh
```

### **Step 2: Add safe files**
```bash
# Add core scripts and configuration
git add scripts/deploy-unified.sh scripts/gcp-contract-registry.sh scripts/update-services-contracts.sh
git add scripts/test-contract-registry.sh scripts/lib/ scripts/setup/ scripts/test/
git add scripts/README.md scripts/DEPRECATED_SCRIPTS.md

# Add documentation
git add DEPLOYMENT.md ENVIRONMENTS.md README.md TESTING.md
git add docs/ CONTRACT_REGISTRY_VALIDATION_SUMMARY.md DUPLICATE_ENV_VARS_FIX.md
git add SCRIPT_CLEANUP_SUMMARY.md VALIDATION_REPORT.md

# Add service code
git add services/shared/ services/relayer/ services/settlement/ services/risk-engine/ services/compliance/

# Add configuration
git add docker-compose.yml cloudbuild.yaml env.*.example scripts/config/
git add .github/workflows/ tests/ examples/
```

### **Step 3: Commit with clear message**
```bash
git commit -m "feat: implement contract registry system and fix duplicate env vars

- Add GCP contract registry for centralized contract resource management
- Fix duplicate environment variables in Cloud Run deployment
- Update services to use contract registry with fallback mechanisms
- Remove deprecated scripts and clean up codebase
- Add comprehensive documentation and validation tools
- Update deployment scripts with automatic contract upload
- Implement environment-agnostic contract loading"
```

## ⚠️ **Security Checklist**

- [ ] No private keys in committed files
- [ ] No API keys in committed files
- [ ] No contract addresses in committed files
- [ ] No database credentials in committed files
- [ ] All sensitive data in .gitignore
- [ ] Example files use placeholder values
- [ ] Documentation references environment variables, not hardcoded values

## 🎯 **Result**

After this commit, the repository will have:
- ✅ Clean, maintainable codebase
- ✅ Comprehensive contract registry system
- ✅ Fixed duplicate environment variable issue
- ✅ Updated documentation
- ✅ No sensitive data exposed
- ✅ Deprecated code removed
