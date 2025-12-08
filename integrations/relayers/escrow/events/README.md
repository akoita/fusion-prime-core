# Escrow Event Relayer

Prototype service responsible for consuming Escrow contract events (deployed via EscrowFactory) and publishing settlement messages into Pub/Sub.

## Responsibilities
- Connect to on-chain provider (e.g., WebSocket RPC) and monitor:
  - `EscrowFactory.EscrowDeployed` events to track new escrow instances
  - `Escrow.EscrowReleased` events for settlement completions
  - `Escrow.EscrowRefunded` events for refund handling
- Transform event data to protobuf `SettlementEvent` payloads with payer/payee/chain/escrow metadata.
- Publish messages to `settlement.events.v1` topic with schema validation.
- Provide metrics and logging for event processing.

## Implementation Sketch
- Language: Python (leveraging web3.py) or TypeScript (ethers.js). For now, scaffold Python script.
- Environment variables:
  - `RPC_URL`: WebSocket/HTTP endpoint.
  - `PUBSUB_TOPIC`: Pub/Sub topic name.
  - `SERVICE_ACCOUNT_JSON`: path to credentials.
- Use Pub/Sub Lite emulator for local development where applicable.

## Next Steps
1. Build script to listen for events using web3.py and publish to Pub/Sub.
2. Add tests mocking event data to ensure correct protobuf serialization.
3. Integrate into Cloud Build pipeline for deployment as Cloud Run job.
