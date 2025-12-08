# Sprint 02: Core Settlement & Cross-Chain Foundation

- **Duration**: 2 weeks
- **Goal**: Build production-grade settlement service with cross-chain event ingestion and risk computation pipeline.
- **Status**: 🟡 In Progress (Week 1 Complete, Week 2 Starting)

## Current Progress

### ✅ Completed (Week 1)
- [x] Smart Contracts: `Escrow.sol` + `EscrowFactory.sol` deployed to Sepolia (`0x0F146104422a920E90627f130891bc948298d6F8`)
- [x] GCP Foundation: Project, VPC, Pub/Sub topics (`settlement.events.v1`), Service Accounts
- [x] Local Development: Docker compose stack operational, contracts tested

### ⏳ In Progress (Week 2)
- [ ] Deploy Cloud SQL PostgreSQL instance
- [ ] Deploy Settlement Service to Cloud Run
- [ ] Deploy Event Relayer as Cloud Run Job
- [ ] Setup BigQuery dataset and tables
- [ ] Deploy basic Dataflow pipeline

### 🎯 Quick Deploy Commands

```bash
# 1. Cloud SQL (15 min)
gcloud sql instances create fusion-prime-db --database-version=POSTGRES_15 --tier=db-g1-small --region=us-central1

# 2. Settlement Service (10 min)
cd services/settlement && gcloud builds submit --tag gcr.io/fusion-prime/settlement-service:latest
gcloud run deploy settlement-service --image gcr.io/fusion-prime/settlement-service:latest --region=us-central1

# 3. Event Relayer (10 min)
cd integrations/relayers/escrow && gcloud builds submit --tag gcr.io/fusion-prime/escrow-event-relayer:latest
gcloud run jobs create escrow-event-relayer --image gcr.io/fusion-prime/escrow-event-relayer:latest
```

**Estimated Time to Complete**: ~2 hours

---

## Objectives
- Implement end-to-end settlement command flow from SDK through Pub/Sub to database persistence.
- Deploy escrow contract to testnet with event relayer publishing to Pub/Sub.
- Bootstrap Dataflow risk pipeline consuming settlement events and writing to BigQuery.
- Establish webhook delivery system for external integrations.

## Workstreams

### Smart Contracts (Smart Contract Architect Agent)
- **Tasks**:
  - Implement `Escrow` contract with release conditions (timelocks, multi-sig approvals, emergency refunds)
  - Add `EscrowFactory` for deploying user-specific escrow instances
  - Deploy contracts to Sepolia (Ethereum testnet) and Polygon Amoy
  - Implement cross-chain message handler skeleton (Axelar integration prep)
- **Deliverables**:
  - `contracts/src/Escrow.sol` with comprehensive tests
  - `contracts/src/EscrowFactory.sol`
  - Deployment scripts for Sepolia + Amoy
  - Updated ABI exports in `contracts/out/`

### Backend Services (Backend Microservices Agent)
- **Tasks**:
  - Complete settlement service command validation with Pydantic schemas
  - Implement webhook delivery worker (async HTTP POST with retries and HMAC signing)
  - Add observability: structured logging, Cloud Trace integration, error tracking
  - Deploy settlement service to Cloud Run with Cloud SQL PostgreSQL backend
- **Deliverables**:
  - `services/settlement/app/services/webhook_delivery.py`
  - `services/settlement/app/middleware/observability.py`
  - Cloud Run deployment via `infra/cloud-deploy/`
  - Service-level SLO dashboard in Cloud Monitoring

### Cross-Chain Integration (Cross-Chain Integration Agent)
- **Tasks**:
  - Production-grade event relayer with `web3.py` polling loop
  - Add checkpoint persistence (last processed block number in Cloud SQL)
  - Implement exponential backoff for RPC failures
  - Configure relayer deployment as Cloud Run job (scheduled every 30 seconds)
- **Deliverables**:
  - `integrations/relayers/escrow/events/checkpoint_manager.py`
  - `integrations/relayers/escrow/events/retry_policy.py`
  - Cloud Run job configuration in Terraform

### Data Infrastructure (Data Infrastructure Agent)
- **Tasks**:
  - Provision BigQuery `risk` dataset and tables via Terraform
  - Create Cloud SQL PostgreSQL instance for settlement service
  - Set up Cloud Pub/Sub topics and schemas (`settlement.events.v1`, `chain.events.v1`)
  - Implement database migration runner (Alembic) for settlement service
- **Deliverables**:
  - `infra/terraform/modules/bigquery_risk/` applied to dev environment
  - `infra/terraform/modules/cloudsql/` with HA configuration
  - `services/settlement/alembic/` migration framework
  - Pub/Sub topic provisioning in `infra/terraform/modules/pubsub_settlement/`

### Risk & Treasury Analytics (Risk & Treasury Analytics Agent)
- **Tasks**:
  - Implement basic Dataflow pipeline skeleton (Apache Beam Python)
  - Parse settlement events from Pub/Sub and write to BigQuery `risk.portfolio_exposures`
  - Add windowed aggregation (1-minute tumbling windows)
  - Deploy pipeline to Dataflow with autoscaling (2-10 workers)
- **Deliverables**:
  - `analytics/dataflow/risk-pipeline/main.py` (Apache Beam pipeline)
  - `analytics/dataflow/risk-pipeline/transforms/` (DoFn implementations)
  - Dataflow job deployment via Terraform or Cloud Build
  - Initial monitoring dashboard for pipeline lag and throughput

### API & SDK (API & SDK Agent)
- **Tasks**:
  - Extend TypeScript SDK with real-time WebSocket support for settlement status updates
  - Add retry logic and circuit breaker to HTTP client
  - Publish SDK to npm (scoped package: `@fusion-prime/sdk`)
  - Generate SDK documentation with TypeDoc
- **Deliverables**:
  - `sdk/ts/src/websocket.ts` (WebSocket client)
  - `sdk/ts/src/resilience.ts` (retry/circuit breaker)
  - Published npm package (version 0.2.0)
  - `sdk/ts/docs/` generated documentation

### DevOps & SecOps (DevOps & SecOps Agent)
- **Tasks**:
  - Configure Cloud Armor WAF rules for API endpoints
  - Set up Secret Manager rotation for database credentials
  - Implement Cloud Logging sink to BigQuery for audit trail
  - Create runbooks for common incidents (service restart, database failover)
- **Deliverables**:
  - `infra/terraform/modules/security/cloud_armor.tf`
  - Secret rotation Cloud Function in `infra/functions/secret-rotation/`
  - `docs/runbooks/incident-response.md`
  - Alerting policies for service health and security events

## Key Milestones
- **Week 1 End**: Settlement service deployed to Cloud Run with PostgreSQL backend, contracts deployed to testnets
- **Week 2 End**: Event relayer publishing to Pub/Sub, Dataflow pipeline writing to BigQuery, webhooks delivering events

## Dependencies
- Sprint 01 deliverables (tooling, CI/CD, service template)
- GCP project quotas approved for Cloud SQL, Dataflow workers
- Testnet ETH/MATIC faucet access for contract deployments

## Risks & Mitigations
- **Risk**: Dataflow pipeline complexity causing delays.
  - *Mitigation*: Start with minimal viable pipeline (just event parsing + BigQuery write), defer advanced analytics to Sprint 03.
- **Risk**: RPC endpoint rate limits affecting event relayer.
  - *Mitigation*: Use multiple RPC providers (Infura, Alchemy, Ankr) with automatic failover.
- **Risk**: Cloud SQL connection pooling issues under load.
  - *Mitigation*: Use Cloud SQL Proxy with connection pooling (PgBouncer), monitor connection metrics.

## Acceptance Criteria
- [ ] Settlement command ingested via SDK reaches BigQuery within 30 seconds (p99)
- [ ] Webhook delivery success rate ≥ 99% (with retries)
- [ ] Event relayer processes all testnet escrow events within 60 seconds of block confirmation
- [ ] Dataflow pipeline lag < 10 seconds (p95)
- [ ] All services pass smoke tests on staging environment
- [ ] Security scan (Cloud Security Command Center) shows zero critical vulnerabilities

## Metrics
- **Settlement Service SLO**: 99.5% availability, <500ms p95 latency
- **Webhook Delivery**: 99% success rate, <5s p95 delivery time
- **Dataflow Throughput**: >100 events/second per worker
- **Event Relayer Reliability**: Zero missed events in 48-hour test window

## Testing Strategy
- **Unit Tests**: All new service code covered (target: 80% coverage)
- **Integration Tests**: Settlement service with real PostgreSQL database
- **E2E Tests**: SDK → Settlement Service → Pub/Sub → Dataflow → BigQuery
- **Contract Tests**: Foundry fork tests against mainnet state
- **Load Tests**: Settlement service handling 1000 req/s (using Locust)

## Documentation Updates
- [ ] Update `services/settlement/README.md` with deployment instructions
- [ ] Add `analytics/dataflow/risk-pipeline/QUICKSTART.md`
- [ ] Document webhook HMAC signature verification in SDK README
- [ ] Create `docs/architecture/event-flow.md` diagram

## Post-Sprint Review
- Demo: Live settlement from testnet contract to BigQuery dashboard
- Retrospective: What slowed us down? What worked well?
- Planning: Identify Sprint 03 priorities based on learnings
