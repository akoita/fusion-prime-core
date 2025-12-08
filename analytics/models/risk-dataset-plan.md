# Risk Dataset Materialization Plan

## Goals
- Provide timely visibility into settlement status, exposure, and counterparty risk.
- Support dashboards and automated alerts for treasury/risk teams.

## Datasets & Tables
- `bq_dataset_risk.settlement_status_v1`
  - Columns: `command_id`, `workflow_id`, `payer`, `payee`, `asset_symbol`, `amount_numeric`, `status`, `last_updated`, `chain_id`.
  - Partition by `DATE(last_updated)`; cluster by `workflow_id`, `payer`.
- `bq_dataset_risk.exposure_snapshot_v1`
  - Aggregated exposures per counterparty and asset; derived from settlement status + on-chain balances.

## Data Sources
- Pub/Sub `settlement.events.v1` (protobuf) → Dataflow job to BigQuery.
- Cloud SQL command table for reference data (joined via Dataflow or scheduled Cloud Functions).
- On-chain snapshots via relayer service storing to GCS/BigQuery.

## Materialization Strategy
- Start with scheduled batch Dataflow pipeline (hourly) ingesting Pub/Sub events into `settlement_status_v1`.
- Maintain materialized view for `open_settlements` (status <> CONFIRMED) to power dashboards.
- Use BigQuery scheduled queries to derive exposure metrics once per hour.

## Observability
- BigQuery job metrics exported to Cloud Monitoring; alert on failures/backlog.
- Data freshness checks using Dataform/DBT-like assertions (future work).

## Next Steps
1. Create Terraform resources for `bq_dataset_risk` and tables.
2. Scaffold Dataflow pipeline code (Python) to parse protobuf and write to BigQuery.
3. Define Looker Studio/Grafana dashboards referencing `settlement_status_v1`.
4. Coordinate with DevOps for IAM roles (Dataflow service account, BigQuery writer).
