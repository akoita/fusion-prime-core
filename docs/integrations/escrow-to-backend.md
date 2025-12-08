# Escrow Event to Backend Ingest Plan

## Overview
Escrow contracts (deployed via EscrowFactory) emit `EscrowReleased(payee, amount, releasedAt)` when release conditions are met. We need to bridge this event to the settlement service ingest workflow and maintain state consistency.

## Flow
1. **Contract Event Emission**
   - Deploy Escrow instances via EscrowFactory capturing contract addresses and network.
   - Escrow emits `EscrowReleased` with payer/payee/amount/timestamp metadata.
2. **Event Listener / Relayer**
   - Use Foundry script or Chainlink/Axelar relayer to subscribe to events.
   - Relay events into Pub/Sub via signed service account.
3. **Pub/Sub Topic**
   - Reuse `settlement.events.v1` schema; encode event payload in protobuf.
4. **Settlement Service Consumer**
   - Subscribe to `settlement.events.v1`, update command status in Cloud SQL, and notify API clients.
5. **SDK Notification**
   - Provide WebSocket or polling endpoint for clients to retrieve status updates.

## Required Work
- Implement relayer microservice in `integrations/relayers` with web3.py + Pub/Sub publish logic.
- Add backend consumer service to `services/settlement` using Pub/Sub streaming pull.
- Update schema definitions if needed (e.g., add escrow address and chain_id fields).
- Extend TypeScript SDK to listen for status updates via API or Pub/Sub.

## Risks
- Event ordering between on-chain release and backend ingest.
- Handling retries/idempotency in relayer and backend consumer.
- Security of relayer credentials and authentication.

## Next Steps
- Monitor EscrowFactory.EscrowDeployed events to track new escrow instances.
- Design protobuf updates for event payloads (`payer`, `payee`, `chain_id`, `escrow_address`).
- Scaffold integration relayer service (Python) with Pub/Sub publish capability.
- Build backend consumer prototype with streaming pull and database persistence.
