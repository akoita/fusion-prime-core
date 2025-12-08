# Sprint 01: Foundation

- **Duration**: 2 weeks
- **Goal**: Establish baseline tooling and scaffolding for cross-chain treasury platform.

## Objectives
- Define coding standards, tooling, and developer experience for the monorepo.
- Deliver initial automation for Foundry and GCP CI/CD pipelines.
- Scaffold service templates with shared libraries and testing harnesses.

## Workstreams
- **Contracts**: Configure Foundry workspace, add sample wallet module skeleton, write Forge CI job.
- **Backend Services**: Create reusable FastAPI service template with hexagonal structure and Cloud Run deployment pipeline.
- **Data & Analytics**: Draft BigQuery schema registry and Pub/Sub topic conventions.
- **DevOps**: Build base Terraform project, enable Cloud Build/Deploy pipelines, set up secrets management with Secret Manager.
- **Compliance**: Establish policy-as-code repository layout and linting workflows.
- **API/SDK**: Define versioning strategy, start TypeScript SDK bootstrap.

## Deliverables
- `docs/standards/coding-guidelines.md` (new)
- CI pipelines for contracts and services (`infra/cloud-build/*.yaml`)
- Terraform bootstrap (`infra/terraform/project/main.tf`)
- Service template (e.g., `services/settlement` initial FastAPI skeleton)
- TypeScript SDK baseline (`sdk/ts`) with workspace setup and lint config

## Key Decisions
- **Message schema format**: Adopt **Protobuf** for Pub/Sub topics to leverage native schema validation, efficient payloads, and shared tooling across languages.
- **Service discovery**: Use **Cloud Run paired with Service Directory** for stable endpoints, IAM-aware discovery, and health metadata without self-hosted components.
- **Secrets rotation**: Standardize on **Secret Manager backed by Cloud KMS** with automated rotation hooks for compliance-grade auditing and lifecycle control.

## Risks & Mitigations
- **Risk**: GCP resource quotas slowing provisioning.
  - *Mitigation*: Request quota increases early; use stub deployments initially.
- **Risk**: Coordination overhead across teams.
  - *Mitigation*: Daily stand-ups, shared Notion/Jira board, enforce architecture review cadence.
- **Risk**: Toolchain drift between Foundry and CI.
  - *Mitigation*: Version pinning, lockfiles, automated compatibility checks.

## Metrics
- Pipeline success rate ≥ 95%.
- Service template deploys to Cloud Run staging within <10 minutes.
- SDK lint/test suite passes on CI.
