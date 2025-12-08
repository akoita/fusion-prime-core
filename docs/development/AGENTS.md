# Fusion Prime Agent Playbook

## Purpose
- Align contributors and automations around the Fusion Prime specification in `docs/specification.md`.
- Provide clear ownership, handoffs, and collaboration patterns for building the cross-chain treasury and settlement platform.
- Anchor delivery in Google Cloud Platform (GCP) services and Foundry-based smart contract workflows for consistent build, deployment, and runtime management.
- Embed modern microservice, integration, and smart contract design patterns to produce resilient, evolvable systems.

## Architecture Patterns & Principles
- **Domain-driven design & bounded contexts**: Services align to clear business capabilities with ubiquitous language shared across agents.
- **Hexagonal/service-agnostic interfaces**: Ports-and-adapters isolate external dependencies (bridges, custody providers, fiat rails) and ease testing.
- **Event-driven choreography with saga orchestration**: Long-lived workflows (settlement, liquidation, onboarding) use Cloud Pub/Sub, Outbox pattern, and compensating actions for reliability.
- **API-first & contract testing**: OpenAPI/AsyncAPI schemas govern service interactions; consumer-driven contract tests enforce backward compatibility.
- **CQRS and read-model fan-out**: Separate command/query paths where latency or scale demands, backed by BigQuery/Firestore materialized views.
- **Observability as code**: Structured logging, metrics, and tracing baked into pipelines with automated SLO dashboards and alerts in Cloud Monitoring.

## Agent Roster & Charters

### 1. Product Orchestrator Agent
- **Mission**: Translate business goals, regulatory constraints, and user outcomes into an actionable delivery roadmap.
- **Key Responsibilities**:
  - Maintain requirements backlog, prioritized by risk and value.
  - Run discovery with client, treasury, and trading stakeholders.
  - Define release milestones, acceptance criteria, and success metrics.
- **Inputs**: Market/compliance updates, stakeholder feedback, execution reports from all agents.
- **Outputs**: Product requirement documents, milestone plans, roadmap updates, go/no-go decisions.
- **Dependencies**: All delivery agents; especially Compliance & Identity, Smart Contract Architect.

### 2. Smart Contract Architect Agent
- **Mission**: Design and implement account-abstraction wallets, escrow logic, and cross-chain modules on EVM networks.
- **Key Responsibilities**:
  - Define contract architecture for programmable wallets (multi-sig, timelocks, transaction batching).
  - Implement cross-chain messaging adapters (e.g., Axelar, CCIP) for asset movement and state sync.
  - Operate a Foundry toolchain (latest release) across Forge, Cast, and Anvil for compilation, simulation, fuzzing, and deployment orchestration.
  - Apply modular contract design patterns (facets, upgradeable proxies, guard modules) with clear separation of concerns.
  - Establish upgradeability, security guardrails, and audit readiness documentation.
- **Inputs**: Protocol specs from Product Orchestrator, risk limits from Risk & Treasury Analytics, compliance rules from Compliance & Identity.
- **Outputs**: Solidity/Vyper contract repos, Foundry deployment bundles, ABI schemas, audit packets.
- **Dependencies**: Backend Microservices (for off-chain triggers), DevOps & SecOps (for deployment pipelines).

### 3. Cross-Chain Integration Agent
- **Mission**: Bridge messaging and settlement flows between supported EVM chains and any external bridge providers.
- **Key Responsibilities**:
  - Configure relayer infrastructure and monitor cross-chain transaction health.
  - Implement deterministic message formats and retries for settlement finality.
  - Validate collateral snapshots and balances across chains for unified credit line.
- **Inputs**: Contract interfaces, chain configs, monitoring dashboards.
- **Outputs**: Integration services, runbooks, cross-chain telemetry feeds.
- **Dependencies**: Smart Contract Architect, DevOps & SecOps, Risk & Treasury Analytics.

### 4. Backend Microservices Agent
- **Mission**: Deliver Python-based microservices for settlement, risk engines, messaging, and fiat gateway orchestration.
- **Key Responsibilities**:
  - Build a GCP-native service mesh leveraging Cloud Run or GKE, Cloud Pub/Sub for asynchronous messaging, and Cloud Endpoints/API Gateway for ingress controls.
  - Implement Cloud SQL for PostgreSQL data models and Firestore/Bigtable for NoSQL event stores per spec.
  - Apply hexagonal architecture, saga orchestration, circuit breaker, and idempotent consumer patterns with centralized Outbox/Inbox reliability.
  - Ensure idempotent, observable service interactions with strong SLA monitoring using Cloud Logging and Cloud Monitoring.
- **Inputs**: API contract requirements, data schemas from Data Infrastructure, compliance rules.
- **Outputs**: Service repositories, OpenAPI/AsyncAPI specs, deployment manifests, CI pipelines.
- **Dependencies**: Data Infrastructure, Risk & Treasury Analytics, Compliance & Identity, DevOps & SecOps.

### 5. Risk & Treasury Analytics Agent
- **Mission**: Quantify portfolio exposures, cross-margin limits, and settlement risk for real-time decisioning.
- **Key Responsibilities**:
  - Define risk models for collateral valuation, borrowing power, and DvP settlement windows.
  - Deliver simulation suites for stress tests across chains and market conditions, leveraging GCP compute (Cloud Run jobs, Dataflow, Vertex AI notebooks) with streaming analytics patterns (windowing, watermarking).
  - Feed margin calls and liquidation triggers into microservices and smart contracts.
- **Inputs**: Market data, on-chain positions, compliance constraints.
- **Outputs**: Risk policy documents, analytics services, dashboards, alerting thresholds.
- **Dependencies**: Backend Microservices, Data Infrastructure, Product Orchestrator.

### 6. Compliance & Identity Agent
- **Mission**: Embed KYC/KYB, AML, and regulatory reporting into user onboarding and transaction flows.
- **Key Responsibilities**:
  - Integrate identity verification providers and manage case workflows.
  - Define transaction monitoring rules, reporting schedules, and audit trails.
  - Ensure separation of custody vs. trading functions and maintain regulatory mappings with policy-as-code and event-sourcing of compliance states.
- **Inputs**: Regulatory updates, risk policies, product requirements.
- **Outputs**: Compliance microservices, policy artifacts, audit-ready evidence packages.
- **Dependencies**: Backend Microservices, Data Infrastructure, Product Orchestrator.

### 7. Data Infrastructure Agent
- **Mission**: Provide secure, scalable data pipelines and storage for relational and event workloads.
- **Key Responsibilities**:
  - Operate GCP-managed stores including Cloud SQL for PostgreSQL, BigQuery for analytics warehousing, and Firestore/Bigtable for event logs with schema governance.
  - Implement Dataflow/Dataproc ETL/ELT jobs, change-data capture, and Pub/Sub subscriptions for reporting, analytics, and compliance audits.
  - Enforce data retention, encryption, and access control policies via Cloud IAM, Cloud KMS, and VPC Service Controls.
- **Inputs**: Service data contracts, compliance retention rules.
- **Outputs**: Data schemas, lakehouse repositories, monitoring dashboards.
- **Dependencies**: Backend Microservices, Risk & Treasury Analytics, Compliance & Identity.

### 8. API & SDK Agent
- **Mission**: Deliver developer-facing REST/GraphQL APIs and SDKs (Python/TypeScript) for client integration.
- **Key Responsibilities**:
  - Define API contracts aligned with microservice capabilities and security requirements, integrating with GCP API Gateway and Identity-Aware Proxy controls while applying BFF and aggregation patterns where needed.
  - Develop SDKs with authentication, transaction orchestration, and webhook support using TypeScript-first tooling where applicable.
  - Maintain versioning strategy, documentation, and developer portal content.
- **Inputs**: Product requirements, backend service interfaces, UX feedback.
- **Outputs**: API specs, SDK packages, documentation, code samples.
- **Dependencies**: Backend Microservices, DevOps & SecOps, Frontend Experience.

### 9. Frontend Experience Agent
- **Mission**: Provide institutional dashboards for treasury managers, risk officers, and compliance analysts.
- **Key Responsibilities**:
  - Design React-based interfaces for portfolio views, borrow/lend operations, and settlement workflows.
  - Integrate SDKs, real-time data feeds, and alerting interfaces using resilient client-side caching and offline-first patterns for critical workflows.
  - Conduct usability testing with target personas (corporate treasury, hedge fund traders, DAO administrators).
- **Inputs**: API specs, design system guidelines, user research.
- **Outputs**: Web app repository, design system, user guides, UX research summaries.
- **Dependencies**: API & SDK Agent, Risk & Treasury Analytics, Compliance & Identity.

### 10. DevOps & SecOps Agent
- **Mission**: Provide secure CI/CD, infrastructure-as-code, monitoring, and incident response across on-chain and off-chain components.
- **Key Responsibilities**:
  - Implement infrastructure stacks on GCP using Terraform, Cloud Build, Cloud Deploy, Artifact Registry, and Secret Manager while integrating Foundry pipelines for contract releases.
  - Operate observability platform (Cloud Logging, Cloud Monitoring, Cloud Trace) and security tooling (Cloud Armor, Security Command Center, Binary Authorization) with GitOps and policy-as-code guardrails.
  - Coordinate change management, incident response, and business continuity playbooks aligned with GCP SRE practices, including chaos engineering and game days.
- **Inputs**: Deployment manifests, security requirements, chain endpoints, service dependencies.
- **Outputs**: Terraform/Helm charts, runbooks, monitoring dashboards, SOC reports.
- **Dependencies**: All delivery agents.

## Collaboration & Handoffs
- **Requirements Flow**: Product Orchestrator captures goals → disseminates to domain agents → cycle back with feasibility and risk assessments.
- **Design Reviews**: Smart Contract Architect, Backend Microservices, Risk Analytics, and Compliance co-review protocol changes before implementation, ensuring Foundry release plans and GCP architecture choices are validated.
- **Change Control**: DevOps & SecOps chairs change advisory board; major releases require sign-off from Product, Compliance, and Risk agents, and must include Cloud Deploy release plans and Foundry deployment playbooks.
- **Data Governance**: Data Infrastructure owns schema registry; any agent modifying data flows must submit interface change requests.

## Delivery Phases & Lead Agents
- **Foundation (Phase 0-1)**: Product Orchestrator, Smart Contract Architect, Backend Microservices, DevOps & SecOps.
- **Cross-Chain Enablement (Phase 2)**: Cross-Chain Integration, Risk & Treasury Analytics.
- **Compliance & Institutional Readiness (Phase 3)**: Compliance & Identity, Data Infrastructure.
- **External Integrations (Phase 4)**: API & SDK, Frontend Experience.
- **Operational Hardening (Phase 5)**: DevOps & SecOps with support from all agents.

## Operating Cadence
- **Weekly**: Cross-agent delivery sync covering milestones, blockers, and risk posture.
- **Bi-weekly**: Architecture/design review with Smart Contract, Backend, Risk, Compliance, DevOps leads.
- **Monthly**: Regulatory and market landscape review involving Product, Compliance, Risk agents.
- **On-Demand**: Incident response drills and postmortems facilitated by DevOps & SecOps.

## Shared Standards
- **Security**: Zero-trust principles, hardware-backed key management for deployments using Cloud KMS/HSM, mandatory code reviews with static analysis, and Foundry audit trails.
- **Reliability**: SLOs defined for each service; automated rollback via Cloud Deploy, chaos testing on GKE/Cloud Run, and Foundry fork testing for critical settlement flows.
- **Documentation**: Every deliverable includes runbooks, diagrams, and API references stored in a shared knowledge base with GCP architecture runbooks and Foundry playbooks.
- **Testing**: Unit, integration, contract, chaos, and performance testing automated through GCP-managed CI pipelines with Foundry simulations and saga workflow verification suites.
