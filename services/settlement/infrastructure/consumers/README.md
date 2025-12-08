# Settlement Event Consumer Plan

## Purpose
Process Pub/Sub `settlement.events.v1` messages to update command status and persist audit trail.

## Architecture
- **Subscriber**: Python async worker using `google-cloud-pubsub` streaming pull.
- **Deserializer**: Protobuf `SettlementEvent` generated module.
- **Persistence**: Cloud SQL (PostgreSQL) table `settlement_commands` with status column.
- **Outbox**: Optionally publish internal events to other services (e.g., risk analytics).

## Workflow
1. Subscriber receives message, ack deadline managed via lease extensions.
2. Deserialize protobuf payload; validate required fields.
3. Upsert command record in Cloud SQL (SQLAlchemy async engine).
4. Emit application event/log for observability (`status=CONFIRMED/FAILED`).
5. Ack or nack message based on success.

## TODO
- Design database schema migrations (use Alembic or SQL scripts).
- Implement consumer runner with graceful shutdown and metrics.
- Add integration tests with Pub/Sub emulator.
- Configure Cloud Run job deployment via Terraform.
