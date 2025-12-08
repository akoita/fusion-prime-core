# Service ABI Access Guide

## Overview

This document explains how Fusion Prime services access smart contract ABIs in different environments (local, dev, staging, production).

## ABI Access Methods

### 1. Environment Variable Configuration

Services receive ABI access information via environment variables:

```bash
# Contract Addresses
ESCROW_FACTORY_ADDRESS=0x1234...
ESCROW_ADDRESS=0x5678...

# ABI Access Methods (in priority order)
ESCROW_FACTORY_ABI_URL=gs://fusion-prime-contract-registry/contracts/dev/11155111/EscrowFactory.json
ESCROW_FACTORY_ABI_PATH=contracts/abi/EscrowFactory.json

ESCROW_ABI_URL=gs://fusion-prime-contract-registry/contracts/dev/11155111/Escrow.json
ESCROW_ABI_PATH=contracts/abi/Escrow.json

# Contract Registry Configuration
CONTRACT_REGISTRY_BUCKET=fusion-prime-contract-registry
CONTRACT_REGISTRY_CHAIN_ID=11155111
```

### 2. ABI Loading Priority

The `ContractRegistry` class loads ABIs in this priority order:

1. **GCS URL** (`ESCROW_FACTORY_ABI_URL`) - For GCP environments
2. **Local File Path** (`ESCROW_FACTORY_ABI_PATH`) - For local development
3. **Contract Registry** - Fallback to registry lookup

## Service Integration Examples

### Method 1: Using Contract Registry Library (Recommended)

```python
# services/settlement/app/main.py
from services.shared.contract_registry import ContractRegistry
from web3 import Web3

# Initialize contract registry
registry = ContractRegistry()

# Get contract resources
factory_address = registry.get_contract_address('EscrowFactory')
factory_abi = registry.get_contract_abi('EscrowFactory')

# Create Web3 contract instance
web3 = Web3(Web3.HTTPProvider(os.getenv('RPC_URL')))
factory_contract = web3.eth.contract(
    address=factory_address,
    abi=factory_abi
)

# Use contract in service logic
def create_escrow(payer, payee, amount):
    tx = factory_contract.functions.createEscrow(
        payer, payee, amount
    ).build_transaction({
        'from': payer,
        'gas': 200000,
        'gasPrice': web3.eth.gas_price
    })
    return tx
```

### Method 2: Direct Environment Variable Access (Current)

```python
# services/relayer/app/main.py
import json
import os
from web3 import Web3

# Get contract address
factory_address = os.getenv("ESCROW_FACTORY_ADDRESS")

# Load ABI from file path (current approach)
factory_abi_path = os.getenv("ESCROW_FACTORY_ABI_PATH")
with open(factory_abi_path, 'r') as f:
    contract_json = json.load(f)
    factory_abi = contract_json.get('abi', contract_json)

# Create Web3 contract
web3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))
factory_contract = web3.eth.contract(
    address=factory_address,
    abi=factory_abi
)
```

### Method 3: GCS URL Loading (For GCP Environments)

```python
# services/risk-engine/app/contract_client.py
import json
import os
from google.cloud import storage
from web3 import Web3

def load_abi_from_gcs(gcs_url: str) -> list:
    """Load ABI from GCS URL."""
    # Parse GCS URL: gs://bucket/path/to/file.json
    if not gcs_url.startswith('gs://'):
        raise ValueError(f"Invalid GCS URL: {gcs_url}")

    path_parts = gcs_url[5:].split('/', 1)  # Remove 'gs://' and split
    bucket_name, blob_name = path_parts

    # Load from GCS
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    abi_json = blob.download_as_text()
    abi_data = json.loads(abi_json)

    # Handle different ABI formats
    if isinstance(abi_data, list):
        return abi_data
    elif isinstance(abi_data, dict) and 'abi' in abi_data:
        return abi_data['abi']
    else:
        raise ValueError(f"Invalid ABI format in {gcs_url}")

# Usage
factory_address = os.getenv("ESCROW_FACTORY_ADDRESS")
factory_abi_url = os.getenv("ESCROW_FACTORY_ABI_URL")

if factory_abi_url:
    factory_abi = load_abi_from_gcs(factory_abi_url)
else:
    # Fallback to local file
    factory_abi_path = os.getenv("ESCROW_FACTORY_ABI_PATH")
    with open(factory_abi_path, 'r') as f:
        factory_abi = json.load(f)['abi']

# Create contract
web3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))
factory_contract = web3.eth.contract(
    address=factory_address,
    abi=factory_abi
)
```

## Environment-Specific ABI Access

### Local Development

**Configuration:**
```bash
# .env.local
ESCROW_FACTORY_ADDRESS=0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512
ESCROW_FACTORY_ABI_PATH=contracts/abi/EscrowFactory.json
```

**Service Code:**
```python
# Load from local file
abi_path = os.getenv("ESCROW_FACTORY_ABI_PATH")
with open(abi_path, 'r') as f:
    abi = json.load(f)['abi']
```

### GCP Development/Staging/Production

**Configuration:**
```bash
# Environment variables set by deployment script
ESCROW_FACTORY_ADDRESS=0x1234...
ESCROW_FACTORY_ABI_URL=gs://fusion-prime-contract-registry/contracts/dev/11155111/EscrowFactory.json
CONTRACT_REGISTRY_BUCKET=fusion-prime-contract-registry
CONTRACT_REGISTRY_ENV=dev
CONTRACT_REGISTRY_CHAIN_ID=11155111
```

**Service Code:**
```python
# Using ContractRegistry (recommended)
from services.shared.contract_registry import ContractRegistry

registry = ContractRegistry()
abi = registry.get_contract_abi('EscrowFactory')
```

## ABI File Structure

### Foundry Compilation Output
```json
{
  "abi": [
    {
      "inputs": [...],
      "name": "createEscrow",
      "outputs": [...],
      "stateMutability": "nonpayable",
      "type": "function"
    }
  ],
  "bytecode": "0x608060405234801561001057600080fd5b50...",
  "deployedBytecode": "0x608060405234801561001057600080fd5b50..."
}
```

### GCS Storage Structure
```
gs://fusion-prime-contract-registry/
├── contracts/
│   ├── dev/11155111/
│   │   ├── EscrowFactory.json    # Full Foundry artifact
│   │   └── Escrow.json           # Full Foundry artifact
│   └── production/1/
│       ├── EscrowFactory.json
│       └── Escrow.json
```

## Service Health Checks

### Contract Registry Health Check
```python
# services/settlement/app/health.py
from services.shared.contract_registry import health_check

@app.get("/health/contracts")
async def contract_health():
    """Check contract accessibility."""
    try:
        health = health_check()
        return health
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

### Manual Health Check
```python
# services/risk-engine/app/health.py
import os
from web3 import Web3

@app.get("/health/contracts")
async def contract_health():
    """Check contract accessibility."""
    try:
        # Check address
        factory_address = os.getenv("ESCROW_FACTORY_ADDRESS")
        if not factory_address:
            return {"status": "unhealthy", "error": "No contract address"}

        # Check ABI loading
        registry = ContractRegistry()
        abi = registry.get_contract_abi('EscrowFactory')

        # Check contract accessibility
        web3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))
        contract = web3.eth.contract(address=factory_address, abi=abi)
        contract.functions.owner().call()

        return {"status": "healthy", "contracts": "accessible"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

## Error Handling

### Common ABI Loading Errors

1. **Missing Environment Variables**
```python
try:
    abi = registry.get_contract_abi('EscrowFactory')
except ValueError as e:
    logger.error(f"ABI loading failed: {e}")
    # Fallback or exit
```

2. **GCS Access Errors**
```python
try:
    abi = load_abi_from_gcs(abi_url)
except Exception as e:
    logger.warning(f"GCS ABI loading failed: {e}")
    # Fallback to local file
    abi = load_abi_from_file(abi_path)
```

3. **Invalid ABI Format**
```python
try:
    abi = json.loads(abi_data)['abi']
except (KeyError, json.JSONDecodeError) as e:
    logger.error(f"Invalid ABI format: {e}")
    # Handle error
```

## Best Practices

### 1. Use Contract Registry Library
- Provides consistent ABI loading across all services
- Handles multiple ABI sources automatically
- Includes caching and error handling

### 2. Implement Health Checks
- Monitor ABI loading success rates
- Alert on contract accessibility issues
- Provide fallback mechanisms

### 3. Error Handling
- Graceful fallback from GCS to local files
- Clear error messages for debugging
- Proper logging for troubleshooting

### 4. Caching
- Cache loaded ABIs to avoid repeated GCS calls
- Implement cache invalidation for updates
- Monitor cache hit rates

## Migration Guide

### From Direct File Loading to Contract Registry

**Before:**
```python
# Direct file loading
abi_path = os.getenv("ESCROW_FACTORY_ABI_PATH")
with open(abi_path, 'r') as f:
    abi = json.load(f)['abi']
```

**After:**
```python
# Using ContractRegistry
from services.shared.contract_registry import ContractRegistry

registry = ContractRegistry()
abi = registry.get_contract_abi('EscrowFactory')
```

### Benefits of Migration
- Automatic GCS URL handling
- Consistent error handling
- Built-in caching
- Health check integration
- Future-proof for new ABI sources

## Conclusion

Services can access ABIs through multiple methods, with the Contract Registry library providing the most robust and flexible approach. The system supports both local development (file-based) and GCP environments (GCS-based) with automatic fallback mechanisms.
