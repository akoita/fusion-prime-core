# GCP Contract Resource Management Strategy

## Overview

This document outlines the comprehensive strategy for managing smart contract resources in GCP environments, addressing the challenge of making contract addresses, ABIs, and metadata accessible to all Fusion Prime services in remote deployments.

## Problem Statement

### Local vs GCP Environment Differences

**Local Development:**
- Contract artifacts stored in `contracts/broadcast/` directory
- Easy access to deployment results via file system
- Direct integration with Foundry toolchain
- Simple contract discovery from local files

**GCP Environments:**
- No direct access to local file system
- Contract artifacts need to be stored in GCP services
- Services run in isolated containers
- Need centralized contract registry for discovery

## GCP Contract Registry Architecture

### 1. Storage Strategy

#### Cloud Storage Bucket Structure
```
gs://{project}-contract-registry/
├── contracts/
│   ├── dev/
│   │   ├── 11155111/                    # Sepolia
│   │   │   ├── deployment.json          # Foundry deployment artifact
│   │   │   ├── metadata.json            # Contract metadata
│   │   │   ├── EscrowFactory.json       # Factory ABI
│   │   │   └── Escrow.json              # Escrow ABI
│   │   └── 1/                           # Ethereum Mainnet
│   │       └── ...
│   ├── staging/
│   │   └── 11155111/
│   │       └── ...
│   └── production/
│       └── 1/
│           └── ...
```

#### Contract Metadata Format
```json
{
  "environment": "dev",
  "chain_id": "11155111",
  "deployment_time": "2024-01-15T10:30:00Z",
  "deployment_artifact": "deployment.json",
  "contracts": {
    "EscrowFactory": {
      "abi_file": "EscrowFactory.json",
      "address": "0x1234...",
      "deployment_tx": "0xabcd...",
      "block_number": 12345678
    },
    "Escrow": {
      "abi_file": "Escrow.json",
      "address": "0x5678...",
      "deployment_tx": "0xefgh...",
      "block_number": 12345679
    }
  }
}
```

### 2. Service Integration Strategy

#### Environment Variable Distribution
All services receive contract resources via environment variables:

```bash
# Contract Addresses
ESCROW_FACTORY_ADDRESS=0x1234...
ESCROW_ADDRESS=0x5678...

# Contract ABIs (GCS URLs)
ESCROW_FACTORY_ABI_URL=gs://fusion-prime-contract-registry/contracts/dev/11155111/EscrowFactory.json
ESCROW_ABI_URL=gs://fusion-prime-contract-registry/contracts/dev/11155111/Escrow.json

# Contract Registry
CONTRACT_REGISTRY_BUCKET=fusion-prime-contract-registry
CONTRACT_REGISTRY_CHAIN_ID=11155111
```

#### Service-Specific Contract Usage

**Settlement Service:**
- **Primary**: EscrowFactory address and ABI for creating escrows
- **Secondary**: Escrow ABI for validation and interaction
- **Storage**: Contract addresses in environment variables
- **Runtime**: Load ABIs from GCS URLs

**Risk Engine Service:**
- **Primary**: EscrowFactory address and ABI for monitoring
- **Secondary**: Escrow ABI for risk calculations
- **Storage**: Contract addresses in environment variables
- **Runtime**: Load ABIs from GCS URLs

**Compliance Service:**
- **Primary**: EscrowFactory address and ABI for compliance checks
- **Secondary**: Escrow ABI for transaction validation
- **Storage**: Contract addresses in environment variables
- **Runtime**: Load ABIs from GCS URLs

**Event Relayer Service:**
- **Primary**: EscrowFactory address and ABI for event listening
- **Secondary**: Escrow ABI for event parsing
- **Storage**: Contract addresses in environment variables
- **Runtime**: Load ABIs from GCS URLs

### 3. Deployment Workflow

#### Phase 1: Contract Deployment
```bash
# 1. Deploy contracts using Foundry
cd contracts
forge script script/DeployMultichain.s.sol:DeployMultichain \
  --rpc-url $RPC_URL \
  --broadcast

# 2. Upload artifacts to GCP Storage
./scripts/gcp-contract-registry.sh upload \
  --env dev \
  --project fusion-prime \
  --chain-id 11155111
```

#### Phase 2: Service Deployment
```bash
# 1. Deploy services with contract registry info
./scripts/deploy-unified.sh --env dev --services all

# 2. Update services with specific contract addresses
./scripts/gcp-contract-registry.sh update-services \
  --env dev \
  --project fusion-prime
```

#### Phase 3: Service Integration
```python
# Service code example
import os
from google.cloud import storage
import json

class ContractRegistry:
    def __init__(self):
        self.bucket_name = os.getenv('CONTRACT_REGISTRY_BUCKET')
        self.environment = os.getenv('CONTRACT_REGISTRY_ENV')
        self.chain_id = os.getenv('CONTRACT_REGISTRY_CHAIN_ID')
        self.client = storage.Client()

    def get_contract_address(self, contract_name: str) -> str:
        """Get contract address from environment variables."""
        return os.getenv(f'{contract_name.upper()}_ADDRESS')

    def get_contract_abi(self, contract_name: str) -> list:
        """Load contract ABI from GCS."""
        abi_url = os.getenv(f'{contract_name.upper()}_ABI_URL')
        if not abi_url:
            raise ValueError(f'ABI URL not found for {contract_name}')

        # Parse GCS URL
        bucket_name = abi_url.split('/')[2]
        blob_name = '/'.join(abi_url.split('/')[3:])

        blob = self.client.bucket(bucket_name).blob(blob_name)
        abi_data = json.loads(blob.download_as_text())
        return abi_data['abi']
```

## Implementation Details

### 1. GCP Contract Registry Script

The `scripts/gcp-contract-registry.sh` script provides:

**Upload Contract Artifacts:**
```bash
./scripts/gcp-contract-registry.sh upload \
  --env dev \
  --project fusion-prime \
  --chain-id 11155111
```

**Update Cloud Run Services:**
```bash
./scripts/gcp-contract-registry.sh update-services \
  --env dev \
  --project fusion-prime
```

**Download Contract Artifacts:**
```bash
./scripts/gcp-contract-registry.sh download \
  --env dev \
  --project fusion-prime \
  --chain-id 11155111
```

**List Available Deployments:**
```bash
./scripts/gcp-contract-registry.sh list \
  --env dev \
  --project fusion-prime
```

### 2. Service Account Permissions

Required IAM roles for contract registry access:

```bash
# Service account for contract registry operations
gcloud iam service-accounts create contract-registry-sa

# Storage permissions
gcloud projects add-iam-policy-binding fusion-prime \
  --member="serviceAccount:contract-registry-sa@fusion-prime.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

# Cloud Run permissions for service updates
gcloud projects add-iam-policy-binding fusion-prime \
  --member="serviceAccount:contract-registry-sa@fusion-prime.iam.gserviceaccount.com" \
  --role="roles/run.admin"
```

### 3. Service Integration Patterns

#### Pattern 1: Environment Variable + GCS ABI Loading
```python
# Services load addresses from env vars and ABIs from GCS
factory_address = os.getenv('ESCROW_FACTORY_ADDRESS')
factory_abi = load_abi_from_gcs(os.getenv('ESCROW_FACTORY_ABI_URL'))
```

#### Pattern 2: Contract Registry Service
```python
# Services use a centralized contract registry service
from contract_registry import ContractRegistry

registry = ContractRegistry()
factory_contract = registry.get_contract('EscrowFactory')
```

#### Pattern 3: Secret Manager Integration
```python
# Sensitive contract data stored in Secret Manager
from google.cloud import secretmanager

def get_contract_abi(contract_name: str) -> list:
    client = secretmanager.SecretManagerServiceClient()
    secret_name = f"contracts/{contract_name}/abi"
    response = client.access_secret_version(request={"name": secret_name})
    return json.loads(response.payload.data.decode("UTF-8"))
```

## Security Considerations

### 1. Access Control
- **Bucket Permissions**: Restrict access to contract registry bucket
- **Service Accounts**: Use least-privilege service accounts
- **IAM Policies**: Implement environment-specific access controls

### 2. Data Protection
- **ABI Storage**: Store ABIs in GCS (public data)
- **Private Keys**: Store in Secret Manager (never in GCS)
- **Address Validation**: Verify contract addresses are checksummed

### 3. Audit and Monitoring
- **Access Logging**: Enable Cloud Audit Logs for GCS access
- **Service Monitoring**: Monitor contract loading success rates
- **Alerting**: Alert on contract address changes or failures

## Monitoring and Observability

### 1. Contract Health Monitoring
```python
# Health check endpoint for contract accessibility
@app.get("/health/contracts")
async def contract_health():
    try:
        factory_address = os.getenv('ESCROW_FACTORY_ADDRESS')
        factory_abi = load_abi_from_gcs(os.getenv('ESCROW_FACTORY_ABI_URL'))

        # Verify contract is accessible
        web3 = Web3(Web3.HTTPProvider(os.getenv('RPC_URL')))
        contract = web3.eth.contract(address=factory_address, abi=factory_abi)
        contract.functions.owner().call()

        return {"status": "healthy", "contracts": "accessible"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

### 2. Service Integration Monitoring
- **Contract Loading Success Rate**: Monitor ABI loading from GCS
- **Contract Call Success Rate**: Monitor contract function calls
- **Address Validation**: Verify contract addresses are valid

### 3. Deployment Monitoring
- **Contract Upload Success**: Monitor artifact upload to GCS
- **Service Update Success**: Monitor Cloud Run service updates
- **Contract Discovery**: Monitor contract address extraction

## Migration Strategy

### Phase 1: Basic GCS Storage
- Upload contract artifacts to GCS
- Update services with GCS URLs for ABIs
- Maintain environment variables for addresses

### Phase 2: Enhanced Metadata
- Add comprehensive contract metadata
- Implement contract versioning
- Add deployment tracking

### Phase 3: Service Integration
- Update services to use contract registry
- Implement automatic contract discovery
- Add health checks and monitoring

### Phase 4: Advanced Features
- Implement contract registry service
- Add contract upgrade management
- Implement cross-chain contract tracking

## Best Practices

### 1. Contract Deployment
- Always upload artifacts after deployment
- Include comprehensive metadata
- Tag deployments with environment and version

### 2. Service Updates
- Update all services atomically
- Verify contract accessibility after updates
- Implement rollback procedures

### 3. Monitoring
- Monitor contract loading success rates
- Alert on contract address changes
- Track service integration health

## Conclusion

This GCP contract resource management strategy provides a scalable, secure, and maintainable approach to distributing smart contract resources across Fusion Prime services in remote environments. It addresses the key challenges of contract discovery, ABI distribution, and service integration while maintaining security and observability best practices.
