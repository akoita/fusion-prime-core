# Fusion Prime Coding Guidelines

## Languages
- **Solidity** (via Foundry) for smart contracts with consistent pragma versions, SPDX identifiers, and NatSpec documentation.
- **Python** (3.11+) for backend services using type hints, Pydantic models, and FastAPI.
- **TypeScript** (ES2022) for SDKs and frontend applications with strict type checking (`"strict": true`).

## General Principles
- Enforce domain-driven design boundaries: domain logic lives in `domain/`, external integrations in `adapters/`.
- Prefer dependency inversion via interfaces/abstract classes to enable testability.
- Follow hexagonal architecture and saga patterns as outlined in `AGENTS.md`.
- Use linting/formatting tools consistently (Prettier, ESLint, Ruff, Black as appropriate).
- Ensure all changes include automated tests or rationale for lack thereof.

## Smart Contracts (Solidity)
- Use latest stable Solidity version supported by Foundry; pin versions in `foundry.toml`.
- Apply modular contract patterns (facets, proxies) as required; document upgrade paths.
- Write comprehensive Forge tests with fuzzing and invariant checks.
- Emit structured events for critical state changes; avoid using `tx.origin`.
- Use OpenZeppelin libraries when applicable; document deviations.

## Python Services
- Use Poetry for dependency management; lock versions.
- Structure modules per service template (app, domain, adapters, infrastructure, tests).
- FastAPI endpoints must validate input via Pydantic models; return typed responses.
- Implement async IO where possible; avoid blocking operations in event loops.
- Tests: pytest with coverage ≥ 80%; integration tests against local emulators (Cloud SQL, Pub/Sub) when feasible.

## TypeScript SDK & Frontend
- Use pnpm workspaces; enforce ESLint + Prettier.
- Target ESM by default with compatible CJS builds when required.
- Prefer composition APIs/hooks; avoid global state.
- Tests with Vitest/Jest; strive for coverage ≥ 80% on critical modules.
- Typed API clients generated from OpenAPI specs; manual layers only when necessary.

## Infrastructure & Automation
- Terraform code follows HashiCorp style conventions; modules named by bounded context.
- Cloud Build/Deploy configs stored under `infra/cloud-build` and `infra/cloud-deploy` with consistent naming.
- Scripts in `scripts/` must be idempotent and shellcheck clean.
- Document new automation in relevant README and sprint notes.

## Reviews & CI
- Require peer review for all PRs; ensure agents impacted are tagged.
- CI pipelines must run lint, test, and security checks before merge.
- No direct pushes to `main` except via approved PRs/automation.
- Maintain changelog per module where relevant (SDK, services, contracts).


