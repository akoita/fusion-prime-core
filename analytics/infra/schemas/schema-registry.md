# Fusion Prime Schema Registry

## Purpose
Define governance for analytical schemas, Pub/Sub topics, and BigQuery datasets supporting cross-chain settlement, risk, and compliance workloads.

## Message Schemas (Pub/Sub)
- **Format**: Protocol Buffers (proto3).
- **Versioning**: Semantic versioning `vMajor.Minor` encoded in package name (e.g., `fusionprime.settlement.v1`). Breaking changes require new major version/topic.
- **Storage**: Check proto files into `analytics/schemas/pubsub/`. Register compiled descriptors with Cloud Pub/Sub Schema Registry using CI automation.
- **Validation**: Producers publish only schema-validated messages; consumers use generated code. Unknown fields preserved for forward compatibility.

### Core Topics
- `settlement.commands.v1` – Initiate DvP or collateral transfers. Key fields: `command_id`, `workflow_id`, `account_ref`, `asset`, `amount`, `deadline`.
- `settlement.events.v1` – Lifecycle events (initiated, confirmed, failed) with metadata for replay.
- `risk.snapshots.v1` – Portfolio valuation results, margin metrics, timestamped per counterparty.
- `compliance.alerts.v1` – AML/KYC triggers, policy decisions with evidence links.
- `telemetry.audit.v1` – Cross-system audit trail entries (user actions, contract invocations).

## BigQuery Datasets
- `bq_dataset_core` – Authoritative settlement and ledger data, normalized per workflow.
- `bq_dataset_risk` – Materialized views for exposure, VaR, stress results.
- `bq_dataset_compliance` – Case management, alerting history, regulatory reports.
- `bq_dataset_observability` – Aggregated metrics/log events for analytics.

### Naming Conventions
- Tables: `purpose_entity_variant_v{major}` (e.g., `settlement_workflows_base_v1`).
- Columns: snake_case. Timestamps stored as `TIMESTAMP` in UTC; numeric high-precision values stored as `NUMERIC` or `BIGNUMERIC`.
- Partition on ingestion time or business date; cluster by identifiers (`counterparty_id`, `workflow_id`).

## Data Governance
- Owners defined per dataset (Risk, Compliance, Treasury) with IAM roles managed via Terraform.
- Schema changes require ADR (architecture decision record) and backward compatibility review.
- Apply row-level security and column-level encryption for sensitive attributes; integrate with Cloud DLP for scans.

## Tooling Roadmap
- Automate proto compilation and schema registration via Cloud Build job.
- Maintain schema docs with buf/buildifier or similar tooling.
- Provide data dictionary exports to documentation portal.


