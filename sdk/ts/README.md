# Fusion Prime TypeScript SDK

TypeScript-first client for interacting with Fusion Prime APIs, smart contracts, and webhook flows.

## Goals
- Provide typed clients for REST/GraphQL APIs with authentication helpers.
- Implement signing utilities for smart-contract wallet interactions.
- Offer webhook verification and retry helpers.
- Publish to private npm registry with semantic versioning and changelog automation.

## Planned Tooling
- `pnpm` workspace setup.
- `tsup`/`esbuild` for bundling ESM/CJS outputs.
- `vitest` for unit tests.
- `eslint` + `prettier` with shared config.

## Next Steps
- Initialize `package.json` and workspace configuration.
- Scaffold API client module with OpenAPI-generated types.
- Integrate CI job for lint/test (Cloud Build).

