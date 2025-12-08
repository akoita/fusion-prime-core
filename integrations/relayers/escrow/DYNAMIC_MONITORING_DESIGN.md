# Dynamic Escrow Monitoring Design (Option 2)

## Overview
Implement a production-ready relayer that dynamically discovers and monitors escrow contracts, scaling with the number of deployed escrows (not total blockchain activity).

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Production Relayer                        │
│                                                              │
│  ┌────────────────────┐      ┌──────────────────────────┐  │
│  │  Factory Monitor   │      │   Escrow Discovery       │  │
│  │                    │─────▶│   & Persistence         │  │
│  │  EscrowDeployed    │      │                          │  │
│  └────────────────────┘      │  Set<EscrowAddresses>    │  │
│                               └──────────────────────────┘  │
│                                          │                   │
│                                          ▼                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Escrow Monitors (Dynamic)                   │  │
│  │                                                        │  │
│  │  For each discovered escrow address:                  │  │
│  │  ┌──────────────┐  ┌───────────────┐  ┌────────────┐ │  │
│  │  │ Approved     │  │ EscrowReleased│  │ Refunded   │ │  │
│  │  └──────────────┘  └───────────────┘  └────────────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
│                                          │                   │
│                                          ▼                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                Pub/Sub Publisher                       │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Dual ABI Support
```python
# Factory ABI - for EscrowDeployed events
FACTORY_ABI = [
    {
        "name": "EscrowDeployed",
        "type": "event",
        "inputs": [
            {"name": "escrow", "type": "address", "indexed": True},
            {"name": "payer", "type": "address", "indexed": True},
            ...
        ]
    }
]

# Escrow ABI - for lifecycle events
ESCROW_ABI = [
    {
        "name": "Approved",
        "type": "event",
        "inputs": [
            {"name": "approver", "type": "address", "indexed": True}
        ]
    },
    {
        "name": "EscrowReleased",
        "type": "event",
        "inputs": [
            {"name": "payee", "type": "address", "indexed": True}
        ]
    },
    {
        "name": "EscrowRefunded",
        "type": "event",
        "inputs": [
            {"name": "payer", "type": "address", "indexed": True}
        ]
    }
]
```

### 2. Escrow Address Registry
- Store discovered escrow addresses in memory (Set)
- Persist to checkpoint store for recovery after restart
- Add new addresses when EscrowDeployed events are detected

### 3. Efficient Querying Strategy
```python
# Per block range:
1. Query Factory for EscrowDeployed events
   → Extract new escrow addresses
   → Add to registry

2. For each escrow in registry:
   → Query Approved events
   → Query EscrowReleased events
   → Query EscrowRefunded events

3. Publish all events to Pub/Sub
```

### 4. Scalability Characteristics
- **RPC Queries per block**: 1 (Factory) + 3 * N (Escrows) where N = number of active escrows
- **With 100 escrows**: ~301 queries per block range
- **Cost**: Linear with YOUR escrows, not entire blockchain
- **Optimization**: Batch queries where possible

## Implementation Plan

### Phase 1: Add Escrow Registry
- [ ] Create `EscrowRegistry` class
- [ ] Store/load from checkpoint
- [ ] Add discovery logic from EscrowDeployed events

### Phase 2: Multi-Contract Monitoring
- [ ] Extend `ProductionEventRelayer` to support multiple contract types
- [ ] Factory monitoring (existing)
- [ ] Dynamic escrow monitoring (new)

### Phase 3: Event Processing
- [ ] Process Factory events → discover escrows
- [ ] Process Escrow events → publish to Pub/Sub
- [ ] Maintain event_type metadata for routing

### Phase 4: Testing & Deployment
- [ ] Unit tests for registry
- [ ] Integration tests with real testnet
- [ ] Deploy and verify with workflow tests

## Benefits
1. **Scalable**: Grows with your contracts, not blockchain size
2. **Efficient**: Only queries known addresses
3. **Resilient**: Persists discovered addresses
4. **Educational**: Great Web3.py learning project!

## Future Enhancements
- Archive old escrows (e.g., finalized > 30 days ago)
- Parallel querying for large escrow sets
- Metrics on escrow discovery rate
