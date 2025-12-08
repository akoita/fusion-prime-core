# Testnet Bridge Setup for Cross-Chain Integration

## Overview

The Cross-Chain Integration Service now supports executing real bridge transactions on testnets using Axelar and Chainlink CCIP.

## Testnet Contract Addresses

### Axelar Testnet (Updated addresses may be needed)

**Ethereum Sepolia:**
- Gateway: `0xe432150cce91c13a887f7D836923d5597adD8E31`
- Gas Service: `0xbE406F0189A0B4cf3A05C286473D23791Dd44Cc6`

**Polygon Amoy:**
- Gateway: `0xBF62ef1486468a6bd26Dd669C06db43dE641d239`
- Gas Service: `0xbE406F0189A0B4cf3A05C286473D23791Dd44Cc6`

**Arbitrum Sepolia:**
- Gateway: `0xe432150cce91c13a887f7D836923d5597adD8E31`
- Gas Service: `0xbE406F0189A0B4cf3A05C286473D23791Dd44Cc6`

### Chainlink CCIP Testnet

**Ethereum Sepolia:**
- Router: `0x0BF3dE8c5D3e8A2B34D2BEeB17ABfCeBaf363A59`

**Polygon Amoy:**
- Router: `0x1035CabC275068e0F4b745A29CEDf38E13aF41b1`

**Arbitrum Sepolia:**
- Router: `0x88E492127709447A5AB4da4A0D1861Bab2bE98e5`

## Required Environment Variables

```bash
# RPC URLs (already in .env.dev)
ETH_RPC_URL=https://sepolia.infura.io/v3/YOUR_KEY
POLYGON_RPC_URL=https://rpc-amoy.polygon.technology
ARBITRUM_RPC_URL=https://sepolia-rollup.arbitrum.io/rpc

# Private key for signing transactions (from .env.dev line 45)
DEPLOYER_PRIVATE_KEY=0x...

# Optional: Override bridge addresses via environment
AXELAR_GATEWAY_ETH=0x...
AXELAR_GATEWAY_POLYGON=0x...
CCIP_ROUTER_ETH=0x...
CCIP_ROUTER_POLYGON=0x...
```

## How It Works

1. **Settlement Initiation**: When a settlement is initiated via `/api/v1/orchestrator/settlement`:
   - Settlement record is created in database
   - Bridge executor is initialized for source chain
   - Transaction payload is encoded
   - Bridge transaction is executed (Axelar or CCIP)
   - Message record is created and linked to settlement

2. **Message Monitoring**: The message monitor periodically:
   - Checks message status via bridge APIs
   - Updates message status (pending → sent → confirmed → delivered)
   - When message is delivered, updates settlement status to "completed"

3. **Status Tracking**: Settlement status can be queried via:
   - `GET /api/v1/orchestrator/status/{settlement_id}`

## Testing

Run the integration test:
```bash
pytest tests/test_cross_chain_integration_full.py::TestCrossChainSettlementFlow::test_complete_cross_chain_settlement -v
```

The test will:
1. Initiate a settlement
2. Wait for bridge transaction to execute
3. Monitor message status
4. Verify settlement completes

## Notes

- Bridge addresses are hardcoded in `bridge_executor.py` - update if testnet addresses change
- Gas estimation is approximate - transactions may need more gas
- Cross-chain transactions can take 5-10 minutes to complete
- Test timeout is 5 minutes - may need adjustment for slow networks

## Updating Bridge Addresses

If testnet addresses change, update `services/cross-chain-integration/app/services/bridge_executor.py`:
- `AXELAR_GATEWAY_TESTNET`
- `AXELAR_GAS_SERVICE_TESTNET`
- `CCIP_ROUTER_TESTNET`

Or use environment variables for dynamic configuration.
