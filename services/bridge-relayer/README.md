# Bridge Relayer Service

Python FastAPI service for monitoring and relaying cross-chain bridge messages, native transfers, and ERC20 transfers.

## 📚 Documentation

- **[Complete Documentation](../contracts/bridge/DOCUMENTATION.md)** - Full documentation with source locations, deployment, and usage
- **[Quick Reference](../contracts/bridge/QUICK_REFERENCE.md)** - Quick reference for common operations

## Features

- ✅ **Event Monitoring**: Watches bridge events on multiple chains
- ✅ **Message Relaying**: Relays messages between chains
- ✅ **Transfer Execution**: Executes native and ERC20 transfers on destination chains
- ✅ **REST API**: HTTP API for querying bridge status
- ✅ **Extensible**: Easy to add new network pairs via configuration

## Architecture

### Components

1. **BridgeMonitor**: Monitors events on all configured chains
2. **BridgeClient**: Client for interacting with bridge contracts
3. **REST API**: FastAPI endpoints for bridge operations

### Flow

1. User initiates transfer on source chain
2. BridgeMonitor detects event
3. Relayer verifies event on source chain
4. Relayer executes transfer on destination chain
5. Status tracked and exposed via API

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL (optional, for tracking transfers)
- Access to RPC endpoints for configured chains

### Installation

```bash
cd services/bridge-relayer
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration

1. Copy environment file:
```bash
cp .env.example .env
```

2. Edit `.env` with your configuration:
```bash
# Relayer Configuration
RELAYER_PRIVATE_KEY=your_relayer_private_key_here
RELAYER_ADDRESS=0x...

# Sepolia Configuration
SEPOLIA_RPC_URL=https://rpc.sepolia.org
SEPOLIA_REGISTRY_ADDRESS=0x...
SEPOLIA_MESSAGE_BRIDGE_ADDRESS=0x...
SEPOLIA_NATIVE_BRIDGE_ADDRESS=0x...
SEPOLIA_ERC20_BRIDGE_ADDRESS=0x...

# Amoy Configuration
AMOY_RPC_URL=https://rpc-amoy.polygon.technology
AMOY_REGISTRY_ADDRESS=0x...
AMOY_MESSAGE_BRIDGE_ADDRESS=0x...
AMOY_NATIVE_BRIDGE_ADDRESS=0x...
AMOY_ERC20_BRIDGE_ADDRESS=0x...
```

## Running Locally

### Development Mode

```bash
uvicorn app.main:app --reload --port 8000
```

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

### Health Check

```bash
GET /health
```

### Send Message

```bash
POST /api/v1/messages/send
{
  "source_chain_id": 11155111,
  "dest_chain_id": 80002,
  "sender": "0x...",
  "recipient": "0x...",
  "payload": "0x..."
}
```

### Get Message Status

```bash
GET /api/v1/messages/{message_id}
```

### Send Native Transfer

```bash
POST /api/v1/transfers/native
{
  "dest_chain_id": 80002,
  "recipient": "0x...",
  "amount": "1000000000000000000"
}
```

### Send ERC20 Transfer

```bash
POST /api/v1/transfers/erc20
{
  "dest_chain_id": 80002,
  "token": "0x...",
  "recipient": "0x...",
  "amount": "1000000000000000000"
}
```

## Deployment

### Local Development

The service runs locally and connects to testnet RPC endpoints.

### GCP Deployment

1. Build Docker image:
```bash
docker build -t bridge-relayer:latest .
```

2. Deploy to Cloud Run:
```bash
gcloud run deploy bridge-relayer \
  --image bridge-relayer:latest \
  --platform managed \
  --region us-central1 \
  --set-env-vars "RELAYER_PRIVATE_KEY=...,SEPOLIA_RPC_URL=..."
```

3. Or use Cloud Build:
```bash
gcloud builds submit --config cloudbuild.yaml
```

## Monitoring

The service logs all bridge events and relay operations. Check logs:

```bash
# Local
tail -f logs/bridge-relayer.log

# GCP
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=bridge-relayer" --limit 50
```

## Adding New Networks

1. Update `config/networks.yaml` with new network configuration
2. Add environment variables for new network's contract addresses
3. Restart the service

## Security Considerations

- **Private Key Security**: Store `RELAYER_PRIVATE_KEY` securely (use GCP Secret Manager in production)
- **Access Control**: Consider adding authentication to API endpoints
- **Rate Limiting**: Implement rate limiting for API endpoints
- **Monitoring**: Monitor for suspicious activity
- **Backup**: Keep backups of relayer private keys

## Troubleshooting

### Service won't start

- Check that all required environment variables are set
- Verify RPC endpoints are accessible
- Check that contract addresses are correct

### Events not being detected

- Verify bridge contract addresses are correct
- Check that relayer address is authorized on bridge contracts
- Verify RPC endpoints are working

### Transfers failing

- Check relayer has sufficient gas on destination chain
- Verify network pair is enabled in registry
- Check amount is within min/max limits

## Next Steps

- [ ] Add database for tracking transfers
- [ ] Implement retry logic for failed relays
- [ ] Add metrics and monitoring
- [ ] Implement signature verification
- [ ] Add comprehensive test coverage
