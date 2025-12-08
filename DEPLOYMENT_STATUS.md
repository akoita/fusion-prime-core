# 🚀 Fusion Prime - Deployment Status

**Purpose**: Current deployment state, resource inventory, and service status
**Target Users**: DevOps, developers, system administrators
**Last Updated**: 2025-11-02
**Update Frequency**: After each deployment

---

## 📊 Quick Status Overview

| Environment | Status | Services | Blockchain | Last Deployed |
|-------------|--------|----------|------------|---------------|
| **dev** | ✅ Active | 12 services | Sepolia + Amoy Testnets | 2025-11-03 |
| **staging** | ⚠️ Partial | 2 services | Sepolia Testnet | TBD |
| **production** | ❌ Not deployed | 0 services | Ethereum Mainnet | N/A |

---

## 🌍 Environment Details

### 🟢 DEV Environment (fusion-prime / fusion-prime-dev)

**GCP Project**: `fusion-prime` or `fusion-prime-dev`
**Blockchain**: Sepolia Testnet (Chain ID: 11155111)
**Region**: `us-central1`

#### Services Deployed

| Service | URL | Status | Revision | Health |
|---------|-----|--------|----------|--------|
| **Cross-Chain Integration** | `https://cross-chain-integration-service-961424092563.us-central1.run.app` | ✅ Running | cross-chain-integration-service-00040-29k | `/health` |
| **API Key Service** | `https://api-key-service-ggats6pubq-uc.a.run.app` | ✅ Running | - | `/health` |
| **Fiat Gateway** | `https://fiat-gateway-service-ggats6pubq-uc.a.run.app` | ✅ Running | - | `/health` |
| **Settlement** | `https://settlement-service-ggats6pubq-uc.a.run.app` | ✅ Running | settlement-service-00028-vrc | `/health` |
| **Risk Engine** | `https://risk-engine-service-ggats6pubq-uc.a.run.app` | ✅ Running | risk-engine-service-00008-ph8 | `/health` |
| **Risk Engine (legacy)** | `https://risk-engine-ggats6pubq-uc.a.run.app` | ✅ Running | risk-engine-00020-f27 | `/health` |
| **Compliance** | `https://compliance-ggats6pubq-uc.a.run.app` | ✅ Running | compliance-00023-mrf | `/health` |
| **Alert Notification** | `https://alert-notification-service-ggats6pubq-uc.a.run.app` | ✅ Running | alert-notification-service-00014-8n9 | `/health` |
| **Alert Notification (legacy)** | `https://alert-notification-ggats6pubq-uc.a.run.app` | ✅ Running | alert-notification-00005-x4n | `/health` |
| **Event Relayer** | `https://escrow-event-relayer-service-961424092563.us-central1.run.app` | ✅ Running | escrow-event-relayer-service-00031-pbd | `/status` |
| **Price Oracle** | `https://price-oracle-service-ggats6pubq-uc.a.run.app` | ✅ Running | price-oracle-service-00002-zlw | `/health` |
| **Risk Dashboard** | `https://risk-dashboard-961424092563.us-central1.run.app` | ✅ Running | risk-dashboard-00001-k7s | `/health` |

#### Infrastructure Resources

**Cloud SQL Databases**:
- `fusion-prime-db` - Settlement service database
- `fusion-prime-risk-db` - Risk Engine database
- `fusion-prime-compliance-db` - Compliance database
- `fp-cross-chain-db-0c277aa9` - Cross-Chain Integration database

**Pub/Sub Topics**:
- `settlement.events.v1` - Escrow lifecycle events
- `prices.v1` - Price feed updates
- `alerts.margin.v1` - Margin health alerts
- `risk.events.v1` - Risk calculation events
- `cross-chain.messages.v1` - Cross-chain message events

**Cloud Scheduler**:
- `relayer-scheduler` - Runs event relayer every 5 minutes

**Secret Manager**:
- `fp-settlement-db-connection-string` - Settlement DB connection
- `fp-risk-db-connection-string` - Risk Engine DB connection
- `fp-compliance-db-connection-string` - Compliance DB connection
- `fp-cross-chain-db-connection-string` - Cross-Chain Integration DB connection
- `fp-ethereum-rpc-url` - Ethereum Sepolia RPC endpoint
- `fp-polygon-rpc-url` - Polygon Amoy RPC endpoint
- `fp-deployer-private-key` - Testnet deployer private key

#### Blockchain Resources

**Deployed Contracts** (Sepolia Testnet):
- **EscrowFactory**: `0x311E63dfcEfe7f2c202715ef0DF01CDA82f58914`
- **Start Block**: `9533200` (deployment block)

**Cross-Chain Contracts** (Testnets):
- **Ethereum Sepolia (Chain ID: 11155111)**:
  - CrossChainVault: `0x0C95a78b0D72F882fae14CD7C842a5f000E0c4e2` ✅
  - BridgeManager: `0xC96DA7e94E8407e0988bb60A1b23B9358Cd63A56` ✅
  - AxelarAdapter: `0x3C8e965aFF06DFcaE9f6cc778b38d72D54D1381d` ✅
  - CCIPAdapter: `0x9204E095e6d50Ff8f828e71F4C0849C5aEfe992c` ✅
  - Axelar Gateway: `0xe432150cce91c13a887f7D836923d5597adD8E31` (testnet)
  - CCIP Router: `0x0BF3dE8c5D3e8A2B34D2BEeB17ABfCeBaf363A59` (testnet)
- **Polygon Amoy (Chain ID: 80002)**:
  - CrossChainVault: `0x7843C2eD8930210142DC51dbDf8419C74FD27529` ✅
  - BridgeManager: `0x3481dbE036C0F4076B397e27FFb8dC32B88d8882` ✅
  - AxelarAdapter: `0x6e48D179CD80979c8eDf65A5d783B501A0313159` ✅
  - CCIPAdapter: `0xe15A30f1eF8c1De56F19b7Cef61cC3776119451C` ✅
  - Axelar Gateway: `0xBF62eF1486468a6bD26DD669C06Db43De641D239` (testnet)
  - CCIP Router: `0x1035CabC275068e0F4b745A29CEDf38E13aF41b1` (testnet)

**RPC Endpoints**:
- Ethereum Sepolia: Spectrum Simply Staking Sepolia RPC
- Polygon Amoy: `https://spectrum-03.simplystaking.xyz/.../polygon/testnet/`
- Fallback: Public testnet RPCs

---

### 🟡 STAGING Environment

**GCP Project**: `fusion-prime-staging` (planned)
**Blockchain**: Sepolia Testnet
**Status**: ⚠️ Partial deployment - Configure when ready for staging

---

### 🔴 PRODUCTION Environment

**GCP Project**: `fusion-prime-production` (planned)
**Blockchain**: Ethereum Mainnet (Chain ID: 1)
**Status**: ❌ Not deployed - Production deployment pending

---

## 📋 Service Inventory

### Core Services

#### 1. Settlement Service
- **Purpose**: Escrow lifecycle management, payment processing
- **Database**: `fusion-prime-db` (PostgreSQL)
- **Pub/Sub**: Consumes `settlement.events.v1`
- **Health Endpoint**: `/health`
- **API Documentation**: `/docs` (FastAPI)

#### 2. Risk Engine Service
- **Purpose**: Risk calculations, margin health monitoring, VaR calculations
- **Database**: `fusion-prime-risk-db` (PostgreSQL)
- **Pub/Sub**: Consumes `settlement.events.v1`, publishes `risk.events.v1`
- **Health Endpoint**: `/health`
- **API Documentation**: `/docs` (FastAPI)

#### 3. Compliance Service
- **Purpose**: KYC/AML checks, compliance workflows
- **Database**: `fusion-prime-compliance-db` (PostgreSQL)
- **Pub/Sub**: Consumes `settlement.events.v1`
- **Health Endpoint**: `/health`
- **API Documentation**: `/docs` (FastAPI)

#### 4. Alert Notification Service
- **Purpose**: Multi-channel alert delivery (email, SMS, webhook)
- **Database**: `fusion-prime-risk-db` (shares with Risk Engine for alert_notifications table)
- **Pub/Sub**: Consumes `alerts.margin.v1`
- **Health Endpoint**: `/health`
- **Features**: Notification preferences, delivery history

#### 5. Event Relayer Service
- **Purpose**: Blockchain event monitoring and Pub/Sub publishing
- **Type**: Cloud Run Service (continuous)
- **Poll Interval**: 3 seconds (adaptive)
- **Auto Fast-Forward**: Enabled (threshold: 500 blocks)
- **Admin Endpoint**: `/admin/set-start-block` (see `services/relayer/ADMIN_ENDPOINT.md`)
- **Status Endpoint**: `/status` - Shows current block, lag, events processed

#### 6. Price Oracle Service
- **Purpose**: Price feed aggregation and distribution
- **Status**: ✅ Running
- **URL**: `https://price-oracle-service-ggats6pubq-uc.a.run.app`
- **Revision**: `price-oracle-service-00002-zlw`
- **Pub/Sub**: Publishes to `prices.v1`

---

## 🔧 Resource Configuration

### Database Configuration

All databases use Cloud SQL Proxy for connections:
- **Connection Method**: Cloud SQL Proxy or private IP
- **Secret Storage**: Google Cloud Secret Manager
- **Migration Tool**: Alembic (per service)

### Pub/Sub Configuration

**Topics**:
- `settlement.events.v1` - Escrow events (EscrowDeployed, EscrowCreated, Approved, EscrowReleased, EscrowRefunded)
- `prices.v1` - Price updates (planned)
- `alerts.margin.v1` - Margin health alerts
- `risk.events.v1` - Risk calculation events

**Subscriptions**:
- `settlement-service-subscription` → Settlement service
- `risk-events-consumer` → Risk Engine
- `compliance-events-consumer` → Compliance service
- `alert-notification-subscription` → Alert Notification service

---

## 📊 Monitoring & Health

### Health Check Endpoints

```bash
# Settlement
curl https://settlement-service-ggats6pubq-uc.a.run.app/health

# Risk Engine
curl https://risk-engine-service-ggats6pubq-uc.a.run.app/health

# Compliance
curl https://compliance-ggats6pubq-uc.a.run.app/health

# Alert Notification
curl https://alert-notification-service-ggats6pubq-uc.a.run.app/health

# Price Oracle
curl https://price-oracle-service-ggats6pubq-uc.a.run.app/health

# Event Relayer Status
curl https://escrow-event-relayer-service-ggats6pubq-uc.a.run.app/status
```

### Monitoring Tools

- **Cloud Run**: Service logs, metrics, revisions
- **Cloud SQL**: Database metrics, connections
- **Pub/Sub**: Message throughput, subscription lag
- **Cloud Monitoring**: Custom dashboards and alerts

---

## 🧪 Test Status

**Current Test Results**: ✅ **86/86 tests passing**

- **Integration Tests**: All passing
- **End-to-End Tests**: All passing
- **Workflow Tests**: All passing (escrow creation, release, refund, approval)
- **Service Health Checks**: All passing
- **Blockchain Integration**: Validated on Sepolia testnet

See [TESTING.md](./TESTING.md) for detailed test information.

---

## 🔄 Deployment History

| Date | Environment | Services | Changes | Status |
|------|-------------|----------|---------|--------|
| 2025-11-02 | dev | All services | Relayer auto fast-forward, performance optimizations | ✅ Success |
| 2025-10-29 | dev | Alert Notification | Database persistence fix | ✅ Success |
| 2025-10-27 | dev | All services | Initial deployment | ✅ Success |

---

## 📝 Update This Document

This document should be updated:

1. **After each deployment** - Update service URLs, revisions, deployment date
2. **When infrastructure changes** - Update resource inventory
3. **Weekly** - Update test status and health checks
4. **When environments are added** - Add new environment sections

### Quick Update Commands

```bash
# Check current service URLs
gcloud run services list --project=fusion-prime --format="table(metadata.name,status.url)"

# Check database instances
gcloud sql instances list --project=fusion-prime

# Check Pub/Sub topics
gcloud pubsub topics list --project=fusion-prime

# Check relayer status
curl https://escrow-event-relayer-service-961424092563.us-central1.run.app/status
```

---

## 🔗 Related Documentation

- **[ENVIRONMENTS.md](./ENVIRONMENTS.md)** - Environment configuration guide
- **[docs/operations/DEPLOYMENT.md](./docs/operations/DEPLOYMENT.md)** - Deployment procedures
- **[QUICKSTART.md](./QUICKSTART.md)** - Local development setup
- **[TESTING.md](./TESTING.md)** - Testing guide

---

## ⚠️ Important Notes

- **DEV environment** is active and used for integration testing
- **All services** are running latest revisions with auto-scaling enabled
- **Database migrations** are handled automatically via Cloud Build
- **Relayer** auto fast-forwards when >500 blocks behind (configurable)
- **Secrets** are stored in Google Cloud Secret Manager

---

**Last Updated**: 2025-11-03
**Next Review**: After next deployment or weekly
