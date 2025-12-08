# Settlement Service

Hexagonal FastAPI service orchestrating delivery-versus-payment (DvP) workflows and ledger updates across chains and fiat rails.

## Structure
- `app/`: FastAPI entrypoints, route handlers, background tasks, and dependencies.
- `domain/`: Aggregates, value objects, domain services modelling settlement workflows and sagas.
- `app/services/`: Application service layer (command ingest, status lookup).
- `infrastructure/`: Cloud Run deployment configs, Pub/Sub consumer, database access, migrations.
- `schemas/`: Pydantic/Avro/Proto message definitions for commands and events.
- `tests/`: Unit and integration tests (SQLite-backed ingestion test, Pub/Sub consumer simulation).

## Local Development
1. Install dependencies via Poetry (`poetry install`).
2. Run FastAPI locally (`poetry run uvicorn app.main:app --reload`).
3. Execute tests (`poetry run pytest`).
4. For local tests, `DATABASE_URL` defaults to `sqlite+aiosqlite:///./settlement.db` and tables are created via fixtures.

## Command Flow Overview
1. **SDK** calls `/commands/ingest` via HTTP (TypeScript client uses `undici`).
2. FastAPI endpoint persists payload via `app/services/commands.py` and returns 202.
3. `/commands/{id}` returns persisted status for SDK polling.
4. Pub/Sub consumer (lifespan-managed) updates records when events arrive.

## Deployment
- Build via Cloud Build pipeline (`infra/cloud-build/service-template-ci.yaml`).
- Deploy using Cloud Deploy configuration (future).
- Observability: structured logging to Cloud Logging, metrics via OpenTelemetry exporters to Cloud Monitoring.
