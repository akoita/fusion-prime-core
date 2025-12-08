# Price Oracle Service

Real-time and historical crypto price data service with automatic Pub/Sub broadcasting for the Fusion Prime platform.

## Overview

The Price Oracle Service provides:
- **Real-time prices** from Chainlink, Pyth, and Coingecko
- **Automatic fallback** across multiple providers
- **Historical price data** for VaR calculations
- **Pub/Sub broadcasting** to `market.prices.v1` topic
- **Circuit breaker protection** for resilience
- **In-memory caching** for performance

## Architecture

```
┌──────────────┐     ┌────────────────┐     ┌─────────────┐
│   Chainlink  │────▶│  Price Oracle  │────▶│  Pub/Sub    │
│   (Primary)  │     │    Service     │     │   Topic     │
└──────────────┘     │                │     └─────────────┘
                     │                │           │
┌──────────────┐     │  - Fetch       │           ▼
│     Pyth     │────▶│  - Cache       │     ┌─────────────┐
│  (Fallback)  │     │  - Publish     │     │ Risk Engine │
└──────────────┘     │                │     │ Settlement  │
                     │                │     │  Service    │
┌──────────────┐     │                │     └─────────────┘
│  Coingecko   │────▶│                │
│(Hist+ Backup)│     └────────────────┘
└──────────────┘
```

## Supported Assets

- **ETH** (Ethereum)
- **BTC** (Bitcoin)
- **USDC** (USD Coin)
- **USDT** (Tether)

## API Endpoints

### Get Single Price

```http
GET /api/v1/prices/{asset_symbol}?force_refresh=false
```

**Example**:
```bash
curl https://price-oracle-service-xxxxx.run.app/api/v1/prices/ETH
```

**Response**:
```json
{
  "asset_symbol": "ETH",
  "price_usd": "2450.75",
  "source": "chainlink",
  "timestamp": "2025-10-27T10:30:00Z",
  "from_cache": false
}
```

### Get Multiple Prices

```http
GET /api/v1/prices?symbols=ETH&symbols=BTC&symbols=USDC
```

**Example**:
```bash
curl "https://price-oracle-service-xxxxx.run.app/api/v1/prices?symbols=ETH&symbols=BTC&symbols=USDC"
```

**Response**:
```json
{
  "prices": {
    "ETH": {
      "asset_symbol": "ETH",
      "price_usd": "2450.75",
      "source": "chainlink",
      "timestamp": "2025-10-27T10:30:00Z",
      "from_cache": false
    },
    "BTC": {
      "asset_symbol": "BTC",
      "price_usd": "68350.25",
      "source": "chainlink",
      "timestamp": "2025-10-27T10:30:00Z",
      "from_cache": false
    }
  },
  "timestamp": "2025-10-27T10:30:00Z",
  "count": 2
}
```

### Get Historical Prices

```http
GET /api/v1/prices/{asset_symbol}/historical?days=30
```

**Example**:
```bash
curl "https://price-oracle-service-xxxxx.run.app/api/v1/prices/ETH/historical?days=30"
```

**Response**:
```json
{
  "asset_symbol": "ETH",
  "prices": [
    {
      "timestamp": "2025-09-27T00:00:00Z",
      "price_usd": "2380.50"
    },
    {
      "timestamp": "2025-09-28T00:00:00Z",
      "price_usd": "2420.75"
    }
  ],
  "days": 30,
  "count": 30,
  "source": "coingecko"
}
```

### Health Check

```http
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-27T10:30:00Z",
  "version": "1.0.0",
  "components": {
    "price_oracle": "healthy",
    "pubsub_publisher": "healthy",
    "cache": "healthy (size: 4)"
  }
}
```

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `GCP_PROJECT` | GCP project ID | `fusion-prime` | Yes |
| `ETH_RPC_URL` | Ethereum RPC endpoint | - | Yes |
| `COINGECKO_API_KEY` | Coingecko API key (optional) | - | No |
| `PRICE_CACHE_TTL` | Cache TTL in seconds | `60` | No |
| `PRICE_UPDATE_INTERVAL` | Pub/Sub publish interval | `30` | No |
| `PUBSUB_TOPIC` | Pub/Sub topic name | `market.prices.v1` | No |
| `PORT` | Service port | `8080` | No |

## Local Development

### Prerequisites

- Python 3.11+
- GCP credentials configured
- Pub/Sub topic created

### Setup

```bash
cd services/price-oracle

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GCP_PROJECT=fusion-prime
export ETH_RPC_URL=https://sepolia.gateway.tenderly.co/YOUR_API_KEY
export COINGECKO_API_KEY=your_coingecko_key  # Optional

# Run the service
python -m app.main
```

### Testing

```bash
# Run tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test
pytest tests/test_price_oracle_client.py -v
```

## Deployment to Cloud Run

### Manual Deployment

```bash
gcloud run deploy price-oracle-service \
  --source=. \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --set-env-vars="GCP_PROJECT=fusion-prime,ETH_RPC_URL=https://sepolia.gateway.tenderly.co/YOUR_KEY,PRICE_UPDATE_INTERVAL=30"
```

### Using Deployment Script

```bash
# From project root
./scripts/deploy-unified.sh --env dev --services price-oracle
```

## Pub/Sub Integration

### Creating the Topic

```bash
gcloud pubsub topics create market.prices.v1 --project=fusion-prime
```

### Message Format

Published messages follow this schema:

```json
{
  "asset_symbol": "ETH",
  "price_usd": "2450.75",
  "source": "chainlink",
  "timestamp": "2025-10-27T10:30:00Z",
  "metadata": {}
}
```

### Subscribing to Price Updates

```python
from google.cloud import pubsub_v1

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(
    "fusion-prime",
    "your-subscription-name"
)

def callback(message):
    price_data = json.loads(message.data)
    print(f"Received price: {price_data['asset_symbol']} = ${price_data['price_usd']}")
    message.ack()

subscriber.subscribe(subscription_path, callback=callback)
```

## Monitoring

### Key Metrics

- **Price fetch latency**: Time to fetch from providers
- **Cache hit rate**: Percentage of requests served from cache
- **Pub/Sub publish success rate**: Percentage of successful publishes
- **Provider failures**: Count of failures per provider

### Logs

View logs in Cloud Logging:

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=price-oracle-service" --limit 50 --format json
```

### Alerts

Set up alerts for:
- Service health check failures
- High error rates (>5%)
- Price fetch failures
- Pub/Sub publish failures

## Architecture Decisions

### Provider Selection

1. **Chainlink** (Primary)
   - On-chain price feeds
   - High reliability
   - Testnet support

2. **Pyth** (Fallback)
   - Real-time oracle network
   - Low latency
   - Confidence intervals

3. **Coingecko** (Backup + Historical)
   - HTTP API
   - Historical data
   - No blockchain dependency

### Caching Strategy

- **TTL**: 60 seconds (configurable)
- **In-memory**: Fast access, no external dependencies
- **Per-asset**: Independent expiration
- **Force refresh**: API parameter to bypass cache

### Circuit Breaker

- **Failure threshold**: 5 consecutive failures
- **Recovery timeout**: 60 seconds
- **Per-provider**: Independent circuit breakers
- **Automatic fallback**: Seamless provider switching

## Troubleshooting

### Price Fetch Failures

**Symptom**: All providers failing

**Solution**:
1. Check RPC_URL is accessible
2. Verify Chainlink feed addresses are correct
3. Check rate limits on Coingecko API
4. Review circuit breaker states

```bash
# Test RPC connectivity
curl -X POST $ETH_RPC_URL \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

### Pub/Sub Publish Failures

**Symptom**: Prices fetched but not published

**Solution**:
1. Verify topic exists: `gcloud pubsub topics list`
2. Check service account permissions
3. Review Pub/Sub quotas

```bash
# Test topic accessibility
gcloud pubsub topics publish market.prices.v1 --message='{"test":true}'
```

### High Latency

**Symptom**: Slow API responses

**Solution**:
1. Check cache hit rate
2. Verify RPC endpoint latency
3. Consider increasing cache TTL
4. Review provider timeouts

## Performance

### Benchmarks

- **Cache hit**: ~1-5ms
- **Chainlink fetch**: ~50-200ms
- **Coingecko fetch**: ~100-300ms
- **Pub/Sub publish**: ~10-50ms

### Optimization Tips

- Increase `PRICE_CACHE_TTL` for less frequent updates
- Use multiple RPC endpoints for redundancy
- Consider Redis for distributed caching
- Batch price fetches when possible

## Security

### API Keys

Store sensitive keys in Secret Manager:

```bash
# Store Coingecko API key
echo -n "your-api-key" | gcloud secrets create coingecko-api-key --data-file=-

# Grant service account access
gcloud secrets add-iam-policy-binding coingecko-api-key \
  --member="serviceAccount:YOUR_SA@fusion-prime.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### IAM Permissions

Required permissions for the service:
- `pubsub.topics.publish`
- `secretmanager.versions.access` (if using Secret Manager)

## Future Enhancements

- [ ] Redis caching for horizontal scaling
- [ ] More price feed providers (Band Protocol, API3)
- [ ] Price deviation alerts
- [ ] Historical data caching in BigQuery
- [ ] GraphQL API
- [ ] WebSocket streaming for real-time updates
- [ ] Multi-currency support (EUR, GBP, JPY)

## Support

For issues or questions:
- Check logs: `gcloud logging read --limit 50`
- Review health endpoint: `curl https://SERVICE_URL/health`
- Contact: DevOps & SecOps Agent

## Related Documentation

- [Sprint 03 Plan](../../docs/sprints/sprint-03.md)
- [Risk Engine Integration](../../docs/architecture/risk-computation.md)
- [Deployment Guide](../../docs/operations/DEPLOYMENT.md)
