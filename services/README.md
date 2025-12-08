## Microservices

Python services organized by bounded context, each following hexagonal architecture.

- `settlement/`: Orchestrates DvP workflows and cash/asset legs.
- `risk-engine/`: Computes exposure, margin, and liquidation signals.
- `compliance/`: KYC/KYB, AML rules, and case management.
- `fiat-gateway/`: Fiat rails, banking integrations, reconciliation.

Structure inside each service:
- `app/`: FastAPI entrypoints, command/query handlers.
- `domain/`: Entities, aggregates, value objects, domain services.
- `adapters/`: Ports for databases, messaging, external APIs.
- `infrastructure/`: Cloud Run/GKE configs, Cloud Pub/Sub bindings, resilience patterns.
- `tests/`: Unit, integration, contract tests.
- Additional folders (`schemas/`, `rules/`, `scripts/`) as needed for sagas, Outbox, and automation.

