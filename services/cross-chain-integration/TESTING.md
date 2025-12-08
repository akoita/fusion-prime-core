# Cross-Chain Integration Service - Testing Guide

Complete guide for testing the Cross-Chain Integration Service, including unit tests, integration tests, and test environment setup.

## 📋 Table of Contents

- [Overview](#overview)
- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Test Files](#test-files)
- [Environment Setup](#environment-setup)
- [Test Coverage](#test-coverage)
- [Troubleshooting](#troubleshooting)

## Overview

The Cross-Chain Integration Service includes comprehensive test coverage for:
- **RetryCoordinator** - Retry logic for failed cross-chain messages
- **CCIPClient** - Chainlink CCIP message status checking
- **AxelarClient** - Axelar transaction queries
- **VaultClient** - CrossChainVault contract queries
- **OrchestratorService** - Settlement orchestration and collateral snapshots

## Test Structure

```
services/cross-chain-integration/
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Pytest configuration and path setup
│   ├── test_retry_coordinator.py
│   ├── test_ccip_client.py
│   ├── test_vault_client.py
│   └── test_orchestrator_collateral.py
├── app/
│   ├── __init__.py              # Package marker (required)
│   ├── core/
│   │   ├── __init__.py
│   │   └── retry_coordinator.py
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── ccip_client.py
│   │   └── axelar_client.py
│   └── services/
│       ├── __init__.py
│       ├── bridge_executor.py
│       ├── vault_client.py
│       └── orchestrator_service.py
└── infrastructure/
    ├── __init__.py              # Package marker (required)
    └── db/
        ├── __init__.py          # Package marker (required)
        └── models.py
```

## Running Tests

### Prerequisites

1. **Python Environment**: Python 3.13+ (or 3.11+)
2. **Dependencies**: Install service dependencies
   ```bash
   cd services/cross-chain-integration
   pip install -r requirements.txt
   ```

3. **Test Dependencies**: Ensure pytest and test dependencies are installed
   ```bash
   pip install pytest pytest-asyncio pytest-mock httpx web3 eth-account eth-abi
   ```

### Running All Tests

From the service directory:

```bash
cd services/cross-chain-integration
PYTHONPATH=. python -m pytest tests/ -v
```

From the project root:

```bash
cd /home/koita/dev/web3/fusion-prime
PYTHONPATH=services/cross-chain-integration python -m pytest services/cross-chain-integration/tests/ -v
```

### Running Specific Test Files

```bash
# Run RetryCoordinator tests
PYTHONPATH=. python -m pytest tests/test_retry_coordinator.py -v

# Run CCIP client tests
PYTHONPATH=. python -m pytest tests/test_ccip_client.py -v

# Run Vault client tests
PYTHONPATH=. python -m pytest tests/test_vault_client.py -v

# Run Orchestrator collateral tests
PYTHONPATH=. python -m pytest tests/test_orchestrator_collateral.py -v
```

### Running Specific Tests

```bash
# Run a specific test class
PYTHONPATH=. python -m pytest tests/test_retry_coordinator.py::TestRetryCoordinator -v

# Run a specific test method
PYTHONPATH=. python -m pytest tests/test_ccip_client.py::TestCCIPClient::test_get_ccip_chain_selector -v
```

### Test Output Formats

```bash
# Verbose output with short traceback
PYTHONPATH=. python -m pytest tests/ -v --tb=short

# Quiet mode (summary only)
PYTHONPATH=. python -m pytest tests/ -q

# With coverage report
PYTHONPATH=. python -m pytest tests/ --cov=app --cov-report=html
```

## Test Files

### test_retry_coordinator.py

Tests for `RetryCoordinator` class that handles retry logic for failed cross-chain messages.

**Test Coverage:**
- ✅ Finding failed messages eligible for retry
- ✅ Checking retry eligibility based on timing and exponential backoff
- ✅ Successfully retrying messages with bridge execution
- ✅ Handling max retries exceeded
- ✅ Handling retry execution failures
- ✅ Processing retry queue in batches

**Key Features Tested:**
- Exponential backoff logic
- Bridge transaction retry execution
- Message status updates
- Error handling and rollback

**Example:**
```python
@pytest.mark.asyncio
async def test_retry_message_success(self, mock_session, failed_message):
    """Test successful message retry."""
    coordinator = RetryCoordinator(mock_session)
    # Mocks BridgeExecutor to return new transaction hash
    result = await coordinator.retry_message(failed_message)
    assert result is True
    assert failed_message.status == MessageStatus.PENDING
```

### test_ccip_client.py

Tests for `CCIPClient` class that queries Chainlink CCIP Router contracts.

**Test Coverage:**
- ✅ Getting CCIP chain selectors for known chains
- ✅ Querying message status via Web3 (with/without RPC)
- ✅ Handling invalid chains gracefully
- ✅ Client cleanup

**Key Features Tested:**
- Chain selector mapping (Sepolia, Amoy, Arbitrum, etc.)
- Web3 contract queries for message status
- Graceful handling when RPC unavailable
- Error handling for unsupported chains

**Example:**
```python
@pytest.mark.asyncio
async def test_get_ccip_chain_selector(self, ccip_client):
    """Test getting chain selector for known chains."""
    selector = await ccip_client.get_ccip_chain_selector("sepolia")
    assert selector == 16015286601757825753
```

### test_vault_client.py

Tests for `VaultClient` class that queries CrossChainVault contracts.

**Test Coverage:**
- ✅ VaultClient initialization
- ✅ Getting collateral on specific chains
- ✅ Getting total collateral across chains
- ✅ Handling unavailable vaults gracefully
- ✅ Querying all chains for collateral

**Key Features Tested:**
- Web3 connections to multiple chains
- Contract ABI interactions
- Collateral aggregation
- Error handling for missing vaults

**Example:**
```python
def test_get_collateral_all_chains(self, vault_client):
    """Test getting collateral across all chains."""
    collateral_by_chain = vault_client.get_collateral_all_chains(user_address)
    assert isinstance(collateral_by_chain, dict)
    for chain, amount in collateral_by_chain.items():
        assert isinstance(amount, int)
        assert amount >= 0
```

### test_orchestrator_collateral.py

Tests for `OrchestratorService.get_collateral_snapshot()` functionality.

**Test Coverage:**
- ✅ Handling invalid user IDs
- ✅ Getting collateral snapshot with valid addresses
- ✅ Handling zero collateral scenarios
- ✅ Fetching ETH price from Price Oracle
- ✅ Price Oracle fallback mechanism

**Key Features Tested:**
- Cross-chain collateral aggregation
- USD conversion via Price Oracle service
- Per-chain breakdown generation
- Database snapshot storage
- Error handling

**Example:**
```python
@pytest.mark.asyncio
async def test_get_collateral_snapshot_valid_address(self, orchestrator_service):
    """Test getting collateral snapshot with valid Ethereum address."""
    # Mocks VaultClient and Price Oracle
    result = await orchestrator_service.get_collateral_snapshot(user_id=user_address)
    assert result["total_collateral_usd"] > 0
    assert "chains" in result
```

## Environment Setup

### Required Environment Variables

For tests that interact with blockchain (optional - tests handle missing RPC gracefully):

```bash
# RPC URLs for testnet chains
export ETH_RPC_URL="https://sepolia.infura.io/v3/YOUR_KEY"
export POLYGON_RPC_URL="https://rpc-amoy.polygon.technology"
export ARBITRUM_RPC_URL="https://sepolia-rollup.arbitrum.io/rpc"

# Private key for signing transactions (if testing bridge execution)
export DEPLOYER_PRIVATE_KEY="0xDEADBEEF..."

# Price Oracle Service URL (defaults to deployed service)
export PRICE_ORACLE_SERVICE_URL="https://price-oracle-service-ggats6pubq-uc.a.run.app"
```

### Test Configuration

The `conftest.py` file handles:
- Python path setup for imports
- Service directory path resolution
- PYTHONPATH environment variable configuration

**Key Configuration:**
```python
# conftest.py ensures service directory is first in sys.path
service_dir = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(service_dir))
os.environ['PYTHONPATH'] = service_dir_str
```

### Package Structure Requirements

For tests to work correctly, these `__init__.py` files must exist:

```
services/cross-chain-integration/
├── app/__init__.py                    # ✅ Required
├── infrastructure/__init__.py          # ✅ Required
├── infrastructure/db/__init__.py       # ✅ Required
├── app/core/__init__.py               # ✅ Required
├── app/integrations/__init__.py        # ✅ Required
└── app/services/__init__.py           # ✅ Required
```

## Test Coverage

### Current Coverage

**Total Tests: 22**

| Test File | Tests | Status |
|-----------|-------|--------|
| `test_retry_coordinator.py` | 7 | ✅ All Passing |
| `test_ccip_client.py` | 5 | ✅ All Passing |
| `test_vault_client.py` | 5 | ✅ All Passing |
| `test_orchestrator_collateral.py` | 5 | ✅ All Passing |

### Test Categories

1. **Unit Tests** (Mocked dependencies)
   - RetryCoordinator with mocked sessions
   - CCIPClient chain selector lookups
   - VaultClient initialization
   - OrchestratorService with mocked services

2. **Integration Tests** (Real dependencies when available)
   - CCIP message status queries (requires RPC)
   - Vault collateral queries (requires RPC)
   - Price Oracle integration (optional, has fallback)

3. **Error Handling Tests**
   - Missing RPC URLs
   - Invalid chain names
   - Unavailable vaults
   - Invalid user addresses

## Troubleshooting

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'app.core.retry_coordinator'`

**Solution:**
```bash
# Ensure you're running from service directory with PYTHONPATH set
cd services/cross-chain-integration
PYTHONPATH=. python -m pytest tests/
```

**Problem:** `ImportError: cannot import name 'BridgeProtocol' from 'infrastructure.db.models'`

**Solution:**
- Ensure `infrastructure/__init__.py` exists
- Ensure `infrastructure/db/__init__.py` exists
- Check that Python isn't finding infrastructure from other services

### Test Failures

**Problem:** Tests fail with "RPC URL not available"

**Solution:**
- Tests are designed to handle missing RPC URLs gracefully
- They should return `None` or `0` when RPC unavailable
- If tests are failing, check the test logic for proper error handling

**Problem:** Web3 connection errors

**Solution:**
- Tests should handle connection failures gracefully
- Check RPC URL validity if testing real connections
- Ensure testnet RPC endpoints are accessible

### Path Issues

**Problem:** Tests can't find modules

**Solution:**
1. Ensure you're in the service directory: `cd services/cross-chain-integration`
2. Set PYTHONPATH: `PYTHONPATH=. python -m pytest tests/`
3. Verify `conftest.py` is loading correctly
4. Check that all `__init__.py` files exist

## Recent Updates

### November 2024

**New Implementations:**
- ✅ RetryCoordinator now executes actual bridge retries (not just marking as pending)
- ✅ CCIPClient queries CCIP Router contracts via Web3
- ✅ AxelarClient improved with multiple endpoint fallback
- ✅ VaultClient for querying CrossChainVault contracts
- ✅ OrchestratorService.get_collateral_snapshot() fully implemented

**Test Infrastructure:**
- ✅ Added `conftest.py` for proper path configuration
- ✅ Added `infrastructure/__init__.py` and `infrastructure/db/__init__.py`
- ✅ Added `app/__init__.py` for package structure
- ✅ Improved path handling in all test files

**Test Improvements:**
- ✅ Changed skipped tests to run and verify graceful handling
- ✅ Fixed import path conflicts with other services
- ✅ All 22 tests now passing

## Best Practices

1. **Always run tests from service directory** with `PYTHONPATH=.`
2. **Use mocks for external dependencies** in unit tests
3. **Test error handling** for missing RPC URLs, invalid inputs, etc.
4. **Keep tests independent** - each test should be able to run alone
5. **Use descriptive test names** that explain what's being tested
6. **Mock expensive operations** like Web3 calls unless testing integration

## CI/CD Integration

For CI/CD pipelines, run tests with:

```bash
cd services/cross-chain-integration
PYTHONPATH=. python -m pytest tests/ -v --tb=short --junitxml=test-results.xml
```

This generates a JUnit XML report compatible with most CI systems.

## Additional Resources

- **Service README**: `services/cross-chain-integration/README.md`
- **Deployment Guide**: `services/cross-chain-integration/DEPLOYMENT_FIX.md`
- **Bridge Setup**: `services/cross-chain-integration/TESTNET_BRIDGE_SETUP.md`
- **Implementation Guide**: `services/cross-chain-integration/IMPLEMENTING_BRIDGE_INTEGRATION.md`

## Configuration Files

### conftest.py

Located at `services/cross-chain-integration/tests/conftest.py`, this file:
- Sets up Python path for imports
- Ensures service directory is first in `sys.path`
- Configures `PYTHONPATH` environment variable
- Must be present for tests to run correctly

### Package Structure (Required)

For tests to work, these `__init__.py` files must exist:
- `app/__init__.py`
- `infrastructure/__init__.py`
- `infrastructure/db/__init__.py`
- `app/core/__init__.py`
- `app/integrations/__init__.py`
- `app/services/__init__.py`

**Note:** All these files have been created as part of the test infrastructure setup.

## Deployment Configuration

### Cloud Build (cloudbuild.yaml)

The service is deployed via Google Cloud Build using `cloudbuild.yaml`:

```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', '${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_ARTIFACT_REGISTRY}/${_SERVICE_NAME}:latest', '.']

  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', '--all-tags', '${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_ARTIFACT_REGISTRY}/${_SERVICE_NAME}']

  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - '${_SERVICE_NAME}'
      - '--image'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_ARTIFACT_REGISTRY}/${_SERVICE_NAME}:latest'
      - '--region'
      - '${_REGION}'
      - '--set-cloudsql-instances'
      - 'fusion-prime:us-central1:fp-cross-chain-db-0c277aa9'
      - '--set-secrets'
      - 'DATABASE_URL=fp-cross-chain-db-connection-string:latest'
      - '--vpc-connector'
      - 'fusion-prime-connector'
      - '--vpc-egress'
      - 'private-ranges-only'
```

### Database Migrations

Database migrations are run via Cloud Run Job:

```bash
./scripts/run_cross_chain_migrations_vpc.sh
```

This script:
1. Builds the service Docker image
2. Creates/updates a Cloud Run Job
3. Executes Alembic migrations
4. Uses VPC connector for Cloud SQL access

### Environment Variables in Production

Secrets are managed via Google Secret Manager:
- `DATABASE_URL` - PostgreSQL connection string
- `DEPLOYER_PRIVATE_KEY` - Testnet deployer key (for bridge execution)
- `ETH_RPC_URL` - Ethereum Sepolia RPC (optional, can be in env vars)
- `POLYGON_RPC_URL` - Polygon Amoy RPC (optional, can be in env vars)

**Note:** RPC URLs can be set as environment variables or secrets, depending on deployment configuration.
