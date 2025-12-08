# Fusion Prime - Unified Test Suite

**One test directory for ALL environments** - local, testnet, and production.

## 🎯 Philosophy

**Same tests, different configuration** - Write tests once, run them everywhere.

## 📁 Structure

```
tests/
├── base_integration_test.py         # Base class for integration tests
├── base_infrastructure_test.py      # Base class for infrastructure tests
├── conftest_integration.py          # Pytest configuration
│
├── test_blockchain_connectivity.py  # Blockchain connectivity
├── test_settlement_service.py       # Settlement service API tests
├── test_risk_engine_service.py      # Risk engine tests
├── test_compliance_service.py       # Compliance service tests
├── test_database_connectivity.py    # Database connectivity
├── test_settlement_service_health.py # Service health checks
├── test_environment_configuration.py # Environment validation
├── test_pubsub_configuration.py     # Pub/Sub setup
├── test_pubsub_integration.py       # Pub/Sub messaging
├── test_relayer_job_health.py       # Relayer health
├── test_relayer_logs_analysis.py    # Relayer logs
│
├── test_escrow_creation_workflow.py # Full escrow creation workflow
├── test_escrow_approval_workflow.py # Escrow approval workflow
├── test_escrow_release_workflow.py  # Payment release workflow
├── test_escrow_refund_workflow.py   # Refund workflow
├── test_end_to_end_workflow.py      # Complete E2E test
│
├── common/                          # Shared utilities
│   ├── abi_loader.py
│   ├── config.py
│   └── helpers.py
│
├── config/                          # Configuration files
│   ├── environments.yaml
│   └── fixtures.yaml
│
└── workflows/                       # Workflow-based tests
    ├── base_workflow_test.py
    └── escrow_creation_workflow.py
```

## 🚀 Quick Start

### Cross-Chain Integration Service Tests

**Location:** `services/cross-chain-integration/tests/`

**Run Tests:**
```bash
cd services/cross-chain-integration
PYTHONPATH=. python -m pytest tests/ -v
```

**Test Coverage:**
- `test_retry_coordinator.py` - Retry logic for failed messages (7 tests)
- `test_ccip_client.py` - CCIP message status queries (5 tests)
- `test_vault_client.py` - CrossChainVault contract queries (5 tests)
- `test_orchestrator_collateral.py` - Collateral snapshot functionality (5 tests)

**See:** `services/cross-chain-integration/TESTING.md` for complete testing guide.

### Dev Environment Testing (Recommended - GCP + Sepolia)

```bash
# Simple test runner for dev environment
# Automatically loads .env.dev configuration
./tests/run_dev_tests.sh all          # All tests except workflows (~20 sec)
./tests/run_dev_tests.sh health       # Health checks only (~5 sec)
./tests/run_dev_tests.sh complete     # Everything including workflows (~90 sec)
```

**Available test categories**:
- `health` - Health checks (~5 sec)
- `service` - Service integration (~10 sec)
- `integration` - Cross-service integration (~8 sec)
- `connectivity` - Blockchain & database (~10 sec)
- `workflow` - E2E workflows (~60-90 sec, uses testnet gas)
- `all` - All tests except workflows (~20 sec) [DEFAULT]
- `complete` - Everything including workflows (~90-120 sec)

**See**: `docs/operations/TESTING.md` for complete testing workflows

---

### Local Testing (AUTOMATED - Recommended!)

```bash
# 1. Start everything automatically (infrastructure + migrations + services)
./scripts/setup/start_local_testing.sh

# 2. Load environment and run tests
source .env.local
export TEST_ENVIRONMENT=local
pytest tests/test_escrow_creation_workflow.py -v
```

**What the automated script does:**
- ✅ Starts Docker Compose services (Postgres, Pub/Sub, Anvil, Redis)
- ✅ Initializes Pub/Sub topics and subscriptions
- ✅ Runs Alembic database migrations
- ✅ Deploys smart contracts to Anvil (if available)
- ✅ Starts application services (Settlement, Risk, Compliance, Relayer)
- ✅ Waits for health checks and provides status

### Manual Local Testing (Advanced)

```bash
# 1. Start services manually
docker compose up -d

# 2. Initialize Pub/Sub
python3 scripts/setup/init_local_pubsub.py

# 3. Run migrations (in fusion-prime venv)
cd services/settlement && alembic upgrade head && cd ../..

# 4. Load environment and run tests
export TEST_ENVIRONMENT=local
source .env.local
python -m pytest tests/ -v
```

### Testnet Testing (Cloud Run)

```bash
# 1. Set environment
export TEST_ENVIRONMENT=testnet

# 2. Configure services
export ETH_RPC_URL="wss://sepolia.infura.io/ws/v3/YOUR_KEY"
export SETTLEMENT_SERVICE_URL="https://settlement-service-xxx.run.app"
export RISK_ENGINE_SERVICE_URL="https://risk-engine-service-xxx.run.app"
export COMPLIANCE_SERVICE_URL="https://compliance-service-xxx.run.app"
export PAYER_PRIVATE_KEY="0x..."

# 3. Run tests
python -m pytest tests/ -v
```

## 🔑 How It Works

### Environment Auto-Detection

Base classes automatically detect and configure for the environment:

```python
# tests/base_integration_test.py
class BaseIntegrationTest:
    def setup_method(self):
        self.environment = os.getenv("TEST_ENVIRONMENT", "local")

        if self.environment == "local":
            # Docker Compose defaults
            self.rpc_url = "http://localhost:8545"
            self.settlement_url = "http://localhost:8000"
            # ...
        else:
            # Cloud Run from env vars
            self.rpc_url = os.getenv("ETH_RPC_URL")
            self.settlement_url = os.getenv("SETTLEMENT_SERVICE_URL")
            # ...
```

### Test Implementation

Tests inherit from base classes and get automatic configuration:

```python
from tests.base_integration_test import BaseIntegrationTest

class TestSettlementService(BaseIntegrationTest):
    def test_settlement_service_connectivity(self):
        # self.settlement_url automatically configured
        response = requests.get(f"{self.settlement_url}/health")
        assert response.status_code == 200
```

## 📊 Test Categories

### 1. Service Integration Tests ✅
- `test_blockchain_connectivity.py` - Anvil/Sepolia connectivity
- `test_settlement_service.py` - Settlement API
- `test_risk_engine_service.py` - Risk calculations
- `test_compliance_service.py` - KYC/AML checks

**Status**: All passing in local environment

### 2. Infrastructure Tests ✅
- `test_database_connectivity.py` - PostgreSQL connection
- `test_pubsub_configuration.py` - Pub/Sub topics/subscriptions
- `test_settlement_service_health.py` - Service health endpoints
- `test_environment_configuration.py` - Environment validation

**Status**: All passing in local environment

### 3. Workflow Tests 🚧
- `test_escrow_creation_workflow.py` - Create escrow + event pipeline
- `test_escrow_approval_workflow.py` - Approval workflow
- `test_escrow_release_workflow.py` - Payment release
- `test_escrow_refund_workflow.py` - Refund process
- `test_end_to_end_workflow.py` - Full cross-service workflow

**Status**: Require contract deployment

### 4. Operational Tests 🚧
- `test_relayer_job_health.py` - Relayer job execution
- `test_relayer_logs_analysis.py` - Log analysis
- `test_pubsub_integration.py` - Message flow

**Status**: Require event relayer configuration

## ✅ Current Test Status

### Passing Tests (Local Environment)

```bash
$ source .env.local && pytest tests/ -v

✅ test_blockchain_connectivity.py::test_blockchain_connectivity
✅ test_settlement_service.py::test_settlement_service_connectivity
✅ test_risk_engine_service.py::test_risk_engine_service
✅ test_compliance_service.py::test_compliance_service
✅ test_database_connectivity.py::test_database_connectivity
✅ test_settlement_service_health.py::test_settlement_service_health
✅ test_environment_configuration.py::test_environment_configuration

7 passed ✅
```

### Tests Requiring Setup

- Workflow tests: Need `ESCROW_FACTORY_ADDRESS` (deploy contracts first)
- Relayer tests: Need relayer configuration
- Pub/Sub tests: Need topic/subscription creation

## 🔧 Configuration Files

### `.env.local` - Local Environment

```bash
TEST_ENVIRONMENT=local
ETH_RPC_URL=http://localhost:8545
CHAIN_ID=31337
SETTLEMENT_SERVICE_URL=http://localhost:8000
RISK_ENGINE_SERVICE_URL=http://localhost:8001
COMPLIANCE_SERVICE_URL=http://localhost:8002
DATABASE_URL=postgresql://fusion_prime:fusion_prime_dev_pass@localhost:5432/fusion_prime
PUBSUB_EMULATOR_HOST=localhost:8085
GCP_PROJECT=fusion-prime-local
# Anvil default accounts (pre-funded)
PAYER_PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
PAYEE_ADDRESS=0x70997970C51812dc3A010C7d01b50e0d17dc79C8
```

### `.env.testnet` - Testnet Environment (Example)

```bash
TEST_ENVIRONMENT=testnet
ETH_RPC_URL=wss://sepolia.infura.io/ws/v3/YOUR_KEY
CHAIN_ID=11155111
ESCROW_FACTORY_ADDRESS=0x...
SETTLEMENT_SERVICE_URL=https://settlement-service-xxx.us-central1.run.app
RISK_ENGINE_SERVICE_URL=https://risk-engine-service-xxx.us-central1.run.app
COMPLIANCE_SERVICE_URL=https://compliance-service-xxx.us-central1.run.app
GCP_PROJECT=fusion-prime
GCP_REGION=us-central1
PAYER_PRIVATE_KEY=0x...  # Your testnet private key
PAYEE_ADDRESS=0x...      # Test payee address
```

## 🏃 Running Tests

### Run All Tests

```bash
# Local
source .env.local && pytest tests/ -v

# Testnet
source .env.testnet && pytest tests/ -v
```

### Run Specific Category

```bash
# Service tests only
pytest tests/test_*_service*.py -v

# Infrastructure tests only
pytest tests/test_database*.py tests/test_*health*.py -v

# Workflow tests only
pytest tests/test_*_workflow.py -v
```

### Run Single Test

```bash
pytest tests/test_settlement_service.py -v
pytest tests/test_settlement_service.py::TestSettlementService::test_settlement_service_connectivity -v
```

### With Coverage

```bash
pytest tests/ --cov=services --cov-report=html
```

## 🐛 Troubleshooting

### Docker Compose Services Not Running

```bash
# Check services
docker compose ps

# Start services
docker compose up -d

# Check logs
docker compose logs settlement-service
docker compose logs anvil
```

### Tests Failing with Connection Errors

```bash
# Verify services are healthy
curl http://localhost:8000/health  # Settlement
curl http://localhost:8001/health  # Risk Engine
curl http://localhost:8002/health  # Compliance

# Check Anvil
cast client --rpc-url http://localhost:8545
```

### Missing Environment Variables

```bash
# Load environment
source .env.local

# Verify
echo $TEST_ENVIRONMENT
echo $SETTLEMENT_SERVICE_URL
```

### Contract Not Deployed

```bash
# Deploy contracts
cd contracts
forge script script/Deploy.s.sol --rpc-url http://localhost:8545 --broadcast

# Update .env.local with ESCROW_FACTORY_ADDRESS
```

## 📚 Related Documentation

- **[TESTING.md](../TESTING.md)** - Complete testing guide
- **[tests/workflows/README.md](workflows/README.md)** - Workflow testing patterns
- **[tests/MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** - Migration from old structure
- **[docker-compose.yml](../docker-compose.yml)** - Local service configuration

## 🎯 Next Steps

1. ✅ **Basic tests** - All passing locally
2. 🚧 **Deploy contracts** - For workflow tests
3. 🚧 **Configure relayer** - For event-driven tests
4. 🚧 **Run on testnet** - Validate remote environment
5. 📋 **Add more tests** - Expand coverage

## 🤝 Contributing

When adding new tests:

1. **Inherit from base class**: Use `BaseIntegrationTest` or `BaseInfrastructureTest`
2. **Environment-agnostic**: Tests should work in both local and testnet
3. **No hardcoded URLs**: Use `self.settlement_url`, `self.rpc_url`, etc.
4. **Graceful handling**: Skip tests if optional services unavailable
5. **Clear assertions**: Meaningful error messages

### Example Test

```python
from tests.base_integration_test import BaseIntegrationTest

class TestMyFeature(BaseIntegrationTest):
    def test_my_feature(self):
        """Test my feature works in any environment."""
        # self.web3, self.settlement_url automatically configured
        # for local or testnet based on TEST_ENVIRONMENT

        response = requests.post(f"{self.settlement_url}/my-endpoint", ...)
        assert response.status_code == 200
```

---

**Key Takeaway**: One unified test suite that adapts to any environment - write once, test everywhere! 🚀
