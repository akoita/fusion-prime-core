## Observability Stack

Artifacts defined here configure Cloud Logging, Cloud Monitoring, and Cloud Trace for Fusion Prime services.

- `dashboards/`: JSON definitions for Cloud Monitoring dashboards (service health, settlement latency, risk metrics).
- `alerts/`: Terraform-compatible alerting policies (SLO violations, error budget burn, Pub/Sub backlog).
- `logging/`: (future) Log-based metrics, sinks, and retention policies.

### Guidelines
- Metrics follow OpenTelemetry semantic conventions and are exported via OTLP.
- Dashboards grouped by bounded context (settlement, risk, compliance, contracts).
- Alerts reference contact policies run by DevOps & SecOps; ensure runbook links added.
- Terraform modules under `infra/terraform` consume these definitions for deployment.

