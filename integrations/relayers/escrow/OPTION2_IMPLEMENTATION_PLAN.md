# Option 2 Implementation Plan: Dynamic Escrow Monitoring

## Overview
Implement a production-ready relayer that dynamically discovers escrow contracts from Factory events and monitors all escrow lifecycle events.

## Current Problem
- Relayer only monitors Factory contract (0x311E63...6914)
- Factory emits: `EscrowDeployed` ✅
- Individual escrows emit: `Approved`, `EscrowReleased`, `EscrowRefunded` ❌ NEVER CAPTURED
- Result: Approval workflow fails because events are never published to Pub/Sub

## Solution Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Production Relayer                        │
│                                                              │
│  ┌────────────────────┐      ┌──────────────────────────┐  │
│  │  Factory Monitor   │      │   Escrow Discovery       │  │
│  │                    │─────▶│   & Registry             │  │
│  │  EscrowDeployed    │      │                          │  │
│  └────────────────────┘      │  Set<EscrowAddresses>    │  │
│                               │  + Checkpoint Store      │  │
│                               └──────────────────────────┘  │
│                                          │                   │
│                                          ▼                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Escrow Monitors (Dynamic + Concurrent)      │  │
│  │                                                        │  │
│  │  For each escrow in registry (parallel queries):     │  │
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

## Implementation Phases

### Phase 1: Add Dual ABI Support
**Goal**: Support both Factory and Escrow contract event definitions

**Files to Modify**:
- `integrations/relayers/escrow/main_production.py`

**Tasks**:
1. Add complete Escrow contract ABI with lifecycle events:
```python
ESCROW_CONTRACT_ABI = [
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

2. Keep existing Factory ABI for `EscrowDeployed`

**Acceptance Criteria**:
- Both ABIs are defined and ready to use
- No changes to relayer logic yet (just preparation)

---

### Phase 2: Create Escrow Registry
**Goal**: Maintain in-memory set of escrow addresses with checkpoint persistence

**New File**: `integrations/relayers/escrow/escrow_registry.py`

**Implementation**:
```python
from typing import Set
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class EscrowRegistry:
    """Manages discovered escrow addresses with persistence."""

    def __init__(self, checkpoint_file: str = "/tmp/escrow_registry.json"):
        self.checkpoint_file = Path(checkpoint_file)
        self.escrows: Set[str] = set()
        self._load()

    def add_escrow(self, address: str) -> bool:
        """Add new escrow address. Returns True if newly added."""
        address_lower = address.lower()
        if address_lower not in self.escrows:
            self.escrows.add(address_lower)
            logger.info(f"New escrow discovered: {address_lower}")
            return True
        return False

    def get_all_escrows(self) -> Set[str]:
        """Get all registered escrow addresses."""
        return self.escrows.copy()

    def count(self) -> int:
        """Get count of registered escrows."""
        return len(self.escrows)

    def save(self) -> None:
        """Persist registry to checkpoint file."""
        data = {
            "escrows": list(self.escrows),
            "count": len(self.escrows)
        }
        with open(self.checkpoint_file, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved {len(self.escrows)} escrows to {self.checkpoint_file}")

    def _load(self) -> None:
        """Load registry from checkpoint file."""
        if not self.checkpoint_file.exists():
            logger.info("No existing registry checkpoint found, starting fresh")
            return

        try:
            with open(self.checkpoint_file, "r") as f:
                data = json.load(f)
            self.escrows = set(data.get("escrows", []))
            logger.info(f"Loaded {len(self.escrows)} escrows from {self.checkpoint_file}")
        except Exception as e:
            logger.error(f"Failed to load registry: {e}, starting fresh")
            self.escrows = set()
```

**Tasks**:
1. Create `EscrowRegistry` class with in-memory set
2. Implement `add_escrow(address)` method
3. Implement `get_all_escrows()` method
4. Implement checkpoint save/load using JSON
5. Add unit tests for registry

**Acceptance Criteria**:
- Registry can add escrows and track count
- Registry persists to file and loads on restart
- Unit tests pass

---

### Phase 3: Extend Production Relayer for Multi-Contract Monitoring
**Goal**: Support querying events from multiple contract addresses

**Files to Modify**:
- `integrations/relayers/escrow/production_relayer.py`

**Current Limitation**:
```python
# Line 212: Single contract address
contract = self.web3.eth.contract(
    address=self.config.contract_address,  # ← Single Factory address
    abi=self.abi
)
```

**New Approach**: Add method to query specific contract:
```python
def _get_contract(self, contract_address: str, abi: List[Dict[str, Any]]):
    """Get contract instance for specific address."""
    return self.web3.eth.contract(
        address=Web3.to_checksum_address(contract_address),
        abi=abi
    )

async def _query_contract_events(
    self,
    contract_address: str,
    abi: List[Dict[str, Any]],
    event_name: str,
    from_block: int,
    to_block: int
) -> List[EventData]:
    """Query events from specific contract."""
    contract = self._get_contract(contract_address, abi)
    event = getattr(contract.events, event_name)

    events = await self._to_thread(
        event.get_logs,
        fromBlock=from_block,
        toBlock=to_block
    )

    return events
```

**Tasks**:
1. Add `_get_contract()` helper method
2. Add `_query_contract_events()` method
3. Refactor existing `_query_events()` to use new method
4. Keep Factory monitoring as primary flow

**Acceptance Criteria**:
- Can query events from arbitrary contract address
- Factory monitoring still works as before
- No breaking changes to existing code

---

### Phase 4: Integrate Discovery + Monitoring
**Goal**: Wire together Factory discovery and escrow monitoring

**Files to Modify**:
- `integrations/relayers/escrow/production_relayer.py`
- `integrations/relayers/escrow/main_production.py`

**Core Logic**:
```python
async def _process_block_range(self, from_block: int, to_block: int):
    """Process a block range: discover escrows + query all events."""

    # Step 1: Query Factory for EscrowDeployed
    factory_events = await self._query_contract_events(
        contract_address=self.config.contract_address,  # Factory
        abi=FACTORY_ABI,
        event_name="EscrowDeployed",
        from_block=from_block,
        to_block=to_block
    )

    # Step 2: Extract and register new escrow addresses
    for event in factory_events:
        escrow_address = event["args"]["escrow"]
        if self.escrow_registry.add_escrow(escrow_address):
            # New escrow discovered!
            pass

    # Step 3: Get all registered escrows
    all_escrows = self.escrow_registry.get_all_escrows()

    # Step 4: Query each escrow for lifecycle events (SEQUENTIAL for now)
    for escrow_address in all_escrows:
        # Query Approved events
        approved_events = await self._query_contract_events(
            contract_address=escrow_address,
            abi=ESCROW_ABI,
            event_name="Approved",
            from_block=from_block,
            to_block=to_block
        )

        # Query Released events
        released_events = await self._query_contract_events(
            contract_address=escrow_address,
            abi=ESCROW_ABI,
            event_name="EscrowReleased",
            from_block=from_block,
            to_block=to_block
        )

        # Query Refunded events
        refunded_events = await self._query_contract_events(
            contract_address=escrow_address,
            abi=ESCROW_ABI,
            event_name="EscrowRefunded",
            from_block=from_block,
            to_block=to_block
        )

        # Publish all events
        all_events = factory_events + approved_events + released_events + refunded_events
        for event in all_events:
            await self._publish_event(event)

    # Step 5: Save registry checkpoint
    self.escrow_registry.save()
```

**Tasks**:
1. Add `escrow_registry` field to `ProductionEventRelayer`
2. Implement discovery logic in `_process_block_range()`
3. Implement sequential escrow querying
4. Update `_publish_event()` to use correct contract address
5. Add registry save on checkpoint

**Acceptance Criteria**:
- Relayer discovers new escrows from Factory events
- Relayer queries all escrows for lifecycle events
- Events are published with correct `contract_address` field
- Registry persists across restarts

---

### Phase 5: Add Concurrent Querying (Performance Optimization)
**Goal**: Query multiple escrows in parallel using asyncio

**Files to Modify**:
- `integrations/relayers/escrow/production_relayer.py`

**Implementation**:
```python
async def _query_all_escrows_concurrent(
    self,
    escrow_addresses: Set[str],
    from_block: int,
    to_block: int,
    max_concurrent: int = 10
) -> List[EventData]:
    """Query all escrows concurrently with rate limiting."""

    semaphore = asyncio.Semaphore(max_concurrent)

    async def query_single_escrow(address: str) -> List[EventData]:
        async with semaphore:
            # Query all 3 events for this escrow
            tasks = [
                self._query_contract_events(address, ESCROW_ABI, "Approved", from_block, to_block),
                self._query_contract_events(address, ESCROW_ABI, "EscrowReleased", from_block, to_block),
                self._query_contract_events(address, ESCROW_ABI, "EscrowRefunded", from_block, to_block),
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Flatten and filter errors
            all_events = []
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Error querying {address}: {result}")
                else:
                    all_events.extend(result)

            return all_events

    # Query all escrows in parallel
    tasks = [query_single_escrow(addr) for addr in escrow_addresses]
    results = await asyncio.gather(*tasks)

    # Flatten results
    return [event for events in results for event in events]
```

**Configuration**:
```python
# Environment variables
MAX_CONCURRENT_QUERIES = int(os.getenv("MAX_CONCURRENT_QUERIES", "10"))
```

**Tasks**:
1. Implement `_query_all_escrows_concurrent()` with asyncio.gather
2. Add Semaphore for rate limiting
3. Add error handling for individual query failures
4. Replace sequential querying with concurrent version
5. Add configuration for concurrency limit

**Acceptance Criteria**:
- Escrows are queried in parallel (verify with timing logs)
- Rate limiting prevents RPC overload
- Individual failures don't break entire batch
- Performance improvement: 50s → 2.5s for 100 escrows

---

### Phase 6: Testing & Validation
**Goal**: Verify the implementation works end-to-end

**Test Strategy**:

#### A. Unit Tests
Create `integrations/relayers/escrow/test_escrow_registry.py`:
```python
def test_registry_add_escrow():
    registry = EscrowRegistry("/tmp/test_registry.json")
    assert registry.add_escrow("0xABC...") == True
    assert registry.add_escrow("0xABC...") == False  # Duplicate
    assert registry.count() == 1

def test_registry_persistence():
    registry1 = EscrowRegistry("/tmp/test_registry.json")
    registry1.add_escrow("0xABC...")
    registry1.save()

    registry2 = EscrowRegistry("/tmp/test_registry.json")
    assert registry2.count() == 1
```

#### B. Integration Tests
Update `tests/test_relayer_readiness.py` to verify:
- Relayer discovers escrows from Factory
- Relayer captures Approved events
- Events have correct `contract_address` field

#### C. Workflow Tests
Run `tests/test_escrow_approval_workflow.py`:
- Expected: Approval transaction triggers DB update
- Verify: `approvals_count` transitions from 0 → 1

**Tasks**:
1. Write unit tests for `EscrowRegistry`
2. Add integration tests for discovery logic
3. Update relayer readiness tests
4. Run workflow tests to verify approval flow
5. Check Settlement Service logs for event processing

**Acceptance Criteria**:
- All unit tests pass
- Integration tests pass
- Workflow approval test PASSES (was failing before)
- Settlement Service logs show "Processing approval for escrow..."

---

### Phase 7: Deployment
**Goal**: Deploy updated relayer to Cloud Run

**Deployment Steps**:

1. Update environment variables:
```bash
# Keep Factory address for discovery
CONTRACT_ADDRESS=0x311E63dfcEfe7f2c202715ef0DF01CDA82f58914

# Add new config for concurrent queries
MAX_CONCURRENT_QUERIES=10

# Keep existing config
CHAIN_ID=11155111
RPC_URL=https://sepolia.gateway.tenderly.co/72gZoWFjAN7SQMDZ2D3llq
PUBSUB_PROJECT_ID=fusion-prime
PUBSUB_TOPIC_ID=settlement.events.v1
START_BLOCK=9508300
```

2. Deploy to Cloud Run:
```bash
gcloud run deploy escrow-event-relayer-prod \
  --source integrations/relayers/escrow \
  --region us-central1 \
  --set-env-vars <above> \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1
```

3. Monitor logs for:
- "New escrow discovered: 0x..."
- "Loaded N escrows from checkpoint"
- "Processing blocks X to Y" with concurrent queries

**Tasks**:
1. Update relayer environment variables
2. Deploy to Cloud Run
3. Monitor startup logs
4. Verify escrow discovery from past blocks
5. Run workflow test to confirm end-to-end

**Acceptance Criteria**:
- Relayer deploys successfully
- Relayer loads existing escrows from Factory history
- New workflow tests pass with approval events captured

---

### Phase 8: Monitoring & Documentation
**Goal**: Add observability and document the system

**Monitoring Additions**:
```python
# Add metrics logging
logger.info(f"Registry: {registry.count()} escrows registered")
logger.info(f"Discovered {new_count} new escrows in blocks {from_block}-{to_block}")
logger.info(f"Queried {len(all_escrows)} escrows in {elapsed:.2f}s")
logger.info(f"Published {event_count} events to Pub/Sub")
```

**Documentation**:
- Update `README.md` with Option 2 architecture
- Add troubleshooting guide for common issues
- Document checkpoint format and recovery process

**Tasks**:
1. Add detailed logging for discovery and querying
2. Log performance metrics (query time, escrow count)
3. Update README with architecture diagrams
4. Create troubleshooting guide
5. Document checkpoint file format

**Acceptance Criteria**:
- Logs show clear progression through discovery/monitoring
- README documents the dynamic monitoring approach
- Troubleshooting guide covers common failure modes

---

## Timeline Estimate

| Phase | Tasks | Time Estimate |
|-------|-------|---------------|
| Phase 1: Dual ABI | Add escrow contract ABI | 15 minutes |
| Phase 2: Registry | Create EscrowRegistry class | 30 minutes |
| Phase 3: Multi-Contract Support | Refactor relayer querying | 45 minutes |
| Phase 4: Integration | Wire discovery + monitoring | 1 hour |
| Phase 5: Concurrency | Add asyncio parallel queries | 45 minutes |
| Phase 6: Testing | Unit + integration tests | 1 hour |
| Phase 7: Deployment | Deploy and validate | 30 minutes |
| Phase 8: Monitoring | Logging + documentation | 30 minutes |
| **Total** | | **~5-6 hours** |

## Success Criteria

The implementation is complete when:
1. ✅ Relayer discovers escrows from `EscrowDeployed` events
2. ✅ Relayer monitors all escrows for lifecycle events
3. ✅ Events are published with correct `contract_address`
4. ✅ Registry persists across restarts
5. ✅ Concurrent querying improves performance
6. ✅ Workflow approval test **PASSES** (currently FAILING)
7. ✅ Settlement Service logs show approval event processing
8. ✅ Database shows `approvals_count` transitions from 0 → 1

## Rollback Plan

If implementation fails:
1. Revert to previous relayer version (only monitors Factory)
2. Approval workflow will still fail (acceptable, not regression)
3. Investigate issues in local testing before re-deploying

## Future Enhancements (Post-MVP)

1. **Escrow Archiving**: Remove finalized escrows from active monitoring
2. **Block Range Optimization**: Skip querying escrows that were deployed after the current block
3. **Historical Backfill**: One-time job to discover all historical escrows
4. **Horizontal Scaling**: Implement partitioning for multiple relayer instances
5. **Metrics Dashboard**: Cloud Monitoring dashboard for escrow discovery rate

---

## Ready to Implement!

This plan provides a clear path from current broken state → working dynamic monitoring with concurrent optimization. Let's start with Phase 1!
