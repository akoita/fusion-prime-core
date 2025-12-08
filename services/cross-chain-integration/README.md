# Cross-Chain Integration Service

Monitors and orchestrates cross-chain messages via Axelar and Chainlink CCIP.

## Features

- **Message Monitoring**: Track cross-chain messages via AxelarScan API and CCIP
- **Status Tracking**: Monitor message delivery and finality across chains
- **Retry Logic**: Automatic retry for failed cross-chain transfers
- **Settlement Orchestration**: Coordinate cross-chain settlements
- **Collateral Aggregation**: Aggregate collateral snapshots across all chains

## API Endpoints

### Messages

- `GET /api/v1/messages/` - List cross-chain messages (with filters)
- `GET /api/v1/messages/{message_id}` - Get message details
- `POST /api/v1/messages/{message_id}/retry` - Retry failed message

### Orchestrator

- `POST /api/v1/orchestrator/settlement` - Initiate cross-chain settlement
- `GET /api/v1/orchestrator/collateral/{user_id}` - Get aggregated collateral snapshot
- `GET /api/v1/orchestrator/status/{settlement_id}` - Get settlement status

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host/db

# GCP
GCP_PROJECT=your-project-id
CROSS_CHAIN_MESSAGES_TOPIC=cross-chain.messages.v1

# Message Monitoring
MESSAGE_MONITOR_INTERVAL=30  # seconds
AXELAR_API_URL=https://api-axelarscan-4ae3bd1a8ade.herokuapp.com
```

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn app.main:app --reload --port 8080
```

## Testing

See [TESTING.md](./TESTING.md) for comprehensive testing guide.

**Quick Start:**
```bash
cd services/cross-chain-integration
PYTHONPATH=. python -m pytest tests/ -v
```

**Test Coverage:**
- ✅ RetryCoordinator (7 tests)
- ✅ CCIPClient (5 tests)
- ✅ VaultClient (5 tests)
- ✅ OrchestratorService (5 tests)
- **Total: 22 tests, all passing**

## Deployment

See `cloudbuild.yaml` for Cloud Run deployment configuration.

### Recent Deployment Updates (November 2024)

**Cross-Chain Contracts Deployed:**
- **Ethereum Sepolia (Chain ID: 11155111)**:
  - CrossChainVault: `0x0C95a78b0D72F882fae14CD7C842a5f000E0c4e2`
  - BridgeManager: `0xC96DA7e94E8407e0988bb60A1b23B9358Cd63A56`
  - AxelarAdapter: `0x3C8e965aFF06DFcaE9f6cc778b38d72D54D1381d`
  - CCIPAdapter: `0x9204E095e6d50Ff8f828e71F4C0849C5aEfe992c`

- **Polygon Amoy (Chain ID: 80002)**:
  - CrossChainVault: `0x7843C2eD8930210142DC51dbDf8419C74FD27529`
  - BridgeManager: `0x3481dbE036C0F4076B397e27FFb8dC32B88d8882`
  - AxelarAdapter: `0x6e48D179CD80979c8eDf65A5d783B501A0313159`
  - CCIPAdapter: `0xe15A30f1eF8c1De56F19b7Cef61cC3776119451C`

**Service URL:**
- Production: `https://cross-chain-integration-service-961424092563.us-central1.run.app`

**Environment Variables:**
- `DATABASE_URL` - PostgreSQL connection (from Secret Manager)
- `ETH_RPC_URL` - Ethereum Sepolia RPC endpoint
- `POLYGON_RPC_URL` - Polygon Amoy RPC endpoint
- `DEPLOYER_PRIVATE_KEY` - Testnet deployer key (from Secret Manager)
- `PRICE_ORACLE_SERVICE_URL` - Price Oracle service URL (optional)
