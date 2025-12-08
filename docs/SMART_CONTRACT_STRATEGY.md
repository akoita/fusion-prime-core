# Smart Contract Resource Distribution Strategy

## Overview

This document outlines the strategy for making smart contract resources (addresses, ABIs, metadata) accessible to all Fusion Prime services.

## Current Issues

1. **Manual Configuration**: Each service needs individual contract address configuration
2. **No Centralized Registry**: Contract metadata scattered across environment files
3. **ABI Distribution**: ABIs not systematically distributed to services
4. **Version Management**: No clear strategy for contract versioning across services

## Recommended Strategy

### 1. Contract Registry Service

Create a centralized contract registry service that provides:

- **Contract Discovery**: Automatically discover deployed contracts
- **Metadata Management**: Store addresses, ABIs, deployment info
- **Version Control**: Track contract versions and upgrades
- **Service Integration**: Provide APIs for services to fetch contract data

### 2. Multi-Layer Distribution

#### Layer 1: Environment Variables (Current)
```bash
# Basic contract addresses
ESCROW_FACTORY_ADDRESS=0x...
ESCROW_ADDRESS=0x...
```

#### Layer 2: Contract Registry API (Recommended)
```python
# Service integration
from contract_registry import ContractRegistry

registry = ContractRegistry()
factory_contract = registry.get_contract("EscrowFactory", chain_id=11155111)
```

#### Layer 3: GCP Secret Manager (Production)
```bash
# Store sensitive contract data
gcloud secrets create escrow-factory-abi --data-file=contracts/abi/EscrowFactory.json
```

### 3. Service-Specific Requirements

#### Settlement Service
- **Required**: EscrowFactory address and ABI
- **Optional**: Escrow contract ABI for validation
- **Usage**: Create and manage escrow contracts

#### Risk Engine Service
- **Required**: EscrowFactory address and ABI
- **Optional**: Escrow contract ABI for risk assessment
- **Usage**: Monitor contract state for risk calculations

#### Compliance Service
- **Required**: EscrowFactory address and ABI
- **Optional**: Escrow contract ABI for compliance checks
- **Usage**: Validate transactions against compliance rules

#### Event Relayer Service
- **Required**: EscrowFactory address and ABI
- **Required**: Event signatures and topics
- **Usage**: Listen to contract events and relay to Pub/Sub

### 4. Implementation Plan

#### Phase 1: Enhanced Environment Variables
- Add all contract addresses to environment variables
- Include ABI paths for each contract
- Update deployment scripts to pass contract metadata

#### Phase 2: Contract Registry Service
- Create centralized contract registry
- Implement contract discovery from deployment artifacts
- Provide REST API for contract metadata

#### Phase 3: Service Integration
- Update services to use contract registry
- Implement fallback to environment variables
- Add contract validation and health checks

## Environment Variable Strategy

### Required Variables for All Services

```bash
# Contract Addresses
ESCROW_FACTORY_ADDRESS=0x...
ESCROW_ADDRESS=0x...

# Contract ABIs (paths or URLs)
ESCROW_FACTORY_ABI_PATH=contracts/abi/EscrowFactory.json
ESCROW_ABI_PATH=contracts/abi/Escrow.json

# Contract Registry (optional)
CONTRACT_REGISTRY_URL=https://contract-registry.fusion-prime.com
CONTRACT_REGISTRY_API_KEY=...
```

### Service-Specific Variables

```bash
# Settlement Service
SETTLEMENT_CONTRACT_ADDRESSES={"EscrowFactory":"0x...","Escrow":"0x..."}

# Risk Engine Service
RISK_ENGINE_CONTRACT_ADDRESSES={"EscrowFactory":"0x...","Escrow":"0x..."}

# Compliance Service
COMPLIANCE_CONTRACT_ADDRESSES={"EscrowFactory":"0x...","Escrow":"0x..."}

# Event Relayer Service
RELAYER_CONTRACT_ADDRESSES={"EscrowFactory":"0x...","Escrow":"0x..."}
RELAYER_EVENT_TOPICS={"EscrowDeployed":"0x...","EscrowFunded":"0x..."}
```

## Deployment Integration

### 1. Contract Deployment
- Deploy contracts using Foundry
- Store deployment artifacts in GCP Storage
- Update contract registry with new addresses

### 2. Service Deployment
- Pass contract addresses via environment variables
- Include ABI paths in service configuration
- Validate contract accessibility during deployment

### 3. Health Checks
- Verify contract addresses are valid
- Check ABI files are accessible
- Validate contract functions are callable

## Security Considerations

### 1. ABI Distribution
- Store ABIs in GCP Secret Manager for production
- Use public ABIs for testnet environments
- Implement ABI validation and checksums

### 2. Address Validation
- Validate contract addresses are checksummed
- Verify addresses are deployed on correct chain
- Implement address verification in health checks

### 3. Access Control
- Use service accounts for contract registry access
- Implement API authentication for contract metadata
- Log all contract access for audit purposes

## Monitoring and Observability

### 1. Contract Health Monitoring
- Monitor contract accessibility
- Track contract function call success rates
- Alert on contract address changes

### 2. Service Integration Monitoring
- Monitor service-to-contract communication
- Track ABI loading success rates
- Alert on contract registry failures

### 3. Deployment Monitoring
- Track contract deployment success
- Monitor service deployment with new contract addresses
- Alert on contract address mismatches

## Migration Strategy

### Phase 1: Current State
- Use environment variables for contract addresses
- Manual ABI file distribution
- Service-specific contract configuration

### Phase 2: Enhanced Environment Variables
- Add comprehensive contract metadata to environment variables
- Include ABI paths and contract versions
- Update deployment scripts for contract distribution

### Phase 3: Contract Registry Service
- Implement centralized contract registry
- Migrate services to use registry API
- Maintain environment variable fallbacks

### Phase 4: Full Integration
- Remove manual contract configuration
- Implement automatic contract discovery
- Add comprehensive contract monitoring

## Conclusion

The recommended strategy provides a scalable, maintainable approach to smart contract resource distribution across Fusion Prime services. It balances simplicity (environment variables) with sophistication (contract registry) while maintaining security and observability.
