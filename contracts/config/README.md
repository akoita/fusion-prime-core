# Chain Configuration

This directory contains environment-based configuration for all supported blockchain networks.

## Files

- **`chains.env`** - Environment-based chain configuration
- **`README.md`** - This documentation

## Usage

### Loading Chain Configuration

```python
from contracts.scripts.load_chain_config import get_chain_config, get_supported_chains

# Get configuration for a specific chain
config = get_chain_config('local')
print(f"Chain ID: {config['chain_id']}")
print(f"RPC URL: {config['rpc_url']}")

# List all supported chains
chains = get_supported_chains()
print(f"Supported chains: {chains}")
```

### Command Line Usage

```bash
# Get chain information
python3 contracts/scripts/load_chain_config.py local

# Deploy to a specific chain
python3 contracts/scripts/deploy_with_config.py local
python3 contracts/scripts/deploy_with_config.py sepolia
```

## Configuration Format

The `chains.env` file uses environment variable format:

```bash
# Chain configuration
LOCAL_CHAIN_ID=31337
LOCAL_CHAIN_NAME=local
LOCAL_RPC_URL=http://localhost:8545
LOCAL_IS_TESTNET=true
LOCAL_IS_MAINNET=false
LOCAL_IS_LOCAL=true
```

## Benefits

✅ **No hardcoded values** - All configuration is external
✅ **Environment-based** - Easy to override with actual environment variables
✅ **Flexible** - Add new chains by adding new entries to `chains.env`
✅ **Runtime loading** - Configuration loaded when needed, not compiled in
✅ **Cross-platform** - Works with any deployment script or tool

## Adding New Chains

1. Add entries to `chains.env`:
```bash
NEW_CHAIN_CHAIN_ID=12345
NEW_CHAIN_CHAIN_NAME=new-chain
NEW_CHAIN_RPC_URL=${NEW_CHAIN_RPC_URL}
NEW_CHAIN_IS_TESTNET=true
NEW_CHAIN_IS_MAINNET=false
NEW_CHAIN_IS_LOCAL=false
```

2. Add to supported chains list:
```bash
SUPPORTED_CHAIN_IDS=31337,11155111,80002,1,137,8453,84532,12345
SUPPORTED_CHAIN_NAMES=local,sepolia,amoy,mainnet,polygon,base,base-sepolia,new-chain
```

3. Update deployment script if needed for chain-specific logic

## Environment Variables

The configuration supports environment variable substitution:

```bash
# This will be resolved to the actual RPC URL from environment
SEPOLIA_RPC_URL=${SEPOLIA_RPC_URL}
```

Make sure to set the corresponding environment variables:
```bash
export SEPOLIA_RPC_URL="https://sepolia.infura.io/v3/YOUR_KEY"
```
