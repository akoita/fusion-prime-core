# Contract Discovery System

## Overview

The Fusion Prime project implements a professional contract discovery system that automatically retrieves deployed contract addresses and ABIs from deployment artifacts, eliminating the need for hardcoded values.

## Architecture

### Local Development
- **Source**: Foundry broadcast artifacts (`contracts/broadcast/`)
- **ABI Source**: Compiled artifacts (`contracts/out/`)
- **Discovery**: Automatic scanning of deployment runs
- **Fallback**: Configuration files for manual override

### Remote Environments
- **Source**: GCP Cloud Storage bucket (`gs://{project}-contract-registry/contracts/`)
- **Format**: JSON files with contract metadata
- **Access**: Service account authentication
- **Versioning**: Multiple deployment versions supported

## Usage

### Automatic Discovery (Recommended)

```python
from tests.common.contract_discovery import discover_contracts

# Discover all contracts for local environment
contracts = discover_contracts("local")
for name, info in contracts.items():
    print(f"{name}: {info.address}")

# Get specific contract
from tests.common.contract_discovery import get_contract_address
address = get_contract_address("EscrowFactory", "local")
```

### Environment Integration

The system is automatically integrated into the test environment loader:

```python
from tests.common.environment_loader import auto_load_environment

env_loader = auto_load_environment()
# Contract addresses are automatically discovered and set
```

## File Structure

```
contracts/
├── broadcast/                    # Foundry deployment artifacts
│   └── DeployMultichain.s.sol/
│       └── 31337/               # Chain ID
│           └── run-latest.json  # Latest deployment
├── out/                         # Compiled artifacts
│   ├── EscrowFactory.sol/
│   │   └── EscrowFactory.json   # ABI and bytecode
│   └── Escrow.sol/
│       └── Escrow.json
└── deployments/                 # Deployment registry
    ├── 31337-local.json         # Local deployments
    ├── 11155111-dev.json        # Dev deployments
    └── 1-production.json        # Production deployments
```

## Professional Deployment Workflow

### 1. Local Development
```bash
# Deploy contracts
forge script script/DeployMultichain.s.sol --rpc-url http://localhost:8545 --broadcast

# Contracts are automatically discovered by tests
pytest tests/ -v
```

### 2. Remote Deployment
```bash
# Deploy to dev environment
forge script script/DeployMultichain.s.sol --rpc-url $ETH_DEV_RPC_URL --broadcast

# Upload to contract registry
gsutil cp contracts/broadcast/DeployMultichain.s.sol/11155111/run-latest.json \
  gs://fusion-prime-dev-contract-registry/contracts/dev/EscrowFactory.json
```

### 3. Service Integration
```python
# Services automatically discover contract addresses
from tests.common.contract_discovery import get_contract_address

factory_address = get_contract_address("EscrowFactory", "dev")
# Use address for service configuration
```

## Configuration

### Local Environment
- **Automatic**: Scans `contracts/broadcast/` for latest deployment
- **Manual Override**: Set in `tests/config/environments.yaml`

### Remote Environments
- **GCP Bucket**: `gs://{project}-contract-registry/contracts/{env}/`
- **Authentication**: Service account with Storage Object Viewer role
- **Format**: JSON files with contract metadata

## Benefits

### ✅ Professional Development
- **No Hardcoded Values**: Contract addresses discovered automatically
- **Version Control**: Deployment artifacts tracked in Git
- **Environment Parity**: Same discovery logic for all environments
- **Service Integration**: All services use same contract addresses

### ✅ Deployment Reliability
- **Automatic Updates**: Tests always use latest deployed contracts
- **Rollback Support**: Can reference previous deployments
- **Multi-Chain**: Supports different chains per environment
- **Audit Trail**: Complete deployment history

### ✅ Team Collaboration
- **Shared Configuration**: All developers use same contract addresses
- **CI/CD Integration**: Automated contract discovery in pipelines
- **Documentation**: Self-documenting deployment artifacts
- **Debugging**: Easy to trace contract deployment issues

## Implementation Details

### Contract Discovery Flow

1. **Environment Detection**: Determine if local or remote
2. **Artifact Scanning**: Find latest deployment artifacts
3. **ABI Loading**: Load ABIs from compiled artifacts
4. **Address Extraction**: Extract contract addresses from deployment
5. **Environment Variables**: Set for downstream services

### Error Handling

- **Fallback Configuration**: Uses config files if discovery fails
- **Graceful Degradation**: Continues with warnings if contracts not found
- **Debug Information**: Detailed logging of discovery process
- **Manual Override**: Supports manual configuration when needed

## Future Enhancements

### Remote Contract Registry
- **GCP Integration**: Full GCP bucket integration
- **Versioning**: Support for multiple contract versions
- **Metadata**: Rich contract metadata (deployment time, gas used, etc.)
- **Notifications**: Pub/Sub notifications for new deployments

### Advanced Features
- **Contract Verification**: Automatic Etherscan verification
- **ABI Validation**: Validate ABI compatibility across versions
- **Deployment Monitoring**: Track deployment success/failure
- **Multi-Chain Support**: Support for multiple chains per environment

## Migration Guide

### From Hardcoded Values
1. Remove hardcoded contract addresses from config files
2. Update services to use contract discovery
3. Test with automatic discovery
4. Remove manual configuration

### To Remote Registry
1. Set up GCP bucket for contract registry
2. Configure service account permissions
3. Update deployment scripts to upload artifacts
4. Test remote contract discovery

## Troubleshooting

### Common Issues

**Contracts Not Found**
- Check if deployment artifacts exist
- Verify chain ID matches environment
- Ensure ABI files are compiled

**Permission Errors**
- Check GCP service account permissions
- Verify bucket access for remote environments
- Ensure local file permissions

**Version Mismatches**
- Clear deployment artifacts and redeploy
- Check for multiple deployment runs
- Verify latest deployment is being used

### Debug Commands

```bash
# Check deployment artifacts
ls -la contracts/broadcast/*/31337/

# Verify contract discovery
python -c "from tests.common.contract_discovery import discover_contracts; print(discover_contracts('local'))"

# Test environment loader
export TEST_ENVIRONMENT=local
python -c "from tests.common.environment_loader import auto_load_environment; print(auto_load_environment().get_contract_addresses())"
```

## Conclusion

The contract discovery system provides a professional, scalable approach to managing deployed contracts across all environments. It eliminates manual configuration, ensures consistency, and provides a foundation for advanced deployment management features.
