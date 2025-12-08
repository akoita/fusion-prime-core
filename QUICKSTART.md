# 🚀 Fusion Prime - Local Development Guide

**Complete guide for deploying and testing Fusion Prime locally**

> **📖 Deploying to Test or Production?** See **[DEPLOYMENT.md](./DEPLOYMENT.md)** for testnet and mainnet deployment guides.

**Golden Rule**: Always validate locally before deploying to remote environments.

```
LOCAL (Free, Fast) → TEST (Cheap, Slow) → PRODUCTION (Expensive, Real)
      ↓                   ↓                        ↓
   Anvil             Sepolia/Amoy            Ethereum/Polygon
   Docker              GCP Dev                  GCP Prod
```

Two ways to use this guide:
- **🏃 Quick Start**: Follow the main path (30 minutes) to get everything running
- **📚 Deep Dive**: Jump to specific sections for detailed information and debugging

---

## 🎯 Why Local-First Development?

✅ **Fast**: Instant block times, no network latency
✅ **Free**: No gas costs, unlimited transactions
✅ **Reproducible**: Reset state anytime
✅ **Debuggable**: Full access to logs, state, traces
✅ **Isolated**: No external dependencies

**Cost Comparison**:
- 100 local tests: **$0**, 10 seconds
- 100 testnet tests: **$0** (but slow), 20+ minutes
- 100 mainnet tests: **$$$$**, 20+ minutes

**Do 99% of testing locally!**

---

## Table of Contents

- [Prerequisites](#prerequisites-5-minutes)
- [Quick Start (30 min)](#quick-start-30-minutes)
  - [Part 1: Local Blockchain](#part-1-local-blockchain-5-minutes)
  - [Part 2: Smart Contracts](#part-2-deploy-smart-contracts-5-minutes)
  - [Part 3: Backend Services](#part-3-start-backend-services-5-minutes)
  - [Part 4: Test Contracts](#part-4-test-smart-contracts-5-minutes)
  - [Part 5: Test Backend](#part-5-test-backend-services-5-minutes)
  - [Part 6: End-to-End](#part-6-end-to-end-test-5-minutes)
  - [Part 7: Modular Integration Testing](#part-7-modular-integration-testing-5-minutes)
  - [Part 8: Comprehensive Relayer-Backend Verification](#part-8-comprehensive-relayer-backend-verification-3-minutes)
- [Reference Sections](#reference-sections)
  - [Service Architecture](#service-architecture)
  - [Pub/Sub Emulator](#pubsub-emulator-guide)
  - [Database Management](#database-management)
  - [Smart Contract Development](#smart-contract-development)
  - [TypeScript SDK](#typescript-sdk-development)
  - [Debugging](#debugging)
  - [Performance Tips](#performance-tips)
- [Troubleshooting](#troubleshooting)
- [Next Steps](#next-steps)

---

## Prerequisites (5 minutes)

### Required Tools

```bash
# Check if tools are installed
command -v forge >/dev/null && echo "✓ Foundry" || echo "✗ Missing: curl -L https://foundry.paradigm.xyz | bash"
command -v docker >/dev/null && echo "✓ Docker" || echo "✗ Missing: https://docs.docker.com/get-docker/"
command -v gcloud >/dev/null && echo "✓ gcloud" || echo "✗ Missing: https://cloud.google.com/sdk"
command -v pnpm >/dev/null && echo "✓ pnpm" || echo "✗ Missing: npm install -g pnpm"
command -v poetry >/dev/null && echo "✓ Poetry" || echo "✗ Missing: curl -sSL https://install.python-poetry.org | python3 -"
command -v jq >/dev/null && echo "✓ jq" || echo "✗ Missing: apt/brew install jq"
```

**Versions**:
- Docker & Docker Compose v2.0+
- Python 3.13+
- Node.js 20+
- Foundry (latest)

### Clone and Setup

```bash
# Clone repository
git clone https://github.com/akoita/fusion-prime.git
cd fusion-prime

# Run bootstrap script (installs missing tools)
./scripts/bootstrap.sh
```

---

## Quick Start (30 minutes)

### Part 1: Local Blockchain (5 minutes)

#### Step 1.1: Start Anvil

```bash
# Start Anvil (local Ethereum node)
docker compose up -d anvil

# Verify it's running
curl -X POST http://localhost:8545 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# Should return: {"jsonrpc":"2.0","id":1,"result":"0x0"}
```

**Anvil Details**:
- **RPC URL**: `http://localhost:8545`
- **Chain ID**: `31337`
- **Pre-funded accounts**: 10 (each with 10,000 ETH)
- **Block time**: Instant (mines on transaction)

#### Step 1.2: Get Test Account

```bash
# Anvil provides 10 pre-funded accounts
# Account #0 (default deployer):
export PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
export ANVIL_ADDRESS=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266

# Verify balance (should have 10,000 ETH)
cast balance $ANVIL_ADDRESS --rpc-url http://localhost:8545
```

---

### Part 2: Deploy Smart Contracts (5 minutes)

#### Step 2.1: Deploy to Anvil

```bash
cd contracts

       # Install dependencies (first time only)
       forge install foundry-rs/forge-std
       forge install OpenZeppelin/openzeppelin-contracts-upgradeable

# Deploy EscrowFactory
# Note: The script reads PRIVATE_KEY from environment
# (From project root. If you see "No such file or directory", ensure you are in the correct folder and contracts are built)
forge script script/DeployMultichain.s.sol:DeployMultichain \
  --rpc-url http://localhost:8545 \
  --broadcast \
  -vvv

# Save deployment addresses
export LOCAL_ESCROW_FACTORY=$(jq -r '.transactions[] | select(.contractName=="EscrowFactory") | .contractAddress' broadcast/DeployMultichain.s.sol/31337/run-latest.json | head -1)

echo "Deployed contracts:"
echo "  EscrowFactory: $LOCAL_ESCROW_FACTORY"

cd ..
```

#### Step 2.2: Verify Deployment

```bash
# Check factory deployment
cast code $LOCAL_ESCROW_FACTORY --rpc-url http://localhost:8545

# Get escrow count (should be 0 initially)
cast call $LOCAL_ESCROW_FACTORY "getEscrowCount()(uint256)" --rpc-url http://localhost:8545
# Should return: 0
```

---

### Part 3: Start Backend Services (5 minutes)

#### Step 3.1: Start All Services

```bash
# Start Pub/Sub emulator, PostgreSQL, Redis, Anvil
docker compose up -d

# Wait for services to be healthy (30 seconds)
sleep 30

# Check status
docker compose ps

# Should see all services as "Up (healthy)"
```

#### Step 3.2: Initialize Pub/Sub

```bash
# Set emulator environment
export PUBSUB_EMULATOR_HOST=localhost:8085
export GCP_PROJECT=fusion-prime-local

# Initialize topics and subscriptions
./scripts/init-pubsub-emulator.sh

# Verify topics (using REST API since gcloud doesn't work with emulator)
curl -s "http://localhost:8085/v1/projects/fusion-prime-local/topics" | jq -r '.topics[].name' | sed 's|.*/||'

# Should see:
#   settlement.events.v1
#   risk.calculations.v1
#   compliance.events.v1

# Verify subscriptions
curl -s "http://localhost:8085/v1/projects/fusion-prime-local/subscriptions" | jq -r '.subscriptions[].name' | sed 's|.*/||'

# Should see:
#   settlement-events-consumer
#   risk-analytics-consumer
#   compliance-monitor-consumer
```

#### Step 3.3: Setup Database

```bash
cd services/settlement

# Install dependencies
poetry install

# Run migrations
docker exec -i fusion-prime-postgres psql -U fusion_prime -d fusion_prime < \
  infrastructure/migrations/001_create_settlement_commands.sql

docker exec -i fusion-prime-postgres psql -U fusion_prime -d fusion_prime < \
  infrastructure/migrations/002_create_webhook_subscriptions.sql

# Verify tables
docker exec fusion-prime-postgres psql -U fusion_prime -d fusion_prime -c "\dt"

cd ../..
```

---

### Part 4: Setup Event Relayer (3 minutes)

The Event Relayer monitors blockchain events and publishes them to Pub/Sub for the Settlement Service to process.

#### Step 4.1: Start Event Relayer

```bash
# Use the automated setup script
./scripts/setup-local-relayer.sh

# Or manually:
# 1. Deploy contracts first (if not already done)
cd contracts
forge script script/DeployMultichain.s.sol:DeployMultichain \
  --rpc-url http://localhost:8545 \
  --broadcast \
  --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80

# 2. Get the deployed contract address
ESCROW_FACTORY=$(jq -r '.transactions[0].contractAddress' broadcast/DeployMultichain.s.sol/31337/run-latest.json)
echo "Escrow Factory: $ESCROW_FACTORY"

# 3. Update Docker Compose with contract address
sed -i "s/CONTRACT_ADDRESS: \"0x_UPDATE_AFTER_DEPLOY\"/CONTRACT_ADDRESS: \"$ESCROW_FACTORY\"/" docker-compose.yml

# 4. Start the relayer
docker compose up -d event-relayer

cd ..
```

#### Step 4.2: Verify Relayer is Running

```bash
# Check relayer status
docker compose ps event-relayer

# View relayer logs
docker compose logs -f event-relayer

# Should see logs like:
# [INFO] Starting Fusion Prime Escrow Event Relayer (Production)
# [INFO] Configuration:
# [INFO]   Chain ID: 31337
# [INFO]   RPC URL: http://anvil:8545
# [INFO]   Contract: 0x...
# [INFO]   Events: EscrowCreated,EscrowReleased,EscrowRefunded,Approval
```

#### Step 4.3: Test Event Monitoring

```bash
# Create a test escrow to generate events
cd contracts

# Get the factory address
ESCROW_FACTORY=$(jq -r '.transactions[0].contractAddress' broadcast/DeployMultichain.s.sol/31337/run-latest.json)

# Create an escrow
cast send $ESCROW_FACTORY \
  "createEscrow(address,uint256,uint8,address)" \
  0x70997970C51812dc3A010C7d01b50e0d17dc79C8 \
  3600 \
  2 \
  0x0000000000000000000000000000000000000000 \
  --rpc-url http://localhost:8545 \
  --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
  --value $(cast --to-wei 0.01)

cd ..

# Check if the relayer detected the event
docker compose logs --tail=10 event-relayer

# Should see:
# [INFO] Processed event EscrowDeployed at block X, tx 0x...
# [INFO] Published event to Pub/Sub, message_id=...

# Verify relayer-backend communication
echo "=== Verifying Relayer-Backend Communication ==="

# 1. Check if events are being published to Pub/Sub
echo "1. Checking Pub/Sub messages..."
export PUBSUB_EMULATOR_HOST=localhost:8085
gcloud pubsub subscriptions pull settlement-events-consumer \
  --limit=5 \
  --auto-ack

# 2. Check settlement service logs for event processing
echo "2. Checking settlement service logs..."
docker compose logs --tail=20 settlement-service | grep -i "escrow\|event\|command"

# 3. Verify database has processed events
echo "3. Checking database for processed events..."
docker exec fusion-prime-postgres psql -U fusion_prime -d fusion_prime \
  -c "SELECT command_id, status, workflow_id, account_ref, amount_numeric, payer, payee, last_updated FROM settlement_commands ORDER BY last_updated DESC LIMIT 5;"

echo "=== Verification Complete ==="
```

---

### Part 5: Test Smart Contracts (5 minutes)

#### Step 4.1: Create Test Escrow

```bash
# Test accounts and parameters
PAYER=$ANVIL_ADDRESS  # Account #0
PAYEE=0x70997970C51812dc3A010C7d01b50e0d17dc79C8  # Account #1
RELEASE_DELAY=3600  # 1 hour in seconds
REQUIRED_APPROVALS=2
ARBITER=0x0000000000000000000000000000000000000000  # Optional arbiter (zero address = none)

# Create escrow and capture transaction hash
# Function signature: createEscrow(address payee, uint256 releaseDelay, uint8 approvalsRequired, address arbiter)
export TEST_ESCROW_TX=$(cast send $LOCAL_ESCROW_FACTORY \
  "createEscrow(address,uint256,uint8,address)" \
  $PAYEE \
  $RELEASE_DELAY \
  $REQUIRED_APPROVALS \
  $ARBITER \
  --rpc-url http://localhost:8545 \
  --private-key $PRIVATE_KEY \
  --value 1ether \
  --json | jq -r '.transactionHash')

echo "Transaction: $TEST_ESCROW_TX"

# Extract escrow address from event logs (EscrowDeployed event, first indexed topic is the escrow address)
export TEST_ESCROW_ADDRESS=$(cast receipt $TEST_ESCROW_TX --rpc-url http://localhost:8545 --json | jq -r '.logs[1].topics[1]' | sed 's/0x000000000000000000000000/0x/')

echo "Created escrow at: $TEST_ESCROW_ADDRESS"
```

#### Step 4.2: Test Escrow Functions

```bash
# Check escrow balance
cast balance $TEST_ESCROW_ADDRESS --rpc-url http://localhost:8545
# Should be 1 ETH

# Approve as payer
cast send $TEST_ESCROW_ADDRESS \
  "approve()" \
  --rpc-url http://localhost:8545 \
  --private-key $PRIVATE_KEY

# Check approval status
cast call $TEST_ESCROW_ADDRESS \
  "approvals(address)(bool)" \
  $PAYER \
  --rpc-url http://localhost:8545

# Should return: true
```

---

### Part 5: Test Backend Services (5 minutes)

#### Step 5.1: Test Settlement Service API

```bash
# Health check
curl http://localhost:8000/health | jq

# Should return: {"status":"ok"}

# Ingest test command
curl -X POST http://localhost:8000/commands/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "command_id": "test-local-001",
    "payer": "'$PAYER'",
    "payee": "'$PAYEE'",
    "amount": "1000000000000000000",
    "chain_id": 31337
  }' | jq

# Should return: 202 Accepted

# Query command status
curl http://localhost:8000/commands/test-local-001 | jq
```

#### Step 5.2: Test Pub/Sub Flow

```bash
# Note: gcloud publish/pull commands work with emulator when PUBSUB_EMULATOR_HOST is set
export PUBSUB_EMULATOR_HOST=localhost:8085

# Publish test event
gcloud pubsub topics publish settlement.events.v1 \
  --message '{"command_id":"test-local-001","event_type":"EscrowCreated"}' \
  --attribute event_type=EscrowCreated,chain_id=31337

# Pull from subscription
gcloud pubsub subscriptions pull settlement-events-consumer \
  --limit=1 \
  --auto-ack

# Should see the published message in a table format
```

#### Step 5.3: Check Database

```bash
# Query settlement commands
docker exec fusion-prime-postgres psql -U fusion_prime -d fusion_prime \
  -c "SELECT command_id, status, workflow_id, account_ref, amount_numeric, payer, payee FROM settlement_commands WHERE command_id='test-local-001';"

# Should see the ingested command
```

---

### Part 6: End-to-End Test (5 minutes)

```bash
# Complete flow: Contract → API → Database
echo "1. Creating escrow..."
TX=$(cast send $LOCAL_ESCROW_FACTORY \
  "createEscrow(address,uint256,uint8,address)" \
  $PAYEE 3600 2 $ARBITER \
  --rpc-url http://localhost:8545 \
  --private-key $PRIVATE_KEY \
  --value 0.5ether \
  --json | jq -r '.transactionHash')

echo "Transaction: $TX"

# Extract escrow address from EscrowDeployed event
ESCROW_ADDR=$(cast receipt $TX --rpc-url http://localhost:8545 --json | jq -r '.logs[1].topics[1]' | sed 's/0x000000000000000000000000/0x/')
echo "Escrow address: $ESCROW_ADDR"

# Ingest command via API
echo "2. Ingesting command..."
curl -s -X POST http://localhost:8000/commands/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "command_id": "e2e-test-'$(date +%s)'",
    "payer": "'$PAYER'",
    "payee": "'$PAYEE'",
    "amount": "500000000000000000",
    "chain_id": 31337
  }' | jq

# Verify in database
echo "3. Checking database..."
sleep 2
docker exec fusion-prime-postgres psql -U fusion_prime -d fusion_prime \
  -c "SELECT COUNT(*) FROM settlement_commands;" -t

echo "✓ End-to-end test complete!"
```

---

### Part 7: Domain-Driven Integration Testing (5 minutes)

The new domain-driven integration test suite provides isolated testing of each business domain with real infrastructure.

#### Step 7.1: Run Domain-Driven Integration Tests

```bash
# Test individual business domains
echo "=== Domain-Driven Integration Testing ==="

# 1. Risk & Analytics Domain Tests
echo "1. Testing Risk & Analytics domain..."
python tests/local/run_domain_tests.py risk -v

# 2. Compliance & Identity Domain Tests
echo "2. Testing Compliance & Identity domain..."
python tests/local/run_domain_tests.py compliance -v

# 3. Settlement Domain Tests
echo "3. Testing Settlement domain..."
python tests/local/run_domain_tests.py settlement -v

# 4. Infrastructure Component Tests
echo "4. Testing Infrastructure components..."
python tests/local/run_domain_tests.py infrastructure -v

# 5. End-to-End Cross-Domain Tests
echo "5. Testing cross-domain workflows..."
python -m pytest tests/local/test_e2e.py -v

# 6. Run All Domain Tests
echo "6. Running all domain tests..."
python tests/local/run_domain_tests.py all -v
```

#### Step 7.2: Using the Unified Test Script

```bash
# Alternative: Use the unified test script for domain-driven tests
echo "=== Using Unified Test Script ==="

# Individual domain tests
./scripts/test.sh contracts               # Smart contract tests
./scripts/test.sh backend                 # Backend service tests
./scripts/test.sh integration             # Integration tests
./scripts/test.sh e2e                     # End-to-end tests

# Or run all local tests at once
./scripts/test.sh local

# For remote testing
python tests/scripts/run_remote_tests.py testnet
python tests/scripts/run_remote_tests.py production
```

---

### Part 8: Comprehensive Relayer-Backend Verification (3 minutes)

This section verifies that the event relayer is properly communicating with backend services.

#### Step 7.1: Verify Event Flow

```bash
echo "=== Comprehensive Relayer-Backend Verification ==="

# 1. Check relayer is processing events
echo "1. Checking relayer event processing..."
docker compose logs --tail=10 event-relayer | grep -E "(Processed event|Published event)"

# 2. Verify Pub/Sub message flow
echo "2. Checking Pub/Sub message flow..."
export PUBSUB_EMULATOR_HOST=localhost:8085

# Check if messages are in the topic
echo "Messages in settlement.events.v1:"
gcloud pubsub subscriptions pull settlement-events-consumer \
  --limit=3 \
  --auto-ack

# 3. Check settlement service is consuming messages
echo "3. Checking settlement service consumption..."
docker compose logs --tail=20 settlement-service | grep -E "(Received|Processing|Command)" || echo "No recent settlement service activity"

# 4. Verify database persistence
echo "4. Checking database persistence..."
docker exec fusion-prime-postgres psql -U fusion_prime -d fusion_prime \
  -c "SELECT
    command_id,
    status,
    workflow_id,
    account_ref,
    amount_numeric,
    payer,
    payee,
    last_updated
  FROM settlement_commands
  ORDER BY last_updated DESC
  LIMIT 5;"

# 5. Check for any errors
echo "5. Checking for errors..."
echo "Relayer errors:"
docker compose logs event-relayer | grep -i error | tail -5 || echo "No relayer errors"

echo "Settlement service errors:"
docker compose logs settlement-service | grep -i error | tail -5 || echo "No settlement service errors"

echo "=== Verification Complete ==="
```

#### Step 7.2: Test Real-Time Event Processing

```bash
# Create a new escrow and watch real-time processing
echo "=== Real-Time Event Processing Test ==="

# Start monitoring logs in background
docker compose logs -f event-relayer &
RELAYER_PID=$!

# Create escrow
cd contracts
cast send $ESCROW_FACTORY \
  "createEscrow(address,uint256,uint8,address)" \
  0x70997970C51812dc3A010C7d01b50e0d17dc79C8 \
  3600 \
  2 \
  0x0000000000000000000000000000000000000000 \
  --rpc-url http://localhost:8545 \
  --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
  --value $(cast --to-wei 0.01)

cd ..

# Wait for processing
sleep 5

# Stop monitoring
kill $RELAYER_PID

echo "✓ Real-time processing test complete!"
```

---

## ✅ Quick Start Complete!

You now have:
- ✅ Anvil blockchain running locally
- ✅ Smart contracts deployed
- ✅ Backend services running (Pub/Sub, PostgreSQL, Redis)
- ✅ End-to-end flow tested

**Next**: Run the universal test suite:
```bash
./scripts/test.sh local
```

See [TESTING.md](TESTING.md) for complete testing guide.

---

## Reference Sections

### Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose Stack                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐      ┌──────────────────┐            │
│  │  Pub/Sub         │      │  PostgreSQL      │            │
│  │  Emulator        │      │  Database        │            │
│  │  :8085           │      │  :5432           │            │
│  └──────────────────┘      └──────────────────┘            │
│           │                          │                       │
│           │                          │                       │
│  ┌──────────────────┐      ┌──────────────────┐            │
│  │  Redis           │      │  Anvil           │            │
│  │  Cache           │      │  Local ETH Node  │            │
│  │  :6379           │      │  :8545           │            │
│  └──────────────────┘      └──────────────────┘            │
│           │                          │                       │
│           └──────────┬───────────────┘                       │
│                      │                                       │
│           ┌──────────▼──────────┐                           │
│           │  Settlement Service │                           │
│           │  FastAPI :8000      │                           │
│           └─────────────────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

**Service URLs**:

| Service | URL | Credentials |
|---------|-----|-------------|
| Anvil RPC | http://localhost:8545 | - |
| Settlement API | http://localhost:8000 | - |
| Pub/Sub Emulator | http://localhost:8085 | - |
| PostgreSQL | localhost:5432 | user: `fusion_prime`, pass: `fusion_prime_dev_pass` |
| Redis | localhost:6379 | - |

---

### Pub/Sub Emulator Guide

#### Features

- ✅ Full Pub/Sub API compatibility
- ✅ Topics and subscriptions
- ✅ Message publishing and consuming
- ✅ Pull and push subscriptions
- ✅ Message retention and retry policies
- ✅ No authentication required

#### Configuration

The emulator is configured via environment variable:

```bash
export PUBSUB_EMULATOR_HOST=localhost:8085
```

When this variable is set, the `google-cloud-pubsub` client automatically connects to the emulator instead of production.

**Important**: `gcloud` commands have mixed support:
- ✅ **Works**: `gcloud pubsub topics publish` and `gcloud pubsub subscriptions pull`
- ❌ **Doesn't work**: `gcloud pubsub topics list` and `gcloud pubsub subscriptions list` (use curl instead)

#### Topics and Subscriptions

Automatically created by `init-pubsub-emulator.sh`:

| Topic | Subscription | Purpose |
|-------|--------------|---------|
| `settlement.events.v1` | `settlement-events-consumer` | Settlement command processing |
| `risk.calculations.v1` | `risk-analytics-consumer` | Risk analytics and margin calls |
| `compliance.events.v1` | `compliance-monitor-consumer` | KYC/AML monitoring and reporting |

#### Manual Management

**Using REST API (curl):**

```bash
# List topics
curl -s http://localhost:8085/v1/projects/fusion-prime-local/topics | jq

# List subscriptions
curl -s http://localhost:8085/v1/projects/fusion-prime-local/subscriptions | jq

# Create a topic
curl -X PUT http://localhost:8085/v1/projects/fusion-prime-local/topics/my-topic

# Create a subscription
curl -X PUT http://localhost:8085/v1/projects/fusion-prime-local/subscriptions/my-sub \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "projects/fusion-prime-local/topics/my-topic",
    "ackDeadlineSeconds": 60
  }'

# Publish a message (REST API)
curl -X POST http://localhost:8085/v1/projects/fusion-prime-local/topics/my-topic:publish \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{
      "data": "SGVsbG8gV29ybGQh",
      "attributes": {"key": "value"}
    }]
  }'
```

**Using gcloud CLI (publish/pull only):**

```bash
# Set emulator host
export PUBSUB_EMULATOR_HOST=localhost:8085

# Publish a message
gcloud pubsub topics publish my-topic \
  --message '{"test":"data"}' \
  --attribute key=value

# Pull messages
gcloud pubsub subscriptions pull my-sub \
  --limit=5 \
  --auto-ack
```

---

### Database Management

#### Connect to PostgreSQL

```bash
# Connect to database
docker exec -it fusion-prime-postgres psql -U fusion_prime -d fusion_prime

# Common commands:
# \dt                        - List tables
# \d settlement_commands     - Describe table schema
# SELECT * FROM settlement_commands;  - Query all records
# \q                         - Quit
```

#### Run Migrations

```bash
cd services/settlement

# Run SQL migrations manually
docker exec -i fusion-prime-postgres psql -U fusion_prime -d fusion_prime < \
  infrastructure/migrations/001_create_settlement_commands.sql

docker exec -i fusion-prime-postgres psql -U fusion_prime -d fusion_prime < \
  infrastructure/migrations/002_create_webhook_subscriptions.sql
```

#### Database Schema

**settlement_commands** table:
```sql
CREATE TABLE settlement_commands (
    command_id VARCHAR(128) PRIMARY KEY,
    workflow_id VARCHAR(128) NOT NULL,
    account_ref VARCHAR(128) NOT NULL,
    payer VARCHAR(128),
    payee VARCHAR(128),
    asset_symbol VARCHAR(64),
    amount_numeric NUMERIC(38, 18),
    status VARCHAR(32) NOT NULL,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Note**: The actual table uses `last_updated` instead of `created_at`, and doesn't have an `event_type` column.

**webhook_subscriptions** table:
```sql
CREATE TABLE webhook_subscriptions (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    secret TEXT NOT NULL,
    events TEXT[] NOT NULL,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### Smart Contract Development

#### Local Anvil Node

```bash
# Already running via Docker Compose on :8545

# Deploy contracts
cd contracts
forge script script/DeployMultichain.s.sol:DeployMultichain \
  --rpc-url http://localhost:8545 \
  --broadcast \
  -vvvv

# Interact with deployed contracts
cast call <CONTRACT_ADDRESS> "version()(string)" --rpc-url http://localhost:8545

# Send transactions
cast send <CONTRACT_ADDRESS> "approve()" \
  --rpc-url http://localhost:8545 \
  --private-key $PRIVATE_KEY
```

#### Fork Testing

Test against live networks using Anvil's fork mode:

```bash
# Stop Anvil container
docker compose stop anvil

# Start Anvil with Sepolia fork
docker run -p 8545:8545 ghcr.io/foundry-rs/foundry:latest \
  anvil --host 0.0.0.0 --fork-url $SEPOLIA_RPC_URL

# Run tests against fork
cd contracts
forge test --fork-url http://localhost:8545 -vvv
```

#### Run Contract Tests

```bash
cd contracts

       # Install dependencies (first time only)
       forge install foundry-rs/forge-std
       forge install OpenZeppelin/openzeppelin-contracts-upgradeable

# Run all tests
forge test -vv

# Run specific test
forge test --match-test testEscrowCreation -vvv

# Run with gas report
forge test --gas-report

# Run with coverage
forge coverage
```

---

### TypeScript SDK Development

```bash
cd sdk/ts

# Install dependencies
pnpm install

# Build SDK
pnpm build

# Run tests
pnpm test

# Run tests in watch mode
pnpm test:watch

# Type check
pnpm typecheck

# Lint
pnpm lint

# Format
pnpm format
```

#### SDK Usage Example

```typescript
import { ingestCommand, getCommandStatus } from '@fusionprime/sdk';

// Ingest a settlement command
const result = await ingestCommand({
  baseUrl: 'http://localhost:8000',
  command: {
    command_id: 'cmd-123',
    payer: '0x...',
    payee: '0x...',
    amount: '1000000000000000000', // 1 ETH in wei
    chain_id: 31337
  }
});

// Check command status
const status = await getCommandStatus({
  baseUrl: 'http://localhost:8000',
  commandId: 'cmd-123'
});
```

---

### Debugging

#### Service Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f pubsub-emulator
docker compose logs -f postgres
docker compose logs -f settlement-service

# Last 50 lines
docker compose logs settlement-service | tail -50
```

#### Pub/Sub Message Inspection

```bash
# Pull messages from a subscription
curl -X POST http://localhost:8085/v1/projects/fusion-prime-local/subscriptions/settlement-events-consumer:pull \
  -H "Content-Type: application/json" \
  -d '{"maxMessages": 10}'

# Acknowledge a message
curl -X POST http://localhost:8085/v1/projects/fusion-prime-local/subscriptions/settlement-events-consumer:acknowledge \
  -H "Content-Type: application/json" \
  -d '{"ackIds": ["<ACK_ID>"]}'
```

#### Python Debugging

Add breakpoints in your code:

```python
import pdb; pdb.set_trace()
```

Or use VS Code debugger with this launch configuration:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "app.main:app",
        "--reload",
        "--port",
        "8000"
      ],
      "env": {
        "PUBSUB_EMULATOR_HOST": "localhost:8085",
        "GCP_PROJECT": "fusion-prime-local"
      },
      "jinja": true
    }
  ]
}
```

#### Contract Debugging

```bash
# Trace a transaction
cast run <TX_HASH> --rpc-url http://localhost:8545 -vvvv

# Get transaction receipt
cast receipt <TX_HASH> --rpc-url http://localhost:8545 --json

# Get logs for an address
cast logs --address <CONTRACT_ADDRESS> --rpc-url http://localhost:8545

# Check storage slot
cast storage <CONTRACT_ADDRESS> <SLOT> --rpc-url http://localhost:8545
```

---

### Performance Tips

#### Speed Up Docker Builds

```bash
# Use BuildKit
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Build with cache
docker compose build --parallel
```

#### Reduce Startup Time

```bash
# Start only essential services
docker compose up -d pubsub-emulator postgres

# Start on-demand
docker compose up -d redis anvil  # Only when needed
```

#### Optimize Local Development

```bash
# Use hot reload for backend
cd services/settlement
poetry run uvicorn app.main:app --reload --port 8000

# Use watch mode for SDK
cd sdk/ts
pnpm test:watch

# Use Foundry's watch mode for contracts
cd contracts
forge test --watch
```

---

## Troubleshooting

### Anvil Not Responding

```bash
# Check if running
docker compose ps anvil

# Verify connection
curl -X POST http://localhost:8545 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# If curl hangs or times out, Anvil may not be listening on 0.0.0.0
# Check logs for "Listening on 127.0.0.1:8545" (wrong) vs "Listening on 0.0.0.0:8545" (correct)
docker compose logs anvil | grep "Listening on"

# If listening on 127.0.0.1, recreate the container (restart won't fix it)
docker compose stop anvil
docker compose rm -f anvil
docker compose up -d anvil

# Verify it's now on 0.0.0.0
sleep 3
docker compose logs anvil | grep "Listening on"
# Should show: "Listening on 0.0.0.0:8545"
```

### Contract Deployment Failed

```bash
# Check Anvil is running
docker compose ps anvil

# Check private key is set and has the correct value
echo $PRIVATE_KEY
# Should be: 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80

# If not set, export it
export PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80

# Check the deployer address has funds
export ANVIL_ADDRESS=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
cast balance $ANVIL_ADDRESS --rpc-url http://localhost:8545
# Should be: 10000000000000000000000 (10,000 ETH)

# Re-deploy with verbose output
cd contracts
forge script script/DeployMultichain.s.sol:DeployMultichain \
  --rpc-url http://localhost:8545 \
  --broadcast -vvvv
```

### Settlement Service Not Responding

```bash
# Check health
curl http://localhost:8000/health

# Check Docker
docker compose ps settlement-service

# Check logs
docker compose logs settlement-service | tail -50

# Restart
docker compose restart settlement-service

# Check environment variables
docker compose exec settlement-service env | grep PUBSUB
```

### Pub/Sub Emulator Issues

```bash
# Check if port 8085 is already in use
lsof -i :8085

# If another process is using port 8085, kill it
# (Find the PID from lsof output)
kill <PID>

# Or find and kill all processes on port 8085
lsof -ti :8085 | xargs kill -9

# Restart emulator
docker compose restart pubsub-emulator

# Reinitialize topics and subscriptions
export PUBSUB_EMULATOR_HOST=localhost:8085
./scripts/init-pubsub-emulator.sh

# List topics to verify (using REST API)
curl -s "http://localhost:8085/v1/projects/fusion-prime-local/topics" | jq -r '.topics[].name'

# List subscriptions to verify
curl -s "http://localhost:8085/v1/projects/fusion-prime-local/subscriptions" | jq -r '.subscriptions[].name'
```

### PostgreSQL Connection Issues

```bash
# Check if running
docker compose ps postgres

# Check if port 5432 is available
lsof -i :5432

# Reset database
docker compose down -v postgres
docker compose up -d postgres

# Wait for it to be ready
docker compose exec postgres pg_isready -U fusion_prime

# Test connection
docker exec fusion-prime-postgres psql -U fusion_prime -d fusion_prime -c "SELECT 1;"
```

### Tests Failing

```bash
# Clear previous state
docker compose down -v

# Fresh start
docker compose up -d
sleep 30

# Reinitialize Pub/Sub
export PUBSUB_EMULATOR_HOST=localhost:8085
./scripts/init-pubsub-emulator.sh

# Run migrations
cd services/settlement
docker exec -i fusion-prime-postgres psql -U fusion_prime -d fusion_prime < \
  infrastructure/migrations/001_create_settlement_commands.sql

# Run tests
./scripts/test.sh local
```

---

## Cleanup

### Quick Cleanup Script

```bash
# Use the cleanup script (recommended)
./scripts/cleanup-local.sh [LEVEL]

# Available levels:
#   minimal   - Stop containers only (data preserved)
#   standard  - Stop containers + remove volumes (default)
#   deep      - Standard + remove images
#   nuclear   - Deep + system cleanup + artifacts

# Examples:
./scripts/cleanup-local.sh minimal   # Just stop services
./scripts/cleanup-local.sh           # Standard cleanup (wipes data)
./scripts/cleanup-local.sh nuclear   # Nuclear option ☢️
```

### Manual Cleanup Commands

```bash
# Stop all services
docker compose down

# Stop and remove volumes (⚠️ deletes all data)
docker compose down -v

# Remove images
docker compose down --rmi all

# Clean Docker system
docker system prune -a --volumes
```

---

## Development Best Practices

### Keep It Fast

```bash
# Start only what you need
docker compose up -d pubsub-emulator postgres  # Minimal
docker compose up -d  # Everything

# Use file watching for hot reload
# - FastAPI: uvicorn --reload
# - TypeScript: pnpm dev
# - Solidity: forge test --watch

# Cache dependencies
# - Docker layer caching
# - Poetry/pnpm lock files
```

### Make It Reproducible

```bash
# Reset state when needed
docker compose down -v  # Remove all data
docker compose up -d     # Fresh start

# Use fixtures for tests
# - Foundry: setUp() function
# - Pytest: @pytest.fixture
# - Vitest: beforeEach()

# Document assumptions
# - Required environment variables
# - Expected initial state
# - Dependencies between services
```

### Pro Tips: Save Time

```bash
# Create aliases for common tasks
alias fusion-up='cd ~/fusion-prime && docker compose up -d && export PUBSUB_EMULATOR_HOST=localhost:8085'
alias fusion-down='docker compose down'
alias fusion-clean='./scripts/cleanup-local.sh'
alias fusion-logs='docker compose logs -f'
alias fusion-test='./scripts/test.sh local'

# Use tmux/screen for multiple terminals
# Terminal 1: Docker logs
# Terminal 2: Backend service
# Terminal 3: Contract testing
# Terminal 4: SDK development
```

---

## Detailed Workflows

### Workflow: New Smart Contract Feature

```bash
# 1. LOCAL: Write contract
vim contracts/core/src/MyNewFeature.sol

# 2. LOCAL: Write tests
vim contracts/core/test/MyNewFeature.t.sol

# 3. LOCAL: Run tests (instant, free)
forge test --match-contract MyNewFeature -vv
# ✓ All tests pass

# 4. LOCAL: Deploy to Anvil
forge script script/DeployMultichain.s.sol:DeployMultichain \
  --rpc-url http://localhost:8545 \
  --broadcast

# 5. LOCAL: Integration test
cast send $CONTRACT_ADDRESS "myNewFunction()" \
  --rpc-url http://localhost:8545 \
  --private-key $PRIVATE_KEY
# ✓ Works as expected

# 6. LOCAL: Test with backend services
curl -X POST http://localhost:8000/...
# ✓ Backend integration works

# 7. TEST: Deploy to Sepolia (only after local pass)
./scripts/test.sh local
# ✓ All local tests pass

cd contracts
forge script script/DeployMultichain.s.sol:DeployMultichain \
  --rpc-url $SEPOLIA_RPC_URL \
  --broadcast \
  --verify

# 8. TEST: Validate on testnet
./scripts/test.sh local
# ✓ Works on testnet

# 9. REVIEW: Code review, security check

# 10. PRODUCTION: Deploy (after approval & audit)
```

### Workflow: New Backend Microservice

```bash
# 1. LOCAL: Develop service
cd services/my-new-service
poetry new .
# ... write code ...

# 2. LOCAL: Unit tests (instant, free)
poetry run pytest -v
# ✓ All unit tests pass

# 3. LOCAL: Add to docker-compose.yml
vim docker-compose.yml
# Add your service definition

# 4. LOCAL: Test integration
docker compose up -d my-new-service
curl http://localhost:8001/health
# ✓ Service responds

# 5. LOCAL: Test Pub/Sub integration
gcloud pubsub topics publish my-topic \
  --message '{"test":"data"}'
# Check service logs
docker compose logs my-new-service
# ✓ Service processes messages

# 6. LOCAL: Domain-specific integration test
# Add test to appropriate domain directory
# For Risk & Analytics: tests/local/risk/
# For Compliance & Identity: tests/local/compliance/
# For Settlement: tests/local/settlement/
# For Infrastructure: tests/local/infrastructure/

# 7. LOCAL: Run domain tests
python tests/local/run_domain_tests.py {domain} -v
# ✓ Domain tests pass

# 8. LOCAL: E2E test
# Test complete flow with contracts + services
# ✓ Full flow works

# 9. TEST: Deploy to Cloud Run
gcloud run deploy my-new-service \
  --region us-central1 \
  --project fusion-prime

# 10. TEST: Integration test
curl https://my-new-service-dev.run.app/health

# 11. PRODUCTION: Deploy (after validation)
```

### Workflow: Bug Fix

```bash
# 1. LOCAL: Reproduce bug
# - Write failing test
# - Confirm bug exists locally

# 2. LOCAL: Fix bug
# - Modify code
# - Run tests until they pass

# 3. LOCAL: Domain-specific regression test
# - Run tests for affected domain
python tests/local/run_domain_tests.py {domain} -v
# ✓ Domain tests pass

# 4. LOCAL: Full regression test
# - Run all domain tests
# - Ensure no side effects
python tests/local/run_domain_tests.py all -v
# ✓ All tests pass

# 5. LOCAL: Manual verification
# - Test the specific scenario
# - Check logs for errors
# ✓ Bug fixed

# 6. TEST: Deploy fix
# - Deploy to test environment
# - Verify fix works
python tests/local/run_domain_tests.py all -v
# ✓ Fix confirmed

# 7. PRODUCTION: Hot fix (if urgent)
# - Follow production deployment process
# - Monitor closely
```

---

## When to Skip Local Testing

Very rarely! But here are exceptions:

1. **External API Integration**
   - Third-party KYC provider
   - Price oracle
   - → Mock locally, test on testnet

2. **Multi-Chain Specific**
   - Cross-chain bridge specific to Polygon
   - → Test on Amoy testnet

3. **GCP-Specific Features**
   - Cloud SQL HA failover
   - Cloud KMS encryption
   - → Test in GCP dev environment

4. **Performance/Load Testing**
   - Stress testing with 1000s of requests
   - → Use GCP dev with load testing tools

**For everything else: Test locally first!**

---

## Test Coverage Requirements

### Before Test Environment Deployment

- ✅ All unit tests pass (100% coverage target)
- ✅ All domain-specific integration tests pass
- ✅ Cross-domain E2E flow works end-to-end
- ✅ No errors in logs
- ✅ Manual smoke test successful
- ✅ Code review complete
- ✅ Documentation updated

### Before Production Deployment

- ✅ All test environment tests pass
- ✅ No critical issues in 48+ hours
- ✅ Security audit complete
- ✅ Multi-sig setup verified
- ✅ Monitoring & alerts tested
- ✅ Rollback plan documented
- ✅ Team sign-off received

---

## Daily Development Workflow

```bash
# Morning: Start your environment
cd fusion-prime
docker compose up -d
export PUBSUB_EMULATOR_HOST=localhost:8085
source .env.local

# Develop
# - Edit code (contracts/services/SDK)
# - Hot reload happens automatically

# Test (domain-specific)
# For Risk & Analytics work:
python tests/local/run_domain_tests.py risk -v

# For Compliance & Identity work:
python tests/local/run_domain_tests.py compliance -v

# For Settlement work:
python tests/local/run_domain_tests.py settlement -v

# For Infrastructure work:
python tests/local/run_domain_tests.py infrastructure -v

# For cross-domain testing:
python tests/local/run_domain_tests.py all -v

# Or use the unified test script:
./scripts/test.sh local

# Evening: Stop services
docker compose down
```

---

## Next Steps

### 1. Run Full Test Suite

```bash
# Universal test runner (recommended)
./scripts/test.sh local

# Specific suites
./scripts/test.sh local contracts
./scripts/test.sh local backend
./scripts/test.sh local integration

# See TESTING.md for complete guide
```

### 2. Explore the Platform

- **Swagger UI**: http://localhost:8000/docs
- **Contract interactions**: Use `cast` commands
- **Database**: Connect with `psql`
- **Pub/Sub**: Use `gcloud pubsub` commands

### 3. Deploy to Test Environment

Ready for testnet?

```bash
# Setup environment
./scripts/setup-env.sh

# Deploy contracts to Sepolia
cd contracts
forge script script/DeployMultichain.s.sol:DeployMultichain \
  --rpc-url $SEPOLIA_RPC_URL \
  --broadcast \
  --verify

# Test on testnet
./scripts/test.sh local
```

See:
- [ENVIRONMENTS.md](ENVIRONMENTS.md) - Three-tier architecture
- [DEPLOYMENT_STATUS.md](DEPLOYMENT_STATUS.md) - Current deployments
- [contracts/DEPLOYMENT.md](contracts/DEPLOYMENT.md) - Contract deployment guide

### 4. Develop New Features

- Modify smart contracts in `contracts/core/src/`
- Add backend endpoints in `services/settlement/app/routes/`
- Extend SDK in `sdk/ts/src/`
- Run tests after each change

### 5. CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Start Services
        run: docker compose up -d

      - name: Initialize Pub/Sub
        run: ./scripts/init-pubsub-emulator.sh

      - name: Run Tests
        run: ./scripts/test.sh local
```

---

## Resources

**Testing & Development**:
- [TESTING.md](TESTING.md) - Universal testing guide ⭐
- [ENVIRONMENTS.md](ENVIRONMENTS.md) - Three-tier architecture ⭐
- [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md) - Local-first philosophy

**Deployment**:
- [DEPLOYMENT_STATUS.md](DEPLOYMENT_STATUS.md) - Current deployment state
- [contracts/DEPLOYMENT.md](contracts/DEPLOYMENT.md) - Contract deployment

**Project Info**:
- [docs/specification.md](docs/specification.md) - Platform specification
- [AGENTS.md](AGENTS.md) - Agent roles and responsibilities

**External References**:
- [Google Cloud Pub/Sub Emulator](https://cloud.google.com/pubsub/docs/emulator)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Foundry Book](https://book.getfoundry.sh/)
- [Poetry Documentation](https://python-poetry.org/docs/)

---

**🎉 You're ready to build!**

Start developing features, run tests locally (free and fast), then deploy to test and production environments.

**Questions or Issues?**
- Check logs: `docker compose logs -f`
- Read troubleshooting section above
- See [TESTING.md](TESTING.md) for testing help

**Happy coding! 🚀**
