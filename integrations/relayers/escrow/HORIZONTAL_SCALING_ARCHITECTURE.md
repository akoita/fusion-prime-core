# Horizontal Scaling Architecture for Escrow Relayer

## Overview
This document describes how the dynamic escrow monitoring relayer (Option 2) can be horizontally scaled across multiple instances for high availability and throughput.

## Current State
- **Single Instance**: One relayer monitors Factory + dynamically discovered escrows
- **Concurrent Processing**: Uses asyncio for parallel RPC queries within single instance
- **Capacity**: Can handle ~1,000-10,000 escrows with proper concurrency tuning

## When to Scale Horizontally
Horizontal scaling makes sense when:
- Active escrow count exceeds 10,000
- RPC rate limits are consistently hit even with concurrency optimization
- High availability requirements (99.9%+ uptime)
- Need geographic distribution of RPC providers

## Architecture Design

### 1. Partition Strategy
Divide escrow monitoring across multiple relayer instances using **address-based partitioning**:

```
┌─────────────────────────────────────────────────────────┐
│         Shared Escrow Registry (Cloud SQL)              │
│  {0xE3d298...: created, 0xD0275E...: created, ...}      │
└─────────────────────────────────────────────────────────┘
                          ↓ Read escrow addresses
            ┌─────────────┼─────────────┐
            ↓             ↓             ↓
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │  Relayer 0   │ │  Relayer 1   │ │  Relayer 2   │
    │  (Partition) │ │  (Partition) │ │  (Partition) │
    │              │ │              │ │              │
    │ Monitors:    │ │ Monitors:    │ │ Monitors:    │
    │ hash % 3 = 0 │ │ hash % 3 = 1 │ │ hash % 3 = 2 │
    └──────────────┘ └──────────────┘ └──────────────┘
```

### 2. Consistent Hashing
Each relayer claims responsibility for escrows based on address hash:

```python
def get_partition_for_address(escrow_address: str, num_partitions: int) -> int:
    """Determine which relayer instance should monitor this escrow."""
    # Convert hex address to integer and modulo by partition count
    return int(escrow_address, 16) % num_partitions

# Example with 3 instances:
# 0xE3d2980084b291fBA9684208EbDB5A4cb03bBD29 % 3 = 2 → Relayer 2 monitors
# 0xD0275E28f9e9C3D261db60e8e1204aA2f16f1Ca2 % 3 = 0 → Relayer 0 monitors
```

**Benefits:**
- Deterministic: Same address always maps to same instance
- Balanced: Uniform distribution across partitions
- Stable: Adding/removing instances only affects (1/N) of escrows

### 3. Shared State Components

#### A. Escrow Registry Table (Cloud SQL)
```sql
CREATE TABLE escrow_registry (
    address TEXT PRIMARY KEY,
    discovered_at TIMESTAMP NOT NULL,
    discovered_block_number INTEGER NOT NULL,
    status TEXT NOT NULL,  -- 'active', 'released', 'refunded'
    last_monitored_block INTEGER,
    payer TEXT,
    payee TEXT,
    amount TEXT,
    chain_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_escrow_status ON escrow_registry(status);
CREATE INDEX idx_escrow_discovered_block ON escrow_registry(discovered_block_number);
```

#### B. Relayer Instance Heartbeat Table
```sql
CREATE TABLE relayer_instances (
    instance_id TEXT PRIMARY KEY,
    partition_number INTEGER NOT NULL,
    total_partitions INTEGER NOT NULL,
    last_heartbeat TIMESTAMP NOT NULL,
    current_block INTEGER,
    escrows_monitored INTEGER,
    status TEXT NOT NULL  -- 'active', 'stopping', 'dead'
);

CREATE INDEX idx_relayer_heartbeat ON relayer_instances(last_heartbeat);
```

#### C. Event Processing Deduplication
```sql
CREATE TABLE processed_events (
    event_id TEXT PRIMARY KEY,  -- format: {tx_hash}:{log_index}
    event_type TEXT NOT NULL,
    contract_address TEXT NOT NULL,
    block_number INTEGER NOT NULL,
    processed_at TIMESTAMP NOT NULL,
    processed_by_instance TEXT NOT NULL
);

CREATE INDEX idx_event_block ON processed_events(block_number);
```

### 4. Factory Monitoring - Leader Election

Only ONE instance monitors the Factory contract to avoid duplicate discovery:

#### A. Leader Election via Database Advisory Lock
```python
async def try_acquire_leader_lock(session) -> bool:
    """Try to acquire leader lock for Factory monitoring."""
    # PostgreSQL advisory lock (automatically released on disconnect)
    result = await session.execute(text("SELECT pg_try_advisory_lock(999999)"))
    return result.scalar()

async def release_leader_lock(session):
    """Release leader lock."""
    await session.execute(text("SELECT pg_advisory_unlock(999999)"))
```

#### B. Leader Responsibilities
- Monitor Factory for `EscrowDeployed` events
- Write new escrow addresses to `escrow_registry` table
- Send heartbeat every 30 seconds
- If leader dies, another instance becomes leader (lock auto-released)

#### C. Follower Responsibilities
- Periodically check if leader is alive (heartbeat check)
- Attempt to become leader if no heartbeat > 60 seconds
- Monitor their partition of escrows from registry
- Process escrow lifecycle events

### 5. Coordination Flow

```
1. Instance Startup:
   - Register in relayer_instances table with partition number
   - Start heartbeat thread (update every 30s)
   - Attempt to acquire leader lock

2. If Leader:
   - Monitor Factory contract for EscrowDeployed
   - On new escrow:
     a. Write to escrow_registry
     b. Publish discovery event (optional)

3. If Follower:
   - Check leader heartbeat (every 60s)
   - If leader dead: attempt to become leader

4. All Instances (Leader + Followers):
   - Read escrow_registry
   - Filter escrows for their partition:
     WHERE hash(address) % {total_partitions} = {my_partition}
   - Monitor filtered escrows for Approved/Released/Refunded
   - Write to processed_events for deduplication

5. Event Processing:
   - Check if event already processed (SELECT FROM processed_events)
   - If not processed:
     a. Persist to escrow_records
     b. Publish to Pub/Sub
     c. Insert into processed_events
```

### 6. Deployment Configuration

#### Cloud Run Service (not Job)
Deploy as long-running services instead of jobs:

```yaml
# relayer-instance-0.yaml
gcloud run deploy escrow-relayer-instance-0 \
  --source integrations/relayers/escrow \
  --region us-central1 \
  --platform managed \
  --set-cloudsql-instances fusion-prime:us-central1:fp-relayer-registry \
  --set-env-vars \
    CHAIN_ID=11155111,\
    RPC_URL=https://sepolia.gateway.tenderly.co/KEY1,\
    FACTORY_ADDRESS=0x311E63dfcEfe7f2c202715ef0DF01CDA82f58914,\
    PUBSUB_PROJECT_ID=fusion-prime,\
    PUBSUB_TOPIC_ID=settlement.events.v1,\
    START_BLOCK=9508300,\
    INSTANCE_ID=relayer-0,\
    PARTITION_NUMBER=0,\
    TOTAL_PARTITIONS=3,\
    DATABASE_URL=postgresql+asyncpg://...,\
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 1 \
  --timeout 3600
```

Repeat for `relayer-instance-1`, `relayer-instance-2`, etc.

### 7. Failure Scenarios

#### Scenario A: Leader Dies
1. Follower detects stale heartbeat (>60s)
2. Follower attempts `pg_try_advisory_lock(999999)`
3. First to acquire lock becomes new leader
4. New leader resumes Factory monitoring from last checkpoint
5. **Risk**: Brief gap in Factory monitoring (max 60s)
6. **Mitigation**: Relayer catches up by querying missed blocks

#### Scenario B: Follower Dies
1. Leader continues monitoring Factory
2. Other followers continue monitoring their partitions
3. Dead follower's partition is not monitored
4. **Risk**: Missed events for escrows in that partition
5. **Mitigation**: On restart, follower resumes from checkpoint and catches up

#### Scenario C: Database Connection Lost
1. Instance cannot read registry or write events
2. Instance logs error and retries with exponential backoff
3. If connection not restored in 5 minutes: instance shuts down
4. Cloud Run restarts instance automatically
5. **Risk**: Event processing delay during outage
6. **Mitigation**: Cloud SQL has 99.95% SLA

#### Scenario D: Partition Rebalancing
When adding/removing instances:
1. Update `TOTAL_PARTITIONS` environment variable for all instances
2. Rolling restart instances one by one
3. Each instance recalculates which escrows to monitor
4. **Risk**: Brief overlap where multiple instances monitor same escrow
5. **Mitigation**: `processed_events` table deduplicates

### 8. Performance Characteristics

#### Single Instance
- Monitors: ALL escrows (e.g., 10,000)
- Queries/block: 1 (Factory) + 3 × 10,000 (Escrows) = 30,001
- Throughput: Limited by asyncio concurrency + RPC rate limits

#### 3 Instances
- Each monitors: 10,000 / 3 ≈ 3,333 escrows
- Queries/block per instance: 1 (Factory, leader only) + 3 × 3,333 ≈ 10,000
- Total throughput: 3× distributed
- Benefits: Fault tolerance, independent RPC providers

#### 10 Instances
- Each monitors: 10,000 / 10 = 1,000 escrows
- Queries/block per instance: 3 × 1,000 = 3,000
- Total throughput: 10× distributed
- Benefits: High availability, geographic distribution

### 9. Cost Analysis

#### Single Instance
- Cloud Run: 1 instance × 2 vCPU × 24h = $0.025/vCPU-hour × 2 × 24 = $1.20/day
- Cloud SQL: Shared registry (minimal writes)
- RPC: Tenderly free tier or paid based on calls

#### 3 Instances
- Cloud Run: 3 × $1.20/day = $3.60/day
- Cloud SQL: Same (registry is shared)
- RPC: Can use 3 different providers for redundancy

**Break-even point**: Horizontal scaling worth it when:
- Escrow count > 10,000
- Availability requirements justify 3× cost
- Single instance can't keep up with blockchain

### 10. Monitoring & Observability

#### Key Metrics (Cloud Monitoring)
```python
# Per-instance metrics
- relayer_escrows_monitored (gauge): Number of escrows in partition
- relayer_blocks_processed (counter): Blocks processed
- relayer_events_published (counter): Events sent to Pub/Sub
- relayer_is_leader (gauge): 1 if leader, 0 if follower
- relayer_last_heartbeat_age (gauge): Seconds since last heartbeat

# Aggregate metrics
- total_active_instances (gauge): Count of healthy instances
- total_escrows_registered (gauge): Size of escrow_registry
- leader_election_count (counter): Leadership changes
- event_deduplication_hits (counter): Duplicate events caught
```

#### Alerting Rules
- No active leader for > 2 minutes → Page on-call
- Instance heartbeat stale > 5 minutes → Restart instance
- Event processing lag > 100 blocks → Investigate RPC issues
- Duplicate event rate > 1% → Check partition configuration

### 11. Comparison to The Graph

| Feature | Our Approach | The Graph |
|---------|-------------|-----------|
| Discovery | Factory monitoring with leader election | Subgraph manifest defines contracts |
| Partitioning | Address-based consistent hashing | Block range assignment |
| Redundancy | 1 leader + N followers | Multiple indexers per subgraph |
| State | Shared Cloud SQL database | Independent Postgres per indexer |
| Queries | Direct to Settlement Service | GraphQL gateway routes to indexers |
| Complexity | Medium (coordination needed) | High (incentive layer, staking) |
| Cost | Pay for infrastructure | Pay for queries + GRT staking |

**Our Advantage**: Simpler for single project, no token economics
**The Graph Advantage**: Battle-tested for massive scale, decentralized

## Implementation Priority

### Phase 1 (Current): Single Instance with Concurrency
- ✅ Implement Option 2 with asyncio concurrency
- ✅ Prove dynamic escrow monitoring works
- ✅ Handle 1,000-10,000 escrows

### Phase 2 (Future): Horizontal Scaling
- Add escrow_registry table
- Add relayer_instances table
- Implement leader election
- Test with 2-3 instances

### Phase 3 (Scale): Production Hardening
- Add monitoring/alerting
- Test failure scenarios
- Document runbooks
- Scale to 5-10 instances if needed

## Conclusion

The dynamic escrow monitoring architecture (Option 2) is **designed for horizontal scalability** from the start:
- Registry pattern allows multiple readers
- Consistent hashing enables deterministic partitioning
- Leader election handles Factory discovery coordination
- Event deduplication prevents duplicate processing

We'll start with **single instance + concurrency** and add horizontal scaling when escrow count or availability requirements demand it.
