# Contract Registry Architecture

## Overview

This document explains the separation of concerns in the Fusion Prime contract resource management system, ensuring each component has a single, well-defined responsibility.

## Architecture Principles

### 1. Separation of Concerns
- **Contract Registry**: Manages contract resources (addresses, ABIs, metadata)
- **Service Management**: Handles Cloud Run service lifecycle
- **Deployment Orchestration**: Coordinates the overall deployment process

### 2. Single Responsibility
Each script has one clear purpose:
- `gcp-contract-registry.sh`: Contract resource management only
- `update-services-contracts.sh`: Service updates using contract resources
- `deploy-unified.sh`: High-level deployment orchestration

## Component Overview

### Contract Registry (`scripts/gcp-contract-registry.sh`)

**Purpose**: Pure contract resource management
**Responsibilities**:
- Upload contract artifacts to GCS
- Download contract artifacts from GCS
- List available contract deployments
- Get contract addresses from registry
- Get deployment metadata from registry

**Actions**:
```bash
# Upload contract artifacts
./scripts/gcp-contract-registry.sh upload --env dev --project fusion-prime --chain-id 11155111

# Download contract artifacts
./scripts/gcp-contract-registry.sh download --env dev --project fusion-prime --chain-id 11155111

# List available deployments
./scripts/gcp-contract-registry.sh list --env dev --project fusion-prime

# Get contract addresses (for use by other scripts)
./scripts/gcp-contract-registry.sh get-addresses --env dev --project fusion-prime --chain-id 11155111

# Get deployment metadata
./scripts/gcp-contract-registry.sh get-metadata --env dev --project fusion-prime --chain-id 11155111
```

**Output Format**:
- `get-addresses`: Environment variable format (`ESCROW_FACTORY_ADDRESS=0x...`)
- `get-metadata`: JSON metadata
- Other actions: Status messages and file operations

### Service Update Script (`scripts/update-services-contracts.sh`)

**Purpose**: Update Cloud Run services with contract addresses
**Responsibilities**:
- Get contract addresses from registry
- Update Cloud Run services with addresses
- Handle service-specific logic
- Provide service update status

**Usage**:
```bash
# Update all services
./scripts/update-services-contracts.sh --env dev --project fusion-prime

# Update specific services
./scripts/update-services-contracts.sh --env dev --project fusion-prime --services settlement-service,risk-engine

# Dry run
./scripts/update-services-contracts.sh --env dev --project fusion-prime --dry-run
```

**Dependencies**:
- Uses `gcp-contract-registry.sh` to get contract addresses
- Requires `gcloud` CLI for Cloud Run operations
- Needs appropriate GCP permissions

### Deployment Orchestration (`scripts/deploy-unified.sh`)

**Purpose**: High-level deployment coordination
**Responsibilities**:
- Deploy services to Cloud Run
- Coordinate contract resource integration
- Handle environment-specific configuration
- Orchestrate the overall deployment process

**Contract Integration**:
- Attempts to get contract addresses from registry first
- Falls back to environment variables if registry unavailable
- Includes GCS URLs for contract ABIs
- Handles both local and remote environments

## Data Flow

### 1. Contract Deployment Flow
```
Foundry Deployment → Contract Artifacts → GCS Upload → Registry Metadata
```

### 2. Service Deployment Flow
```
Registry Query → Contract Addresses → Service Environment Variables → Cloud Run Deploy
```

### 3. Service Update Flow
```
Registry Query → Contract Addresses → Cloud Run Service Update
```

## Integration Patterns

### Pattern 1: Registry-First Approach
```bash
# 1. Upload contracts to registry
./scripts/gcp-contract-registry.sh upload --env dev --project fusion-prime --chain-id 11155111

# 2. Deploy services (automatically uses registry)
./scripts/deploy-unified.sh --env dev --services all --ci-mode

# 3. Update services with latest addresses (optional)
./scripts/update-services-contracts.sh --env dev --project fusion-prime
```

### Pattern 2: Environment Variable Fallback
```bash
# 1. Set contract addresses in environment
export ESCROW_FACTORY_ADDRESS=0x...
export ESCROW_ADDRESS=0x...

# 2. Deploy services (uses environment variables)
./scripts/deploy-unified.sh --env dev --services all --ci-mode
```

### Pattern 3: Hybrid Approach
```bash
# 1. Upload contracts to registry
./scripts/gcp-contract-registry.sh upload --env dev --project fusion-prime --chain-id 11155111

# 2. Deploy services (registry + environment variables)
./scripts/deploy-unified.sh --env dev --services all --ci-mode

# 3. Services get addresses from registry, fallback to env vars
```

## Benefits of This Architecture

### 1. Modularity
- Each script has a single, clear purpose
- Easy to test and maintain individual components
- Clear separation between contract and service concerns

### 2. Flexibility
- Can use registry, environment variables, or both
- Easy to add new contract resources
- Supports different deployment strategies

### 3. Reusability
- Contract registry can be used by any service
- Service update script can be used independently
- Deployment script handles orchestration

### 4. Maintainability
- Changes to contract management don't affect service logic
- Service updates don't affect contract registry
- Clear interfaces between components

## Error Handling

### Contract Registry Errors
- Missing deployment artifacts
- GCS access issues
- Invalid contract metadata
- Network connectivity problems

### Service Update Errors
- Service not found
- Permission denied
- Invalid contract addresses
- Cloud Run API errors

### Deployment Errors
- Registry unavailable (falls back to env vars)
- Invalid environment configuration
- Service deployment failures
- Contract address validation errors

## Security Considerations

### Contract Registry Security
- GCS bucket permissions
- Service account authentication
- Contract address validation
- ABI integrity checks

### Service Update Security
- Cloud Run service permissions
- Environment variable validation
- Address verification
- Audit logging

## Monitoring and Observability

### Contract Registry Monitoring
- Upload/download success rates
- Contract address availability
- Metadata integrity
- GCS access patterns

### Service Update Monitoring
- Service update success rates
- Contract address propagation
- Service health checks
- Update rollback capabilities

## Future Enhancements

### Contract Registry
- Contract versioning
- Multi-chain support
- Contract upgrade management
- ABI validation and verification

### Service Management
- Blue-green deployments
- Canary releases
- Service health monitoring
- Automatic rollback

### Deployment Orchestration
- GitOps integration
- CI/CD pipeline integration
- Environment promotion
- Automated testing

## Conclusion

This architecture provides a clean separation of concerns while maintaining flexibility and reusability. Each component has a single responsibility, making the system easier to understand, maintain, and extend.
