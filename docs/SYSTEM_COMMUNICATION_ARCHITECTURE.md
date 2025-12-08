# Fusion Prime - System Communication Architecture

## Overview

Fusion Prime uses a **hybrid communication architecture** combining event-driven messaging (Pub/Sub) with synchronous REST APIs. This design ensures reliable, scalable, and observable communication between all system components.

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         BLOCKCHAIN LAYER                                  │
│  ┌─────────────────────┐                                                 │
│  │  Escrow Factory     │  Emits: EscrowDeployed, ApprovalGranted, etc.  │
│  │  Smart Contract     │                                                  │
│  └──────────┬──────────┘                                                 │
│             │ Event Logs                                                  │
└─────────────┼──────────────────────────────────────────────────────────┘
              │
              ↓ (Poll via Web3)
┌─────────────────────────────────────────────────────────────────────────┐
│                      EVENT PROCESSING LAYER                              │
│  ┌──────────────────┐                                                    │
│  │  Event Relayer   │  • Polls blockchain every ~30-60s                  │
│  │  (Cloud Run Job) │  • Captures contract events                        │
│  │                  │  • Transforms to settlement commands               │
│  └────────┬─────────┘  • Maintains checkpoint (last processed block)    │
│           │                                                               │
└───────────┼───────────────────────────────────────────────────────────────┘
            │
            ↓ (Publish)
┌───────────────────────────────────────────────────────────────────────────┐
│                       MESSAGE BUS LAYER                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                     Google Cloud Pub/Sub                             │ │
│  │                                                                      │ │
│  │  Topics:                                                             │ │
│  │  • escrow-events          (EscrowDeployed, ApprovalGranted, etc.)   │ │
│  │  • settlement-commands    (Settlement instructions)                 │ │
│  │  • risk-events            (Risk updates, margin calls)              │ │
│  │  • compliance-events      (KYC/AML alerts)                          │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│           │                 │                  │                           │
└───────────┼─────────────────┼──────────────────┼───────────────────────────┘
            │                 │                  │
            ↓                 ↓                  ↓
┌───────────────────────────────────────────────────────────────────────────┐
│                      APPLICATION SERVICES LAYER                            │
│                                                                            │
│  ┌──────────────────┐  ┌─────────────────┐  ┌──────────────────┐        │
│  │   Settlement     │  │   Risk Engine   │  │   Compliance     │        │
│  │    Service       │  │    Service      │  │    Service       │        │
│  │  (Cloud Run)     │  │  (Cloud Run)    │  │  (Cloud Run)     │        │
│  │                  │  │                 │  │                  │        │
│  │  • Pub/Sub Sub   │  │  • Pub/Sub Sub  │  │  • Pub/Sub Sub   │        │
│  │  • REST API      │  │  • REST API     │  │  • REST API      │        │
│  │  • Event Handler │  │  • Risk Engine  │  │  • KYC/AML Logic │        │
│  └────────┬─────────┘  └────────┬────────┘  └────────┬─────────┘        │
│           │                     │                     │                   │
│           └─────────────────────┼─────────────────────┘                   │
│                                 │                                         │
└─────────────────────────────────┼─────────────────────────────────────────┘
                                  │
                                  ↓ (SQL Queries/Writes)
┌───────────────────────────────────────────────────────────────────────────┐
│                         DATA PERSISTENCE LAYER                             │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                    Cloud SQL PostgreSQL                              │ │
│  │                                                                      │ │
│  │  Databases:                                                          │ │
│  │  • settlement_db     (Commands, workflows, escrow state)            │ │
│  │  • risk_db           (Portfolio positions, risk metrics)            │ │
│  │  • compliance_db     (KYC/AML records, checks)                      │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────┐
│                        OBSERVABILITY LAYER                                 │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │  Cloud Logging  │  Cloud Monitoring  │  Cloud Trace  │  Alerts      │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## Communication Patterns

### 1. Event-Driven Communication (Asynchronous)

**Purpose**: Decouple services, ensure reliability, enable fan-out

#### Pattern: Event Relayer → Pub/Sub → Services

```
Smart Contract Event
        ↓
Event Relayer (polls blockchain)
        ↓
Transform to Settlement Command
        ↓
Publish to Pub/Sub Topic
        ↓
        ├─→ Settlement Service (processes command)
        ├─→ Risk Engine (updates risk metrics)
        └─→ Compliance Service (validates transaction)
```

**Characteristics:**
- ✅ **Asynchronous**: Services process events at their own pace
- ✅ **Reliable**: Pub/Sub guarantees at-least-once delivery
- ✅ **Scalable**: Multiple subscribers can consume same event
- ✅ **Decoupled**: Services don't need to know about each other

**Example Flow (Escrow Creation):**

```python
# 1. Smart Contract emits event
event EscrowDeployed(
    address escrow,
    address payer,
    address payee,
    uint256 amount
)

# 2. Event Relayer captures and transforms
{
    "event_type": "EscrowDeployed",
    "escrow_address": "0xabc...",
    "payer": "0x123...",
    "payee": "0x456...",
    "amount": "1000000000000000000",  # 1 ETH
    "block_number": 12345,
    "transaction_hash": "0xdef..."
}

# 3. Published to Pub/Sub topic: "escrow-events"

# 4. Settlement Service receives and processes
async def handle_escrow_event(message):
    # Save to database
    await db.execute("""
        INSERT INTO settlement_commands (...)
        VALUES (...)
    """)

    # Trigger downstream services (optional)
    await risk_engine.calculate_portfolio_risk(...)
    await compliance.check_kyc_aml(...)
```

**Key Technologies:**
- **Google Cloud Pub/Sub**: Message broker
- **Push Subscriptions**: Pub/Sub pushes to service endpoints
- **Pull Subscriptions**: Services poll Pub/Sub (alternative)
- **Dead Letter Queues**: For failed message processing

---

### 2. Synchronous Communication (REST API)

**Purpose**: Direct service-to-service calls, client interactions, queries

#### Pattern: Service → REST API → Service

```
Settlement Service
        ↓ HTTP POST
Risk Engine Service /risk/portfolio
        ↓ JSON Response
Settlement Service (continues processing)
```

**Characteristics:**
- ✅ **Synchronous**: Immediate response required
- ✅ **Request/Response**: Clear input/output contract
- ✅ **Transactional**: Know result immediately
- ⚠️  **Coupled**: Caller depends on callee availability

**Example Flows:**

#### A. Settlement → Risk Engine
```python
# Settlement service calls Risk Engine for risk calculation
response = await http_client.post(
    f"{risk_engine_url}/risk/portfolio",
    json={
        "user_id": "user-123",
        "positions": [
            {"asset": "ETH", "amount": 1.5, "escrow_address": "0xabc..."}
        ]
    }
)

risk_data = response.json()
# {
#     "risk_score": 0.25,
#     "risk_level": "low",
#     "margin_available": 15000.0
# }
```

#### B. Settlement → Compliance
```python
# Settlement service calls Compliance for KYC/AML check
response = await http_client.post(
    f"{compliance_url}/compliance/check",
    json={
        "user_id": "user-123",
        "payer_address": "0x123...",
        "payee_address": "0x456...",
        "amount": "1.5",
        "asset": "ETH"
    }
)

compliance_result = response.json()
# {
#     "status": "approved",
#     "approved": true,
#     "checks": ["kyc_verified", "aml_clear"]
# }
```

**Key Technologies:**
- **FastAPI**: Python web framework
- **httpx/requests**: HTTP clients
- **Cloud Run**: Serverless HTTP endpoints
- **Cloud Endpoints/API Gateway**: API management (optional)

---

### 3. Database Communication (Persistence)

**Purpose**: Store state, query data, maintain consistency

#### Pattern: Service → Cloud SQL → Service

```
Settlement Service
        ↓ SQL INSERT
Cloud SQL PostgreSQL
        ↓ SQL SELECT
Settlement Service (query status)
```

**Characteristics:**
- ✅ **ACID Transactions**: Guaranteed consistency
- ✅ **Relational**: Complex queries, joins
- ✅ **Persistent**: Survives service restarts
- ⚠️  **Shared State**: Requires coordination

**Example Operations:**

#### Write (Command Ingestion)
```python
# Settlement service writes command to database
async with db.transaction():
    await db.execute("""
        INSERT INTO settlement_commands (
            command_id, workflow_id, account_ref,
            asset_symbol, amount, payer, payee,
            status, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
    """, command_id, workflow_id, account_ref, ...)
```

#### Read (Status Query)
```python
# Query command status
command = await db.fetch_one("""
    SELECT command_id, status, created_at, updated_at
    FROM settlement_commands
    WHERE command_id = $1
""", command_id)
```

**Key Technologies:**
- **Cloud SQL PostgreSQL**: Managed relational database
- **SQLAlchemy**: Python ORM (Object-Relational Mapping)
- **asyncpg**: Async PostgreSQL driver
- **Alembic**: Database migration tool

---

## Communication Protocols by Layer

### Blockchain → Event Relayer
- **Protocol**: Web3 RPC (JSON-RPC over HTTP/WebSocket)
- **Method**: Polling (`eth_getLogs`, `eth_getBlockNumber`)
- **Frequency**: Every 30-60 seconds
- **Data Format**: Event logs (topics, data, blockNumber, transactionHash)

### Event Relayer → Pub/Sub
- **Protocol**: gRPC (Google Pub/Sub API)
- **Method**: `publish(topic, data, attributes)`
- **Frequency**: After processing each block
- **Data Format**: JSON messages with event data

### Pub/Sub → Services
- **Protocol**: HTTP/2 (Push subscription) or gRPC (Pull subscription)
- **Method**: POST to service endpoint or `pull()` from client
- **Frequency**: Real-time (as messages arrive)
- **Data Format**: JSON payload in HTTP body

### Service → Service (REST)
- **Protocol**: HTTP/1.1 or HTTP/2
- **Method**: GET, POST, PUT, DELETE
- **Authentication**: Cloud IAM, Service Account tokens
- **Data Format**: JSON request/response bodies

### Service → Database
- **Protocol**: PostgreSQL Wire Protocol (over TCP)
- **Method**: SQL queries via connection pool
- **Authentication**: Database user/password (from Secret Manager)
- **Connection**: Cloud SQL Auth Proxy (Unix socket or TCP)

---

## Security & Authentication

### Service-to-Service Authentication

#### 1. Cloud Run to Cloud Run
```python
# Get service account token
import google.auth.transport.requests
import google.oauth2.id_token

auth_req = google.auth.transport.requests.Request()
target_audience = "https://risk-engine-service-HASH-uc.a.run.app"
token = google.oauth2.id_token.fetch_id_token(auth_req, target_audience)

# Make authenticated request
headers = {"Authorization": f"Bearer {token}"}
response = requests.post(risk_engine_url, headers=headers, json=data)
```

#### 2. Service to Database
```python
# Connection string with Cloud SQL Auth Proxy
DATABASE_URL = (
    "postgresql+asyncpg://settlement_user:PASSWORD@"
    "/cloudsql/fusion-prime:us-central1:settlement-db/settlement"
)

# Password retrieved from Secret Manager
from google.cloud import secretmanager
client = secretmanager.SecretManagerServiceClient()
secret_name = "projects/PROJECT_ID/secrets/settlement-db-password/versions/latest"
password = client.access_secret_version(name=secret_name).payload.data.decode()
```

#### 3. Service to Pub/Sub
```python
# Service account with pubsub.publisher role
from google.cloud import pubsub_v1

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(project_id, topic_name)

# Automatically authenticated via Application Default Credentials
future = publisher.publish(topic_path, data, **attributes)
```

---

## Error Handling & Retry Strategies

### Pub/Sub Message Processing

**Retry Policy:**
```yaml
Subscription: escrow-events-settlement
  ackDeadline: 60s                    # Time to process message
  retryPolicy:
    minimumBackoff: 10s               # Initial retry delay
    maximumBackoff: 600s              # Max retry delay
  deadLetterPolicy:
    deadLetterTopic: escrow-events-dlq
    maxDeliveryAttempts: 5            # Move to DLQ after 5 failures
```

**Handler Pattern:**
```python
async def handle_message(message):
    try:
        # Process message
        await process_escrow_event(message.data)

        # Acknowledge success
        message.ack()

    except RetryableError as e:
        # Don't ack - Pub/Sub will retry
        logger.warning(f"Retryable error: {e}")
        message.nack()

    except FatalError as e:
        # Ack to avoid infinite retries
        logger.error(f"Fatal error: {e}")
        message.ack()
        await send_alert(e)
```

### REST API Calls

**Retry with Exponential Backoff:**
```python
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10)
)
async def call_risk_engine(data):
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(risk_engine_url, json=data)
        response.raise_for_status()
        return response.json()
```

**Circuit Breaker Pattern:**
```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
async def call_compliance_service(data):
    # Circuit opens after 5 failures
    # Recovers after 60 seconds
    response = await http_client.post(compliance_url, json=data)
    return response.json()
```

---

## Observability & Monitoring

### Structured Logging

**All services emit structured logs:**
```python
import structlog

logger = structlog.get_logger()

# Event processing log
logger.info(
    "escrow_event_processed",
    event_id="evt-123",
    escrow_address="0xabc...",
    block_number=12345,
    processing_time_ms=150
)

# Error log
logger.error(
    "risk_calculation_failed",
    user_id="user-123",
    error_type="TimeoutError",
    retry_count=2
)
```

**Logs flow to Cloud Logging:**
- Automatic log collection from Cloud Run
- Log-based metrics and alerts
- Log correlation via trace IDs

### Distributed Tracing

**Trace propagation across services:**
```python
from opentelemetry import trace
from opentelemetry.propagate import inject

tracer = trace.get_tracer(__name__)

# Start span
with tracer.start_as_current_span("settlement_command_processing") as span:
    span.set_attribute("command_id", command_id)

    # Propagate trace context to downstream service
    headers = {}
    inject(headers)

    response = await http_client.post(
        risk_engine_url,
        json=data,
        headers=headers  # Includes trace context
    )
```

### Metrics & SLOs

**Key metrics tracked:**
- **Pub/Sub**: Message publish rate, delivery latency, error rate
- **Services**: Request rate, response time (p50/p95/p99), error rate
- **Database**: Connection pool usage, query latency, deadlocks

**Example SLO:**
```yaml
Service: settlement-service
SLO: 99.9% of requests succeed within 500ms

Metrics:
  - request_count{status="success"}
  - request_duration_ms{le="500"}

Alert:
  - Error budget burn rate > 10x
  - Trigger: Page DevOps team
```

---

## Data Flow Examples

### Complete Escrow Creation Flow

**Step-by-step communication:**

```
1. USER TRANSACTION
   User → Blockchain: Execute createEscrow(payee, amount)
   Blockchain → User: Transaction receipt + events

2. EVENT CAPTURE
   Event Relayer → Blockchain: eth_getLogs(factoryAddress, fromBlock, toBlock)
   Blockchain → Event Relayer: [EscrowDeployed event]

3. EVENT PUBLISHING
   Event Relayer → Pub/Sub: publish("escrow-events", event_data)
   Pub/Sub → Event Relayer: message_id

4. EVENT DISTRIBUTION
   Pub/Sub → Settlement Service: POST /pubsub/escrow-events (push)
   Pub/Sub → Risk Engine: POST /pubsub/escrow-events (push)
   Pub/Sub → Compliance: POST /pubsub/escrow-events (push)

5. SETTLEMENT PROCESSING
   Settlement Service → Cloud SQL: INSERT INTO settlement_commands(...)
   Cloud SQL → Settlement Service: command_id

6. RISK CALCULATION
   Settlement Service → Risk Engine: POST /risk/portfolio
   Risk Engine → Settlement Service: {risk_score: 0.25, risk_level: "low"}
   Risk Engine → Cloud SQL: UPDATE risk_metrics SET ...

7. COMPLIANCE CHECK
   Settlement Service → Compliance: POST /compliance/check
   Compliance → Settlement Service: {status: "approved", approved: true}
   Compliance → Cloud SQL: INSERT INTO compliance_checks(...)

8. STATUS UPDATE
   Settlement Service → Cloud SQL: UPDATE settlement_commands SET status='processed'

9. CLIENT QUERY (later)
   Client → Settlement Service: GET /commands/{command_id}/status
   Settlement Service → Cloud SQL: SELECT * FROM settlement_commands WHERE...
   Settlement Service → Client: {command_id, status, created_at, ...}
```

**Total time**: ~60-90 seconds (includes 45s relayer polling interval)

---

## Communication Best Practices

### 1. Idempotency

**All message handlers must be idempotent:**
```python
async def handle_escrow_event(message):
    event_id = message.attributes.get("event_id")

    # Check if already processed
    existing = await db.fetch_one(
        "SELECT 1 FROM processed_events WHERE event_id = $1",
        event_id
    )

    if existing:
        logger.info("event_already_processed", event_id=event_id)
        message.ack()  # Ack duplicate
        return

    # Process event
    await process_event(message.data)

    # Mark as processed
    await db.execute(
        "INSERT INTO processed_events (event_id, processed_at) VALUES ($1, NOW())",
        event_id
    )

    message.ack()
```

### 2. Timeout Configuration

**Set appropriate timeouts at each layer:**
```python
# HTTP client timeout
async with httpx.AsyncClient(timeout=10.0) as client:
    response = await client.post(url, json=data)

# Database query timeout
await db.execute("SET statement_timeout = '5s'")
result = await db.fetch("SELECT ...")

# Pub/Sub ack deadline
subscription.update(ack_deadline_seconds=60)
```

### 3. Graceful Degradation

**Handle service unavailability gracefully:**
```python
async def process_with_fallback():
    try:
        # Try Risk Engine
        risk = await risk_engine.calculate(data)
    except Exception as e:
        logger.warning("risk_engine_unavailable", error=str(e))
        # Use default risk score
        risk = {"risk_score": 0.5, "risk_level": "medium"}

    # Continue processing with fallback data
    return risk
```

### 4. Circuit Breaking

**Prevent cascading failures:**
```python
# After 5 failures, stop trying for 60 seconds
@circuit(failure_threshold=5, recovery_timeout=60)
async def call_external_service():
    # If circuit is open, raises CircuitBreakerError immediately
    # If circuit is closed, tries request
    return await make_request()
```

---

## Testing Communication Patterns

### Unit Tests: Mock External Services
```python
@pytest.mark.asyncio
async def test_settlement_command_processing(mocker):
    # Mock Risk Engine
    mock_risk = mocker.patch("services.risk_engine.calculate_portfolio_risk")
    mock_risk.return_value = {"risk_score": 0.25}

    # Mock Compliance
    mock_compliance = mocker.patch("services.compliance.check_kyc_aml")
    mock_compliance.return_value = {"approved": True}

    # Test settlement processing
    result = await settlement_service.process_command(command_data)

    assert result["status"] == "processed"
    mock_risk.assert_called_once()
    mock_compliance.assert_called_once()
```

### Integration Tests: Real Services
```python
async def test_end_to_end_workflow():
    # Ingest command (Settlement Service)
    response = await client.post(
        f"{settlement_url}/commands/ingest",
        json=command_data
    )
    assert response.status_code == 200

    # Verify database write
    command = await db.fetch_one(
        "SELECT * FROM settlement_commands WHERE command_id = $1",
        command_id
    )
    assert command is not None

    # Verify Risk Engine was called
    risk_response = await client.post(
        f"{risk_engine_url}/risk/portfolio",
        json=portfolio_data
    )
    assert risk_response.status_code == 200
```

---

## Related Documentation

- **[TESTING.md](../TESTING.md)**: Testing strategy
- **[SMART_CONTRACT_EVENT_TESTING.md](./SMART_CONTRACT_EVENT_TESTING.md)**: Event-driven testing
- **[DATABASE_SETUP.md](../DATABASE_SETUP.md)**: Database configuration
- **[TEST_STRUCTURE.md](../tests/remote/testnet/TEST_STRUCTURE.md)**: Test organization

---

**Last Updated**: October 25, 2025
**Maintained By**: Backend Microservices Agent, DevOps & SecOps Agent
**Status**: Active - Core communication architecture
