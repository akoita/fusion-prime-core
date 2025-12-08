# Fusion Prime Scripts

This directory contains organized scripts for setting up, testing, and managing the Fusion Prime project.

## 📁 Directory Structure

```
scripts/
├── test.sh                    # Main test runner (entry point)
├── setup/                     # Setup and bootstrap scripts
│   ├── setup.sh              # Main setup dispatcher
│   ├── bootstrap.sh           # Project bootstrap
│   ├── setup-env.sh           # Environment configuration
│   ├── setup-relayer.sh       # Relayer setup
│   └── init-pubsub.sh         # Pub/Sub initialization
├── test/                      # Test execution scripts
│   ├── local.sh               # Local testing
│   ├── remote.sh              # Remote testing
│   └── common.sh              # Shared test utilities
├── utility/                   # Utility scripts
│   ├── utility.sh             # Main utility dispatcher
│   ├── build.sh               # Build scripts
│   ├── cleanup.sh             # Cleanup scripts
│   ├── verify.sh              # Verification scripts
│   └── reports.sh             # Report viewing
└── specialized/               # Specialized testing scripts
    ├── test-contracts-manual.sh  # Manual Sepolia testing with real transactions
    └── test-local-relayer.sh     # Specific relayer testing and debugging
```

## 🚀 Quick Start

### Main Entry Points

```bash
# Testing
./scripts/test.sh local          # Run local tests
./scripts/test.sh testnet        # Run testnet tests
./scripts/test.sh production     # Run production health checks

# Setup
./scripts/setup/setup.sh all     # Complete setup
./scripts/setup/setup.sh env     # Configure environments

# Deployment
./scripts/deploy-unified.sh --env dev --services all --contracts     # Deploy to dev with contracts
./scripts/deploy-unified.sh --env staging --services all --tag v1.0.0  # Deploy to staging

# Contract Management
./scripts/gcp-contract-registry.sh upload --env dev --project fusion-prime-dev  # Upload contracts
./scripts/update-services-contracts.sh --project fusion-prime-dev  # Update services with contract addresses

# Utilities
./scripts/utility/utility.sh build    # Build project
./scripts/utility/utility.sh cleanup  # Clean up resources
./scripts/utility/utility.sh reports  # View test reports
```

### Environment Configuration

> 📋 **Configuration Management**: See [docs/CONFIGURATION_MANAGEMENT.md](../docs/CONFIGURATION_MANAGEMENT.md) for complete configuration details.

The scripts use a **hierarchical configuration system**:

1. **`scripts/config/environments.yaml`** - Hardcoded defaults
2. **Environment Variables** - Override defaults
3. **Secret Manager** - Sensitive values
4. **GitHub Secrets** - CI/CD credentials

**Required Environment Variables:**
```bash
# Override hardcoded values
export GCP_PROJECT_ID="fusion-prime-dev"
export ETHEREUM_RPC_URL="https://sepolia.infura.io/v3/YOUR_KEY"
export CHAIN_ID="11155111"

# Required secrets (never hardcoded)
export PRIVATE_KEY="0x..."  # For contract deployment
export ETHERSCAN_API_KEY="..."  # For contract verification
```

**Configuration Validation:**
```bash
# Check configuration without deploying
./scripts/deploy-unified.sh --env dev --services all --dry-run
```

## 🧪 Testing

### Local Testing
```bash
# Quick validation (~30 seconds)
./scripts/test.sh quick

# Full local testing (~5 minutes)
./scripts/test.sh local

# Specific test categories
./scripts/test.sh contracts
./scripts/test.sh backend
./scripts/test.sh integration
./scripts/test.sh e2e

# Health and status
./scripts/test.sh health
./scripts/test.sh status
./scripts/test.sh services
```

### Remote Testing
```bash
# Testnet testing (~10 minutes)
./scripts/test.sh testnet

# Production health checks (~5 minutes)
./scripts/test.sh production

# Cross-environment integration (~15 minutes)
./scripts/test.sh integration-remote
```

### Test Options
```bash
# Generate reports
./scripts/test.sh local --reports

# Disable reports
./scripts/test.sh local --no-reports

# Verbose output
./scripts/test.sh local --verbose

# Coverage analysis
./scripts/test.sh contracts --coverage
```

## ⚙️ Setup

### Complete Setup
```bash
# Run complete setup
./scripts/setup/setup.sh all

# Or step by step
./scripts/setup/setup.sh bootstrap
./scripts/setup/setup.sh env
./scripts/setup/setup.sh services
```

### Individual Setup Tasks
```bash
# Bootstrap project
./scripts/setup/setup.sh bootstrap

# Configure environments
./scripts/setup/setup.sh env --force

# Start services
./scripts/setup/setup.sh services

# Initialize Pub/Sub
./scripts/setup/setup.sh pubsub

# Setup relayer
./scripts/setup/setup.sh relayer
```

## 🔧 Contract Registry System

The contract registry system manages smart contract resources (addresses, ABIs, metadata) across all environments.

### Contract Management
```bash
# Upload contract artifacts to GCS
./scripts/gcp-contract-registry.sh upload --env dev --project fusion-prime-dev

# Download contract artifacts from GCS
./scripts/gcp-contract-registry.sh download --env dev --project fusion-prime-dev

# List available contracts
./scripts/gcp-contract-registry.sh list --project fusion-prime-dev

# Get contract addresses
./scripts/gcp-contract-registry.sh get-addresses --project fusion-prime-dev

# Get deployment metadata
./scripts/gcp-contract-registry.sh get-metadata --env dev --project fusion-prime-dev

# Update services with contract addresses
./scripts/update-services-contracts.sh --project fusion-prime-dev
```

### Manual Contract Upload
```bash
# Upload after manual deployment
./scripts/gcp-contract-registry.sh upload --env dev --project fusion-prime-dev --chain-id 11155111
```

## 🔧 Utilities

### Build and Deploy
```bash
# Build project
./scripts/utility/utility.sh build

# Verify deployment
./scripts/utility/utility.sh verify
```

### Cleanup and Maintenance
```bash
# Clean up resources
./scripts/utility/utility.sh cleanup --force

# View test reports
./scripts/utility/utility.sh reports
```

## 📋 Migration from Old Structure

The old flat structure has been reorganized for better maintainability:

### Old → New Mapping
```bash
# Old commands (now work via main entry points)
./scripts/test-local.sh          → ./scripts/test.sh local
./scripts/test-remote.sh         → ./scripts/test.sh testnet
./scripts/test-integration.sh    → ./scripts/test.sh integration
./scripts/test-e2e.sh           → ./scripts/test.sh e2e

# Old setup commands
./scripts/setup-env.sh           → ./scripts/setup/setup.sh env
./scripts/setup-local-relayer.sh → ./scripts/setup/setup.sh relayer

# Old utility commands
./scripts/cleanup-local.sh       → ./scripts/utility/utility.sh cleanup
./scripts/verify-deployment.sh   → ./scripts/utility/utility.sh verify
./scripts/view-test-reports.sh   → ./scripts/utility/utility.sh reports
```

## 🔧 Specialized Scripts

Two specialized scripts remain in `scripts/specialized/` for specific use cases:

### `test-contracts-manual.sh`
- **Purpose**: Manual testing on Sepolia with real transactions
- **When to use**: When you need to test contracts with real gas costs and network conditions
- **Usage**: `./scripts/specialized/test-contracts-manual.sh`
- **Note**: This functionality may be integrated into remote testing in the future

### `test-local-relayer.sh`
- **Purpose**: Specific relayer testing and debugging
- **When to use**: When debugging relayer-specific issues or testing relayer functionality in isolation
- **Usage**: `./scripts/specialized/test-local-relayer.sh`
- **Note**: This functionality may be integrated into backend testing in the future

## 🎯 Benefits of New Organization

1. **Clear Separation**: Setup, test, and utility scripts are organized by purpose
2. **Single Entry Points**: Main dispatchers provide consistent interface
3. **Reduced Redundancy**: Consolidated similar functionality
4. **Better Maintainability**: Easier to find and update specific functionality
5. **Consistent Interface**: All scripts follow the same pattern
6. **Legacy Support**: Old scripts preserved for migration period

## 🔍 Finding Scripts

- **Need to test something?** → `scripts/test.sh`
- **Need to set up the project?** → `scripts/setup/setup.sh`
- **Need to build or clean up?** → `scripts/utility/utility.sh`
- **Need specialized testing?** → `scripts/specialized/`

## 📚 Documentation

- **Testing**: See `TESTING.md` for detailed testing documentation
- **Setup**: See `QUICKSTART.md` for setup instructions
- **Remote Testing**: See `REMOTE_TESTING.md` for remote testing details
- **Environments**: See `ENVIRONMENTS.md` for environment configuration
