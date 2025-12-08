# GCP Contract Management Workflow

## Overview

This document provides step-by-step instructions for managing smart contract resources in GCP environments using the Fusion Prime contract registry system.

## Prerequisites

1. **GCP Project Setup**: Ensure you have a GCP project with the necessary APIs enabled
2. **Authentication**: Authenticate with `gcloud auth login`
3. **Permissions**: Ensure you have Storage Admin and Cloud Run Admin roles
4. **Foundry**: Install Foundry for contract deployment

## Complete Workflow

### Step 1: Deploy Smart Contracts

```bash
# Navigate to contracts directory
cd contracts

# Deploy contracts to Sepolia testnet
forge script script/DeployMultichain.s.sol:DeployMultichain \
  --rpc-url $RPC_URL \
  --broadcast \
  --verify

# Note the deployment addresses from the output
```

### Step 2: Upload Contract Artifacts to GCP

```bash
# Upload deployment artifacts to GCS
./scripts/gcp-contract-registry.sh upload \
  --env dev \
  --project fusion-prime \
  --chain-id 11155111

# This will:
# - Create gs://fusion-prime-contract-registry bucket if it doesn't exist
# - Upload deployment.json with Foundry artifacts
# - Upload EscrowFactory.json and Escrow.json ABIs
# - Create metadata.json with contract information
```

### Step 3: Update Environment Configuration

```bash
# Update .env.dev with contract addresses
./scripts/update-contract-addresses.sh \
  --env dev \
  --chain-id 11155111

# This will update:
# - .env.dev with ESCROW_FACTORY_ADDRESS and ESCROW_ADDRESS
# - env.dev.example with the same addresses
```

### Step 4: Deploy Services

```bash
# Deploy all services with contract registry configuration
./scripts/deploy-unified.sh --env dev --services all --ci-mode

# This will:
# - Deploy services with contract addresses from registry (if available)
# - Include GCS URLs for contract ABIs
# - Set up contract registry configuration
# - Fall back to environment variables if registry not available
```

### Step 5: Update Services with Contract Addresses (Optional)

```bash
# Update Cloud Run services with specific contract addresses
./scripts/update-services-contracts.sh \
  --env dev \
  --project fusion-prime

# This will:
# - Get contract addresses from registry
# - Update all Cloud Run services with the addresses
# - Verify services are accessible
```

### Step 6: Verify Deployment

```bash
# List available contract deployments
./scripts/gcp-contract-registry.sh list \
  --env dev \
  --project fusion-prime

# Check service health
curl https://settlement-service-xxx.us-central1.run.app/health/contracts
curl https://risk-engine-xxx.us-central1.run.app/health/contracts
```

## Service Integration Examples

### Settlement Service Integration

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

### Risk Engine Service Integration

```python
# services/risk-engine/app/main.py
from services.shared.contract_registry import ContractRegistry

# Initialize contract registry
registry = ContractRegistry()

# Get contract resources for risk monitoring
factory_address = registry.get_contract_address('EscrowFactory')
factory_abi = registry.get_contract_abi('EscrowFactory')

# Monitor contract events for risk assessment
def monitor_escrow_events():
    factory_contract = web3.eth.contract(
        address=factory_address,
        abi=factory_abi
    )

    # Listen for EscrowDeployed events
    event_filter = factory_contract.events.EscrowDeployed.create_filter(
        fromBlock='latest'
    )

    for event in event_filter.get_new_entries():
        # Process event for risk assessment
        process_escrow_event(event)
```

### Event Relayer Service Integration

```python
# services/relayer/app/main.py
from services.shared.contract_registry import ContractRegistry

# Initialize contract registry
registry = ContractRegistry()

# Get contract resources for event relaying
factory_address = registry.get_contract_address('EscrowFactory')
factory_abi = registry.get_contract_abi('EscrowFactory')

# Set up event relaying
def setup_event_relaying():
    factory_contract = web3.eth.contract(
        address=factory_address,
        abi=factory_abi
    )

    # Configure event topics
    event_topics = {
        'EscrowDeployed': factory_contract.events.EscrowDeployed.build_filter().topics[0]
    }

    # Start relaying events to Pub/Sub
    relay_events_to_pubsub(factory_contract, event_topics)
```

## Environment-Specific Workflows

### Development Environment

```bash
# 1. Deploy to Sepolia
forge script script/DeployMultichain.s.sol:DeployMultichain \
  --rpc-url $SEPOLIA_RPC_URL \
  --broadcast

# 2. Upload to GCS
./scripts/gcp-contract-registry.sh upload \
  --env dev \
  --project fusion-prime-dev \
  --chain-id 11155111

# 3. Deploy services
./scripts/deploy-unified.sh --env dev --services all --ci-mode

# 4. Update services with addresses (optional)
./scripts/update-services-contracts.sh \
  --env dev \
  --project fusion-prime-dev
```

### Staging Environment

```bash
# 1. Deploy to Sepolia (staging)
forge script script/DeployMultichain.s.sol:DeployMultichain \
  --rpc-url $SEPOLIA_RPC_URL \
  --broadcast

# 2. Upload to GCS
./scripts/gcp-contract-registry.sh upload \
  --env staging \
  --project fusion-prime-staging \
  --chain-id 11155111

# 3. Deploy services
./scripts/deploy-unified.sh --env staging --services all --ci-mode

# 4. Update services with addresses (optional)
./scripts/update-services-contracts.sh \
  --env staging \
  --project fusion-prime-staging
```

### Production Environment

```bash
# 1. Deploy to Ethereum Mainnet
forge script script/DeployMultichain.s.sol:DeployMultichain \
  --rpc-url $MAINNET_RPC_URL \
  --broadcast \
  --verify

# 2. Upload to GCS
./scripts/gcp-contract-registry.sh upload \
  --env production \
  --project fusion-prime-prod \
  --chain-id 1

# 3. Deploy services
./scripts/deploy-unified.sh --env production --services all --ci-mode

# 4. Update services with addresses (optional)
./scripts/update-services-contracts.sh \
  --env production \
  --project fusion-prime-prod
```

## Troubleshooting

### Common Issues

#### 1. Contract Address Not Found
```bash
# Check if contract addresses are set in environment
echo $ESCROW_FACTORY_ADDRESS
echo $ESCROW_ADDRESS

# Update addresses from deployment artifacts
./scripts/update-contract-addresses.sh --env dev --chain-id 11155111
```

#### 2. ABI Loading Failed
```bash
# Check if ABI files exist in GCS
gsutil ls gs://fusion-prime-contract-registry/contracts/dev/11155111/

# Re-upload contract artifacts
./scripts/gcp-contract-registry.sh upload --env dev --project fusion-prime --chain-id 11155111
```

#### 3. Service Update Failed
```bash
# Check service status
gcloud run services list --region=us-central1

# Update services manually
gcloud run services update settlement-service \
  --region=us-central1 \
  --set-env-vars=ESCROW_FACTORY_ADDRESS=0x...
```

#### 4. Contract Registry Access Denied
```bash
# Check authentication
gcloud auth list

# Check permissions
gcloud projects get-iam-policy fusion-prime

# Grant necessary permissions
gcloud projects add-iam-policy-binding fusion-prime \
  --member="user:your-email@example.com" \
  --role="roles/storage.admin"
```

### Health Checks

#### Service Health Check
```bash
# Check settlement service
curl https://settlement-service-xxx.us-central1.run.app/health/contracts

# Check risk engine
curl https://risk-engine-xxx.us-central1.run.app/health/contracts

# Check compliance service
curl https://compliance-xxx.us-central1.run.app/health/contracts
```

#### Contract Registry Health Check
```bash
# List available deployments
./scripts/gcp-contract-registry.sh list --env dev --project fusion-prime

# Check GCS bucket contents
gsutil ls -r gs://fusion-prime-contract-registry/contracts/dev/
```

## Best Practices

### 1. Contract Deployment
- Always verify contracts after deployment
- Upload artifacts immediately after deployment
- Tag deployments with environment and version
- Keep deployment artifacts for rollback purposes

### 2. Service Updates
- Update all services atomically
- Verify contract accessibility after updates
- Implement health checks for contract loading
- Monitor service logs for contract-related errors

### 3. Security
- Use least-privilege service accounts
- Store sensitive data in Secret Manager
- Validate contract addresses before use
- Implement access controls for contract registry

### 4. Monitoring
- Monitor contract loading success rates
- Alert on contract address changes
- Track service integration health
- Log contract access for audit purposes

## Conclusion

This workflow provides a complete solution for managing smart contract resources in GCP environments. It ensures that all services have access to the necessary contract information while maintaining security, reliability, and observability best practices.
