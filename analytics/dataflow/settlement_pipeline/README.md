# Settlement Events Dataflow Pipeline

Apache Beam pipeline for processing settlement events from Pub/Sub and loading into BigQuery for analytics.

## Features

- ✅ **Real-time Processing**: Streams events from Pub/Sub
- ✅ **Enrichment**: Adds calculated fields and metadata
- ✅ **Windowing**: Fixed windows for batch processing
- ✅ **Dead Letter Queue**: Failed records sent to separate table
- ✅ **Metrics**: Computed metrics for monitoring
- ✅ **Auto-scaling**: Throughput-based worker scaling
- ✅ **Error Handling**: Robust error handling with retries

## Architecture

```
Pub/Sub → Parse → Enrich → Transform → BigQuery
   │         │        │         │           │
   └─────────┴────────┴─────────┴──→ Dead Letter Queue
```

## Local Development

### Setup

```bash
cd analytics/dataflow/settlement-pipeline

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Run Locally (DirectRunner)

```bash
python main.py \
  --project your-project-id \
  --input_subscription projects/your-project-id/subscriptions/settlement-events-consumer \
  --output_table your-project-id:fusion_prime_risk.settlement_transactions \
  --dead_letter_table your-project-id:fusion_prime_risk.dead_letter \
  --runner DirectRunner \
  --window_size 60
```

### Test with Local Pub/Sub Emulator

```bash
# Terminal 1: Start emulator
export PUBSUB_EMULATOR_HOST=localhost:8085
docker compose up -d pubsub-emulator

# Terminal 2: Run pipeline
python main.py \
  --project local-project \
  --input_subscription projects/local-project/subscriptions/settlement-events-consumer \
  --output_table local-project:fusion_prime_risk.settlement_transactions \
  --runner DirectRunner
```

## Production Deployment

### Deploy to Dataflow

```bash
# Set variables
export PROJECT_ID=your-project-id
export REGION=us-central1
export TEMP_LOCATION=gs://your-bucket/temp
export STAGING_LOCATION=gs://your-bucket/staging
export SUBSCRIPTION=projects/${PROJECT_ID}/subscriptions/settlement-events-consumer
export OUTPUT_TABLE=${PROJECT_ID}:fusion_prime_risk.settlement_transactions
export DEAD_LETTER_TABLE=${PROJECT_ID}:fusion_prime_risk.dead_letter

# Deploy pipeline
python main.py \
  --project ${PROJECT_ID} \
  --region ${REGION} \
  --input_subscription ${SUBSCRIPTION} \
  --output_table ${OUTPUT_TABLE} \
  --dead_letter_table ${DEAD_LETTER_TABLE} \
  --runner DataflowRunner \
  --temp_location ${TEMP_LOCATION} \
  --staging_location ${STAGING_LOCATION} \
  --window_size 60 \
  --max_num_workers 10 \
  --autoscaling_algorithm THROUGHPUT_BASED \
  --service_account_email dataflow-worker@${PROJECT_ID}.iam.gserviceaccount.com
```

### Deploy with Terraform

Create `infra/terraform/dataflow/main.tf`:

```hcl
resource "google_dataflow_job" "settlement_pipeline" {
  name              = "settlement-events-pipeline"
  template_gcs_path = "gs://your-bucket/templates/settlement-pipeline"
  temp_gcs_location = "gs://your-bucket/temp"
  region            = var.region

  parameters = {
    input_subscription  = "projects/${var.project_id}/subscriptions/settlement-events-consumer"
    output_table        = "${var.project_id}:fusion_prime_risk.settlement_transactions"
    dead_letter_table   = "${var.project_id}:fusion_prime_risk.dead_letter"
    window_size         = "60"
  }

  on_delete = "cancel"
}
```

## Pipeline Configuration

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--project` | Yes | - | GCP project ID |
| `--region` | No | `us-central1` | GCP region |
| `--input_subscription` | Yes | - | Pub/Sub subscription path |
| `--output_table` | Yes | - | BigQuery output table |
| `--dead_letter_table` | No | - | BigQuery dead letter table |
| `--window_size` | No | `60` | Window size in seconds |
| `--runner` | No | `DirectRunner` | `DirectRunner` or `DataflowRunner` |
| `--temp_location` | No | - | GCS temp location |
| `--staging_location` | No | - | GCS staging location |

### Input Format

Expected Pub/Sub message format:

```json
{
  "timestamp": "2025-10-19T01:00:00Z",
  "command_id": "cmd-123",
  "chain_id": "11155111",
  "payer": "0x1234...",
  "payee": "0x5678...",
  "amount": "1000000000000000000",
  "asset_address": "0xabcd...",
  "status": "confirmed",
  "transaction_hash": "0xtxhash...",
  "block_number": 12345,
  "settlement_type": "escrow_release"
}
```

Or smart contract event format:

```json
{
  "timestamp": "2025-10-19T01:00:00Z",
  "chain_id": "11155111",
  "contract_address": "0x1234...",
  "event_name": "EscrowReleased",
  "transaction_hash": "0xtxhash...",
  "block_number": 12345,
  "args": {
    "payer": "0x1234...",
    "payee": "0x5678...",
    "amount": "1000000000000000000"
  }
}
```

## Monitoring

### Dataflow Metrics

View metrics in Google Cloud Console:
- **Throughput**: Elements/second
- **Latency**: P50, P95, P99
- **Worker Utilization**: CPU, memory
- **Auto-scaling**: Current workers

### BigQuery Metrics

Query dead letter table:

```sql
SELECT
  error,
  COUNT(*) as count,
  MIN(timestamp) as first_error,
  MAX(timestamp) as last_error
FROM `PROJECT.fusion_prime_risk.dead_letter`
WHERE DATE(timestamp) = CURRENT_DATE()
GROUP BY error
ORDER BY count DESC
```

### Cloud Monitoring Alerts

Create alerts for:
- High error rate in dead letter queue
- Pipeline lag > 5 minutes
- Worker failures
- BigQuery insert failures

## Testing

### Unit Tests

```python
import unittest
import apache_beam as beam
from apache_beam.testing.test_pipeline import TestPipeline
from apache_beam.testing.util import assert_that, equal_to

from main import ParsePubSubMessage, EnrichSettlementEvent

class TestSettlementPipeline(unittest.TestCase):

    def test_parse_message(self):
        with TestPipeline() as p:
            input_data = [
                b'{"command_id": "cmd-1", "amount": "100"}'
            ]

            result = (
                p
                | beam.Create(input_data)
                | beam.ParDo(ParsePubSubMessage())
            )

            assert_that(result, lambda x: len(list(x)) == 1)
```

### Integration Tests

```bash
# Run with test Pub/Sub topic
python main.py \
  --project test-project \
  --input_subscription projects/test-project/subscriptions/test-sub \
  --output_table test-project:test_dataset.test_table \
  --runner DirectRunner
```

## Performance Tuning

### Throughput Optimization

- **Increase workers**: `--max_num_workers 20`
- **Larger machines**: `--machine_type n1-standard-4`
- **Disk size**: `--disk_size_gb 100`

### Latency Optimization

- **Smaller windows**: `--window_size 10`
- **More workers**: `--max_num_workers 15`
- **Streaming engine**: `--enable_streaming_engine`

### Cost Optimization

- **Fewer workers**: `--max_num_workers 5`
- **Smaller machines**: `--machine_type n1-standard-1`
- **Batch processing**: Larger windows
- **Shutdown idle workers**: `--autoscaling_algorithm THROUGHPUT_BASED`

## Troubleshooting

### Pipeline Not Starting

**Check**:
1. Service account has required permissions
2. Pub/Sub subscription exists
3. BigQuery dataset exists
4. GCS temp/staging locations are accessible

### High Latency

**Solutions**:
1. Increase worker count
2. Use streaming engine
3. Optimize transforms (reduce complexity)
4. Check BigQuery insert rate limits

### High Error Rate

**Solutions**:
1. Check dead letter queue for error patterns
2. Validate input message format
3. Add more error handling in transforms
4. Increase retry attempts

## Cost Estimation

### Development (DirectRunner)

- **Cost**: $0 (runs locally)
- **Workers**: 1 (local)

### Production (DataflowRunner)

| Configuration | Workers | Machine Type | Cost/Hour | Cost/Day |
|---------------|---------|--------------|-----------|----------|
| Small | 1-3 | n1-standard-1 | ~$0.15 | ~$3.60 |
| Medium | 1-5 | n1-standard-2 | ~$0.50 | ~$12.00 |
| Large | 1-10 | n1-standard-4 | ~$1.50 | ~$36.00 |

*Estimates include compute, network egress, and Pub/Sub costs*

## License

MIT License - See root LICENSE file

