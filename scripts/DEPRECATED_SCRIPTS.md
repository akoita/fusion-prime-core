# Deprecated Scripts

This document lists scripts that have been deprecated and should be removed.

## ❌ Deprecated Scripts

### 1. `update-cloud-deployment.sh`
- **Status**: DEPRECATED
- **Reason**: Superseded by `update-services-contracts.sh`
- **Issues**:
  - Hardcoded project ID and region
  - Limited functionality
  - Doesn't use contract registry
- **Replacement**: `./scripts/update-services-contracts.sh --project <PROJECT>`

### 2. `update-contract-address.sh`
- **Status**: DEPRECATED
- **Reason**: Manual approach, superseded by automated contract registry
- **Issues**:
  - Requires manual contract address input
  - Doesn't integrate with GCS registry
  - Duplicates functionality
- **Replacement**:
  - `./scripts/deploy-unified.sh --contracts` (auto-uploads)
  - `./scripts/upload-contracts.sh` (manual upload)

### 3. `update-contract-addresses.sh`
- **Status**: DEPRECATED
- **Reason**: Redundant with unified deployment and contract registry
- **Issues**:
  - Duplicates functionality in `deploy-unified.sh`
  - Doesn't use GCS registry
  - Manual approach
- **Replacement**:
  - `./scripts/deploy-unified.sh --contracts` (auto-uploads)
  - `./scripts/upload-contracts.sh` (manual upload)

### 4. `update-env-test.sh`
- **Status**: DEPRECATED
- **Reason**: One-time setup script, no longer needed
- **Issues**:
  - Hardcoded values
  - Not part of current workflow
  - Environment files are now managed differently
- **Replacement**: Use `env.dev.example` as template

### 5. `upload-contracts.sh`
- **Status**: DEPRECATED
- **Reason**: Redundant wrapper around `gcp-contract-registry.sh`
- **Issues**:
  - Just calls `gcp-contract-registry.sh upload`
  - No added functionality
  - Maintenance overhead
- **Replacement**: Use `./scripts/gcp-contract-registry.sh upload` directly

## ✅ Active Scripts

### Contract Registry System
- `gcp-contract-registry.sh` - Contract resource management (upload, download, list, get-addresses, get-metadata)
- `update-services-contracts.sh` - Update Cloud Run services with contract addresses

### Deployment System
- `deploy-unified.sh` - Main deployment script (includes contract deployment)

## 🗑️ Cleanup Actions

1. **Remove deprecated scripts**:
   ```bash
   rm scripts/update-cloud-deployment.sh
   rm scripts/update-contract-address.sh
   rm scripts/update-contract-addresses.sh
   rm scripts/update-env-test.sh
   ```

2. **Update documentation** to remove references to deprecated scripts

3. **Update any CI/CD workflows** that might reference deprecated scripts

## 📋 Migration Guide

### Old → New Commands

| Old Command | New Command |
|-------------|-------------|
| `./scripts/update-cloud-deployment.sh 0x123...` | `./scripts/update-services-contracts.sh --project fusion-prime` |
| `./scripts/update-contract-address.sh 0x123...` | `./scripts/deploy-unified.sh --contracts` |
| `./scripts/update-contract-addresses.sh --env dev` | `./scripts/deploy-unified.sh --env dev --contracts` |
| `./scripts/update-env-test.sh` | Copy from `env.dev.example` |
| `./scripts/upload-contracts.sh --env dev --project fusion-prime` | `./scripts/gcp-contract-registry.sh upload --env dev --project fusion-prime` |

## 🎯 Benefits of New System

1. **Automated**: Contract addresses automatically extracted and uploaded
2. **Centralized**: All contract resources managed in GCS registry
3. **Consistent**: Same process for all environments
4. **Reliable**: Built-in error handling and validation
5. **Maintainable**: Single source of truth for contract management
