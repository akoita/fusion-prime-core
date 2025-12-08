# Escrow Event Relayer

Production-grade event relayer for monitoring Fusion Prime escrow contracts and publishing events to Google Cloud Pub/Sub.

## Features

### 🔄 **Checkpoint Persistence**
- Tracks last processed block per contract
- Enables graceful restarts without missing events
- Supports SQLite (local dev) and PostgreSQL (production)

### 🛡️ **Replay Protection**
- Deduplicates events using unique event IDs
- Prevents double-processing of events after restarts
- Stores processed event history for audit trails

### 📊 **Monitoring & Metrics**
- Real-time metrics (events processed, errors, uptime)
- Structured logging with context
- Periodic metrics logging

### 🚀 **Production-Ready**
- Graceful shutdown on SIGTERM/SIGINT
- Exponential backoff on publish failures
- Batch processing with configurable sizes
- Automatic cleanup of old event records

### ⚡ **Performance**
- Batch fetching of events (default: 1000 blocks)
- Async I/O throughout
- Configurable poll intervals
- Gap detection to catch missed blocks

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Production Event Relayer                   │
└─────────────────────────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌─────────────┐      ┌─────────────┐     ┌─────────────┐
│   Web3      │      │  Checkpoint │     │   Pub/Sub   │
│  Provider   │      │    Store    │     │  Publisher  │
│             │      │             │     │             │
│  (Alchemy,  │      │  (SQLite/   │     │  (GCP)      │
│   Infura)   │      │  PostgreSQL)│     │             │
└─────────────┘      └─────────────┘     └─────────────┘
        │                    │                    │
        │                    │                    │
        ▼                    ▼                    ▼
┌─────────────┐      ┌─────────────┐     ┌─────────────┐
│  Contract   │      │  Checkpoint │     │ Settlement  │
│   Events    │      │   Records   │     │   Service   │
└─────────────┘      └─────────────┘     └─────────────┘
```

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CHAIN_ID` | No | `31337` | Blockchain network ID (31337=Anvil, 11155111=Sepolia, 80002=Amoy) |
| `RPC_URL` | No | `http://localhost:8545` | JSON-RPC endpoint URL |
| `CONTRACT_ADDRESS` | **Yes** | - | Escrow contract address to monitor |
| `PUBSUB_PROJECT_ID` | No | `local-project` | GCP project ID for Pub/Sub |
| `PUBSUB_TOPIC_ID` | No | `settlement.events.v1` | Pub/Sub topic to publish to |
| `EVENT_NAMES` | No | `EscrowReleased,EscrowCreated,Approval,EscrowRefunded` | Comma-separated list of events to monitor |
| `START_BLOCK` | No | `0` | Block number to start from (if no checkpoint) |
| `POLL_INTERVAL_SECONDS` | No | `12` | Seconds to wait between polling cycles |
| `BATCH_SIZE` | No | `1000` | Number of blocks to process per batch |
| `CHECKPOINT_INTERVAL_BLOCKS` | No | `100` | Save checkpoint every N blocks |
| `CHECKPOINT_STORE_TYPE` | No | `sqlite` | `sqlite` or `postgresql` |
| `CHECKPOINT_STORE_URL` | No | - | Connection string for checkpoint store |

### Checkpoint Store Configuration

#### SQLite (Local Development)
```bash
export CHECKPOINT_STORE_TYPE=sqlite
export CHECKPOINT_STORE_URL=relayer_checkpoints.db
```

#### PostgreSQL (Production)
```bash
export CHECKPOINT_STORE_TYPE=postgresql
export CHECKPOINT_STORE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
```

---

## Usage

### Local Development with Anvil

1. **Start Anvil (local Ethereum node)**:
```bash
anvil --block-time 1
```

2. **Deploy contract** (copy the deployed address):
```bash
cd contracts
forge script script/DeployMultichain.s.sol:DeployMultichain \
  --rpc-url http://localhost:8545 \
  --broadcast
```

3. **Start Pub/Sub emulator**:
```bash
docker compose up -d pubsub-emulator
./scripts/init-pubsub-emulator.sh
```

4. **Run relayer**:
```bash
cd integrations/relayers/escrow

export CONTRACT_ADDRESS=0x...  # From step 2
export CHAIN_ID=31337
export RPC_URL=http://localhost:8545
export PUBSUB_EMULATOR_HOST=localhost:8085

python main_production.py
```

### Production Deployment

#### 1. Deploy to Sepolia Testnet

```bash
# Set environment
export CHAIN_ID=11155111
export RPC_URL=https://eth-sepolia.g.alchemy.com/v2/YOUR_API_KEY
export CONTRACT_ADDRESS=0x...  # Deployed contract address
export PUBSUB_PROJECT_ID=your-gcp-project
export PUBSUB_TOPIC_ID=settlement.events.v1
export CHECKPOINT_STORE_TYPE=postgresql
export CHECKPOINT_STORE_URL=postgresql+asyncpg://user:pass@cloudsql-proxy:5432/fusion_prime

# Run relayer
python main_production.py
```

#### 2. Deploy as Cloud Run Job

**Create `Dockerfile`**:
```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy relayer code
COPY . .

# Run relayer
CMD ["python", "main_production.py"]
```

**Deploy to Cloud Run**:
```bash
# Build and push image
gcloud builds submit --tag gcr.io/PROJECT_ID/escrow-relayer

# Deploy as Cloud Run Job (for continuous running)
gcloud run jobs create escrow-relayer \
  --image gcr.io/PROJECT_ID/escrow-relayer \
  --region us-central1 \
  --set-env-vars "CHAIN_ID=11155111,RPC_URL=https://...,CONTRACT_ADDRESS=0x...,PUBSUB_PROJECT_ID=PROJECT_ID" \
  --set-cloudsql-instances PROJECT_ID:REGION:INSTANCE \
  --vpc-connector your-vpc-connector \
  --cpu 1 \
  --memory 512Mi \
  --max-retries 5

# Execute job
gcloud run jobs execute escrow-relayer --region us-central1
```

#### 3. Deploy to Kubernetes (GKE)

**Create `k8s/deployment.yaml`**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: escrow-relayer
spec:
  replicas: 1
  selector:
    matchLabels:
      app: escrow-relayer
  template:
    metadata:
      labels:
        app: escrow-relayer
    spec:
      containers:
      - name: relayer
        image: gcr.io/PROJECT_ID/escrow-relayer:latest
        env:
        - name: CHAIN_ID
          value: "11155111"
        - name: RPC_URL
          valueFrom:
            secretKeyRef:
              name: relayer-secrets
              key: rpc-url
        - name: CONTRACT_ADDRESS
          value: "0x..."
        - name: PUBSUB_PROJECT_ID
          value: "your-project"
        - name: CHECKPOINT_STORE_TYPE
          value: "postgresql"
        - name: CHECKPOINT_STORE_URL
          valueFrom:
            secretKeyRef:
              name: relayer-secrets
              key: db-url
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            cpu: "1000m"
            memory: "1Gi"
```

**Deploy**:
```bash
kubectl apply -f k8s/deployment.yaml
```

---

## Monitoring

### Metrics Endpoint

The relayer exposes metrics via the `get_metrics()` method:

```python
{
  "is_running": true,
  "total_events_processed": 1234,
  "total_events_published": 1234,
  "last_processed_block": 5678,
  "last_checkpoint_time": "2025-10-19T01:30:00Z",
  "errors_count": 0,
  "uptime_seconds": 3600,
  "started_at": "2025-10-19T00:30:00Z",
  "chain_id": "11155111",
  "contract_address": "0x..."
}
```

### Logs

Structured logs are emitted for all operations:

```
2025-10-19 01:30:00 [INFO] production_relayer: Starting production event relayer...
2025-10-19 01:30:05 [INFO] production_relayer: Resuming from block 5678 (checkpoint found)
2025-10-19 01:30:05 [INFO] production_relayer: Processing blocks 5678 to 6678
2025-10-19 01:30:10 [INFO] production_relayer: Processed event EscrowReleased at block 5680, tx 0x...
2025-10-19 01:30:10 [INFO] checkpoint_store: Saved checkpoint: 11155111:0x... @ block 6678
2025-10-19 01:31:00 [INFO] __main__: Metrics: processed=10, published=10, last_block=6678, errors=0, uptime=60s
```

### Cloud Monitoring Integration

For production deployments, integrate with Cloud Monitoring:

```python
from google.cloud import monitoring_v3

# Emit custom metrics
client = monitoring_v3.MetricServiceClient()
series = monitoring_v3.TimeSeries()
series.metric.type = "custom.googleapis.com/escrow_relayer/events_processed"
series.resource.type = "generic_task"
series.resource.labels["project_id"] = project_id
series.resource.labels["location"] = "us-central1"
series.resource.labels["namespace"] = "fusion-prime"
series.resource.labels["job"] = "escrow-relayer"
# ... add data points
client.create_time_series(name=project_name, time_series=[series])
```

---

## Testing

### Unit Tests

Run checkpoint store tests:
```bash
pytest test_checkpoint_store.py -v
```

### Integration Tests

Test with local Anvil:
```bash
# Terminal 1: Start Anvil
anvil --block-time 1

# Terminal 2: Deploy contract and emit events
cd contracts
forge script script/DeployMultichain.s.sol --rpc-url http://localhost:8545 --broadcast

# Terminal 3: Start relayer
cd integrations/relayers/escrow
python main_production.py

# Terminal 4: Trigger escrow events
cast send $CONTRACT_ADDRESS "approve()" --rpc-url http://localhost:8545 --private-key 0xac0974...
```

---

## Troubleshooting

### Issue: Relayer not processing events

**Check**:
1. RPC connection: `curl $RPC_URL -X POST -H "Content-Type: application/json" --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'`
2. Contract address is correct
3. Events exist in the contract ABI
4. Checkpoint not stuck (check database)

### Issue: Duplicate events

**Check**:
1. Checkpoint store is writable
2. Event IDs are being generated correctly
3. Database constraints are in place

### Issue: High memory usage

**Solution**:
- Reduce `BATCH_SIZE` to process fewer blocks per iteration
- Enable event cleanup more frequently
- Use PostgreSQL instead of SQLite for large-scale operations

### Issue: Lagging behind chain

**Solution**:
- Increase `BATCH_SIZE` to process more blocks per iteration
- Reduce `POLL_INTERVAL_SECONDS` for faster polling
- Use a faster RPC provider (premium tier)
- Scale horizontally with multiple relayers per contract/chain

---

## Security Considerations

1. **RPC API Keys**: Store in secrets manager, not environment variables
2. **Database Credentials**: Use Cloud SQL Auth Proxy or IAM authentication
3. **Pub/Sub Authentication**: Use Workload Identity in GKE
4. **Network Security**: Use VPC connectors for private services
5. **Resource Limits**: Set memory/CPU limits to prevent DoS

---

## Performance Tuning

### Batch Size

- **Small (100-500)**: Lower memory, higher latency, more API calls
- **Medium (1000-2000)**: Balanced for most use cases
- **Large (5000+)**: Higher memory, lower latency, fewer API calls

### Poll Interval

- **Fast (1-5s)**: Near real-time, higher API usage
- **Medium (10-15s)**: Good balance
- **Slow (30-60s)**: Lower costs, acceptable for non-critical events

### Checkpoint Interval

- **Frequent (every 10-50 blocks)**: Lower replay window on restarts
- **Moderate (every 100-200 blocks)**: Balanced
- **Infrequent (every 500+ blocks)**: Lower DB writes, larger replay window

---

## License

MIT License - See root LICENSE file

