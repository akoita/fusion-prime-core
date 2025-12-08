# Escrow Indexer Service

Indexes escrow events from blockchain and provides fast REST API for querying escrow data.

## Architecture

```
Blockchain (Sepolia)
    ↓
Event Relayer Service
    ↓
Pub/Sub Topic: settlement.events.v1
    ↓
Escrow Indexer (this service)
    ↓
PostgreSQL Database
    ↓
REST API
    ↓
Frontend / Clients
```

## Features

- **Event Processing**: Subscribes to Pub/Sub and processes blockchain events in real-time
- **Database Indexing**: Stores escrow data in PostgreSQL for fast queries
- **REST API**: Provides endpoints for querying escrows by role (payer/payee/arbiter)
- **Status Tracking**: Tracks escrow status (created → approved → released/refunded)
- **Audit Trail**: Maintains complete event history for each escrow

## Database Schema

### Escrows Table
- `escrow_address` (PK)
- `payer_address`, `payee_address`, `arbiter_address` (indexed)
- `amount`, `release_delay`, `approvals_required`
- `status` (created/approved/released/refunded)
- `chain_id`, `created_block`, `created_tx`
- Timestamps

### Approvals Table
- Tracks individual approvals for each escrow
- Links to escrow via foreign key

### Events Table
- Complete audit trail of all escrow events
- Stores: EscrowDeployed, Approved, EscrowReleased, EscrowRefunded

## API Endpoints

### Query by Role
- `GET /api/v1/escrows/by-payer/{address}` - Get escrows where user is payer
- `GET /api/v1/escrows/by-payee/{address}` - Get escrows where user is payee
- `GET /api/v1/escrows/by-arbiter/{address}` - Get escrows where user is arbiter
- `GET /api/v1/escrows/by-role/{address}` - Get all escrows grouped by role

### Escrow Details
- `GET /api/v1/escrows/{escrowAddress}` - Get specific escrow details
- `GET /api/v1/escrows/{escrowAddress}/approvals` - Get approval history
- `GET /api/v1/escrows/{escrowAddress}/events` - Get event history (audit trail)

### System
- `GET /` - Health check
- `GET /health` - Detailed health check
- `GET /api/v1/escrows/stats` - Overall statistics

### Query Parameters
All role-based endpoints support:
- `status` - Filter by status (created, approved, released, refunded)

## Events Processed

### From EscrowFactory
- **EscrowDeployed**: Creates new escrow record

### From Escrow Contracts
- **EscrowCreated**: Updates escrow details
- **Approved**: Adds approval, checks if fully approved
- **EscrowReleased**: Marks escrow as released
- **EscrowRefunded**: Marks escrow as refunded

## Setup

### Prerequisites
- Python 3.11+
- PostgreSQL database
- GCP Pub/Sub subscription to `settlement.events.v1`

### Local Development

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Set environment variables**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Initialize database**:
```bash
python -m app.main
```

4. **Run service**:
```bash
python app/main.py
```

### Docker

```bash
docker build -t escrow-indexer .
docker run -p 8080:8080 --env-file .env escrow-indexer
```

## Deployment to Cloud Run

### Prerequisites
1. Create PostgreSQL database (Cloud SQL or managed PostgreSQL)
2. Create Pub/Sub subscription:
```bash
gcloud pubsub subscriptions create escrow-indexer-sub \
  --topic=settlement.events.v1 \
  --ack-deadline=60
```

3. Store database URL as secret:
```bash
echo -n "postgresql://user:pass@host:5432/escrow_indexer" | \
  gcloud secrets create escrow-indexer-db-url --data-file=-
```

### Deploy

```bash
gcloud builds submit --config cloudbuild.yaml
```

Or manually:

```bash
# Build
docker build -t gcr.io/fusion-prime/escrow-indexer .
docker push gcr.io/fusion-prime/escrow-indexer

# Deploy
gcloud run deploy escrow-indexer \
  --image gcr.io/fusion-prime/escrow-indexer \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars PUBSUB_PROJECT_ID=fusion-prime,PUBSUB_SUBSCRIPTION_ID=escrow-indexer-sub \
  --set-secrets DATABASE_URL=escrow-indexer-db-url:latest \
  --memory 512Mi \
  --cpu 1 \
  --max-instances 10 \
  --timeout 3600
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `PUBSUB_PROJECT_ID` | GCP project ID | `fusion-prime` |
| `PUBSUB_SUBSCRIPTION_ID` | Pub/Sub subscription | `escrow-indexer-sub` |
| `PORT` | HTTP server port | `8080` |

## Monitoring

### Health Checks
- `/health` - Returns database connection status and subscriber stats

### Logging
- All events are logged with structured logging
- Emojis for easy scanning: ✅ success, ❌ error, 📨 message received, etc.

### Metrics
- Messages processed count
- Messages failed count
- Database query performance (via PostgreSQL logs)

## Example API Usage

### Get escrows where user is payee
```bash
curl http://localhost:8080/api/v1/escrows/by-payee/0x6eFc2ecB7A021c2249Ae2Cf253a7F9fA37Ad71bA
```

Response:
```json
{
  "success": true,
  "count": 3,
  "escrows": [
    {
      "escrow_address": "0x08ce4bb5f68277aac2c217943d606f9e326616c3",
      "payer_address": "0xe6be859007336c4f108ee3b0ee6ae0d7927cabe2",
      "payee_address": "0x6efc2ecb7a021c2249ae2cf253a7f9fa37ad71ba",
      "arbiter_address": "0x5e85f268274b9e89eceb77a513e45f7ea68d3a5b",
      "amount": "100000000000000000",
      "release_delay": 0,
      "approvals_required": 2,
      "status": "approved",
      "chain_id": 11155111,
      "created_block": 7472123,
      "created_tx": "0x...",
      "created_at": "2025-11-04T20:30:00",
      "updated_at": "2025-11-04T20:35:00"
    }
  ]
}
```

### Get all escrows for a user (by role)
```bash
curl http://localhost:8080/api/v1/escrows/by-role/0x6eFc2ecB7A021c2249Ae2Cf253a7F9fA37Ad71bA
```

Response:
```json
{
  "success": true,
  "address": "0x6efc2ecb7a021c2249ae2cf253a7f9fa37ad71ba",
  "total": 5,
  "escrows": {
    "asPayer": [...],
    "asPayee": [...],
    "asArbiter": [...]
  }
}
```

## Troubleshooting

### Database Connection Issues
- Check `DATABASE_URL` is correctly formatted
- Verify database is accessible from service
- Check Cloud SQL proxy if using Cloud SQL

### Pub/Sub Issues
- Verify subscription exists: `gcloud pubsub subscriptions list`
- Check relayer is publishing events
- Monitor message queue: `gcloud pubsub subscriptions describe escrow-indexer-sub`

### Missing Escrows
- Check relayer is running and processing events
- Verify relayer is publishing to correct topic
- Check subscriber logs for errors
- Manually re-process events if needed

## Development

### Run Tests
```bash
pytest
```

### Database Migrations
Currently using SQLAlchemy's `create_all()`. For production, consider:
- Alembic for migrations
- Backup before schema changes

## License

Apache 2.0
