# Risk Analytics Dataflow Pipeline

Apache Beam pipeline for real-time risk computation from settlement events, on-chain positions, and market data.

## Overview

This pipeline processes multiple event streams to compute portfolio-level and asset-level risk metrics, which are then written to BigQuery for dashboard visualization and alerting.

## Pipeline Architecture

```
Pub/Sub (settlement.events.v1)
    ↓
[Parse Settlement Events]
    ↓
[Join with Market Prices]
    ↓
[Compute Portfolio Metrics] ← (1min, 5min, 1hr windows)
    ↓
[Write to BigQuery (risk.portfolio_exposures)]

Pub/Sub (chain.events.v1)
    ↓
[Parse Chain Events]
    ↓
[Aggregate by Account + Asset]
    ↓
[Write to BigQuery (risk.asset_exposures)]

Pub/Sub (market.prices.v1)
    ↓
[Cache Latest Prices]
    ↓
(Side input for portfolio computation)
```

## Pipeline Components

### 1. Settlement Event Parser
- Reads from `settlement.events.v1` Pub/Sub topic
- Deserializes Protobuf `SettlementEvent` messages
- Filters out non-confirmed events
- Emits structured event data

### 2. Chain Event Parser
- Reads from `chain.events.v1` Pub/Sub topic
- Parses `EscrowReleased`, `CollateralDeposited`, `CollateralWithdrawn` events
- Extracts account, asset, chain, and amount information
- Normalizes across different chain event formats

### 3. Market Price Cache
- Reads from `market.prices.v1` Pub/Sub topic
- Maintains a sliding window cache of latest prices by asset
- Provides side input for risk computation

### 4. Portfolio Risk Computation
- Windows: 1-minute tumbling for real-time, 1-hour for analytics
- Joins settlement events with market prices
- Computes:
  - Total collateral USD
  - Total borrow USD
  - Available credit USD
  - Margin health score
  - VaR (Historical Simulation method)
  - Expected Shortfall
  - Liquidation prices
- Outputs to `risk.portfolio_exposures` BigQuery table

### 5. Asset Position Aggregation
- Groups chain events by (account, asset, chain)
- Computes balance and USD value
- Calculates utilization percentage
- Outputs to `risk.asset_exposures` BigQuery table

### 6. Margin Event Detector
- Monitors margin health score thresholds
- Triggers margin call events when score < 30
- Triggers liquidation events when score < 15
- Outputs to `risk.margin_events` BigQuery table
- Publishes alerts to `alerts.margin.v1` Pub/Sub topic

## Running the Pipeline

### Local Development (Direct Runner)

```bash
# Set up Python environment
cd analytics/dataflow/risk-pipeline
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run pipeline locally
python main.py \
  --runner DirectRunner \
  --project fusion-prime-dev \
  --input_subscription projects/fusion-prime-dev/subscriptions/settlement-events \
  --output_table fusion-prime-dev:risk.portfolio_exposures \
  --temp_location gs://fusion-prime-dev-dataflow-temp/temp
```

### Production (Dataflow Runner)

```bash
python main.py \
  --runner DataflowRunner \
  --project fusion-prime-prod \
  --region us-central1 \
  --staging_location gs://fusion-prime-prod-dataflow/staging \
  --temp_location gs://fusion-prime-prod-dataflow/temp \
  --input_subscription projects/fusion-prime-prod/subscriptions/settlement-events \
  --output_table fusion-prime-prod:risk.portfolio_exposures \
  --max_num_workers 10 \
  --autoscaling_algorithm THROUGHPUT_BASED \
  --service_account_email dataflow-pipeline@fusion-prime-prod.iam.gserviceaccount.com
```

### Using Terraform

```bash
cd infra/terraform/dataflow
terraform init
terraform apply -var="environment=prod"
```

## Configuration

### Pipeline Options

| Option | Description | Default |
|--------|-------------|---------|
| `--runner` | Pipeline runner (DirectRunner, DataflowRunner) | `DirectRunner` |
| `--project` | GCP project ID | `fusion-prime-dev` |
| `--region` | GCP region for Dataflow workers | `us-central1` |
| `--input_subscription` | Pub/Sub subscription for settlement events | Required |
| `--chain_events_subscription` | Pub/Sub subscription for chain events | Required |
| `--market_prices_subscription` | Pub/Sub subscription for market prices | Required |
| `--output_table` | BigQuery table for portfolio exposures | Required |
| `--asset_exposures_table` | BigQuery table for asset exposures | Required |
| `--margin_events_table` | BigQuery table for margin events | Required |
| `--window_duration` | Window duration for aggregation (seconds) | `60` |
| `--margin_call_threshold` | Margin health score threshold for margin calls | `30.0` |
| `--liquidation_threshold` | Margin health score threshold for liquidations | `15.0` |

### Environment Variables

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
export GCP_PROJECT=fusion-prime-prod
export DATAFLOW_REGION=us-central1
```

## Testing

### Unit Tests

```bash
pytest tests/unit/
```

### Integration Tests (with Pub/Sub Emulator)

```bash
# Start Pub/Sub emulator
gcloud beta emulators pubsub start --project=test-project

# In another terminal
export PUBSUB_EMULATOR_HOST=localhost:8085
pytest tests/local/
```

### End-to-End Tests (Staging Environment)

```bash
pytest tests/e2e/ --env=staging
```

## Monitoring

### Dataflow Metrics
- **System Lag**: Time between event publication and processing (target: <10s p99)
- **Data Freshness**: Age of most recent output in BigQuery (target: <30s)
- **Throughput**: Events processed per second (target: >500)
- **Error Rate**: Failed elements per second (target: <0.1%)

### Alerts
- Pipeline stalled (no output for 5 minutes)
- Error rate exceeds 1%
- System lag exceeds 30 seconds
- Worker autoscaling failures

### Dashboards
- **Dataflow Job Monitoring**: Worker CPU, memory, throughput, lag
- **BigQuery Write Performance**: Rows written per second, write latency
- **Business Metrics**: Margin calls triggered, liquidations executed

## VaR Computation Details

### Historical Simulation Method

1. **Price History**: Maintain 90-day price history for all assets
2. **Return Calculation**: Compute daily log returns for each asset
3. **Portfolio Revaluation**: Apply historical returns to current positions
4. **VaR Calculation**: 99th percentile of loss distribution
5. **ES Calculation**: Expected loss beyond VaR threshold

### Configuration

```python
VAR_CONFIDENCE_LEVEL = 0.99
VAR_HORIZON_DAYS = 1
PRICE_HISTORY_DAYS = 90
```

## Scaling Considerations

### Autoscaling
- **Min Workers**: 2
- **Max Workers**: 20
- **Algorithm**: THROUGHPUT_BASED
- **Target Throughput**: 500 events/sec per worker

### Performance Tuning
- **Batch Size**: 100 events per bundle
- **Window Duration**: 1 minute for real-time, 1 hour for analytics
- **Side Input Refresh**: Market prices refreshed every 10 seconds
- **BigQuery Streaming Inserts**: Batched writes every 5 seconds

## Cost Optimization

### Estimated Monthly Cost (Production)

| Component | Usage | Cost |
|-----------|-------|------|
| Dataflow (20 workers, 24/7) | 14,400 worker-hours | ~$1,500 |
| BigQuery Storage (1TB) | 1TB | ~$20 |
| BigQuery Streaming Inserts (10M/day) | 300M/month | ~$150 |
| Pub/Sub (100M messages/day) | 3B/month | ~$120 |
| **Total** | | **~$1,790/month** |

### Cost Reduction Strategies
- Use Flex templates for batch jobs
- Enable Dataflow Shuffle Service
- Optimize window durations to reduce processing
- Use Cloud Storage for cold data (>90 days)

## Troubleshooting

### Common Issues

**Issue**: Pipeline lag increasing
- **Cause**: Insufficient workers or processing bottleneck
- **Solution**: Increase `max_num_workers` or optimize transforms

**Issue**: BigQuery write failures
- **Cause**: Schema mismatch or quota exceeded
- **Solution**: Verify schema compatibility, request quota increase

**Issue**: Missing market prices
- **Cause**: Price oracle downtime or subscription misconfiguration
- **Solution**: Check Pub/Sub subscription, verify oracle service

## References

- [Apache Beam Python SDK](https://beam.apache.org/documentation/sdks/python/)
- [Dataflow Best Practices](https://cloud.google.com/dataflow/docs/guides/best-practices)
- [BigQuery Streaming Inserts](https://cloud.google.com/bigquery/streaming-data-into-bigquery)
- [Risk Analytics Pipeline Architecture](../../../docs/architecture/risk-analytics-pipeline.md)

