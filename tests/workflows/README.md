

# Environment-Agnostic Workflow Tests

## 🎯 Purpose

This directory contains **environment-agnostic workflow tests** that run identically across:
- **Local** - Anvil blockchain, Docker Compose services
- **Testnet** - Sepolia blockchain, GCP Cloud Run services
- **Production** - Ethereum mainnet, production GCP services

The **same test code** validates all environments - only **configuration** differs.

## 📁 Architecture

```
tests/
├── workflows/                       # ← Shared, environment-agnostic tests
│   ├── base_workflow_test.py       # Base class with environment detection
│   ├── escrow_creation_workflow.py # Escrow creation logic
│   ├── escrow_approval_workflow.py # Escrow approval logic
│   ├── escrow_release_workflow.py  # Payment release logic
│   └── escrow_refund_workflow.py   # Refund process logic
│
├── local/                           # ← Local environment wrappers
│   └── test_escrow_creation.py     # Imports escrow_creation_workflow
│
└── remote/testnet/                  # ← Testnet environment wrappers
    └── test_escrow_creation_shared.py  # Imports escrow_creation_workflow
```

## 🔑 Key Principle

**One Test, Multiple Environments**

```python
# tests/workflows/escrow_creation_workflow.py
class EscrowCreationWorkflow(BaseWorkflowTest):
    def test_escrow_creation_workflow(self):
        # This SAME code runs in ALL environments
        escrow = self.create_escrow(...)  # Works on Anvil OR Sepolia
        self.verify_settlement(...)        # Works local OR Cloud Run
        self.verify_risk(...)              # Works Docker OR GCP
```

```python
# tests/local/test_escrow_creation.py
os.environ["TEST_ENVIRONMENT"] = "local"
from tests.workflows.escrow_creation_workflow import EscrowCreationWorkflow

class TestLocalEscrowCreation(EscrowCreationWorkflow):
    pass  # Inherits test, runs in LOCAL environment
```

```python
# tests/remote/testnet/test_escrow_creation_shared.py
os.environ["TEST_ENVIRONMENT"] = "testnet"
from tests.workflows.escrow_creation_workflow import EscrowCreationWorkflow

class TestTestnetEscrowCreation(EscrowCreationWorkflow):
    pass  # SAME test, runs in TESTNET environment
```

## 🔧 How It Works

### 1. Environment Detection

The `BaseWorkflowTest` class automatically detects the environment:

```python
class BaseWorkflowTest:
    def setup_method(self):
        # Read TEST_ENVIRONMENT variable
        env_name = os.getenv("TEST_ENVIRONMENT", "local")
        self.environment = Environment(env_name)

        # Load environment-specific configuration
        self.config = self.env_manager.set_environment(self.environment)

        # Setup connections based on configuration
        self._setup_blockchain()      # Anvil OR Sepolia
        self._setup_services()        # localhost OR Cloud Run
        self._setup_test_accounts()  # Hardcoded OR env vars
```

### 2. Environment Configuration

Configuration comes from `tests/config/environments.yaml`:

```yaml
environment:
  local:
    blockchain:
      rpc_url: "http://localhost:8545"
      network: "anvil"
    services:
      settlement: "http://localhost:8000"

  testnet:
    blockchain:
      rpc_url: "${ETH_TESTNET_RPC_URL}"
      network: "sepolia"
    services:
      settlement: "${TESTNET_SETTLEMENT_SERVICE_URL}"
```

### 3. Environment-Aware Utilities

The base class provides helpers that adapt to the environment:

```python
# Automatic environment-specific wait times
self.wait_for_relayer_processing()
# → Local: waits 5 seconds
# → Testnet: waits 45 seconds

# Environment-aware service queries
self.query_service("Settlement", url, endpoint)
# → Local: queries localhost:8000
# → Testnet: queries Cloud Run URL

# Environment-specific test IDs
test_id = self.create_test_id("escrow-creation")
# → Local: "escrow-creation-local-1234567890"
# → Testnet: "escrow-creation-testnet-1234567890"
```

## 🚀 Running Tests

### Run Locally

```bash
# Set local environment
export TEST_ENVIRONMENT=local

# Run shared workflow tests in local environment
pytest tests/local/test_escrow_creation.py -v

# Or use existing local test scripts
./scripts/test/local.sh
```

### Run on Testnet

```bash
# Set testnet environment
export TEST_ENVIRONMENT=testnet

# Run shared workflow tests in testnet environment
pytest tests/remote/testnet/test_escrow_creation_shared.py -v

# Or use existing remote test scripts
./scripts/test/remote.sh
```

### Run Both (CI/CD)

```bash
# Run all environments sequentially
pytest tests/local/test_escrow_creation.py -v  # Local first
pytest tests/remote/testnet/test_escrow_creation_shared.py -v  # Then testnet
```

## 🎨 Creating New Workflow Tests

### Step 1: Create Shared Workflow

```python
# tests/workflows/my_new_workflow.py
from tests.workflows.base_workflow_test import BaseWorkflowTest

class MyNewWorkflow(BaseWorkflowTest):
    def test_my_new_workflow(self):
        """
        Environment-agnostic workflow test.

        Works in local, testnet, and production.
        """
        self.skip_if_no_private_key()

        test_id = self.create_test_id("my-workflow")

        # Your test logic here - works in ALL environments
        # Use self.web3, self.settlement_url, etc.
        # The base class handles environment differences
```

### Step 2: Create Local Wrapper

```python
# tests/local/test_my_new_workflow.py
import os
os.environ.setdefault("TEST_ENVIRONMENT", "local")

from tests.workflows.my_new_workflow import MyNewWorkflow

@pytest.mark.local
class TestLocalMyNewWorkflow(MyNewWorkflow):
    pass  # Inherits and runs in local environment
```

### Step 3: Create Testnet Wrapper

```python
# tests/remote/testnet/test_my_new_workflow_shared.py
import os
os.environ.setdefault("TEST_ENVIRONMENT", "testnet")

from tests.workflows.my_new_workflow import MyNewWorkflow

@pytest.mark.testnet
class TestTestnetMyNewWorkflow(MyNewWorkflow):
    pass  # Same test, runs in testnet environment
```

## ✅ Benefits

### 1. **DRY (Don't Repeat Yourself)**
- Write test logic ONCE
- Run in ALL environments
- No code duplication

### 2. **Consistency**
- Same validations everywhere
- Same test coverage
- Identical behavior verification

### 3. **Maintainability**
- Fix bugs in one place
- Update tests in one location
- Refactor once, apply everywhere

### 4. **Confidence**
- Local tests match production
- Catch environment-specific issues
- Validate real deployments

### 5. **Developer Experience**
- Easy to understand structure
- Clear separation of concerns
- Simple to add new tests

## 📊 Test Coverage Matrix

| Workflow | Local | Testnet | Production |
|----------|-------|---------|------------|
| Escrow Creation | ✅ | ✅ | 🔄 Pending |
| Escrow Approval | ✅ | ✅ | 🔄 Pending |
| Escrow Release | ✅ | ✅ | 🔄 Pending |
| Escrow Refund | 📋 TDD | 📋 TDD | 📋 TDD |
| Risk Calculation | ✅ | ✅ | 🔄 Pending |
| Compliance Check | ✅ | ✅ | 🔄 Pending |

Legend:
- ✅ Implemented and passing
- 🔄 Implemented, validation in progress
- 📋 TDD specification defined

## 🔍 Troubleshooting

### Test Fails Locally But Passes on Testnet

**Likely Cause**: Local services not running or misconfigured

```bash
# Check local services
docker-compose ps

# Restart services
docker-compose down && docker-compose up -d

# Check logs
docker-compose logs settlement-service
```

### Test Fails on Testnet But Passes Locally

**Likely Cause**: Environment variables not set

```bash
# Check required env vars for testnet
echo $ETH_TESTNET_RPC_URL
echo $TESTNET_SETTLEMENT_SERVICE_URL
echo $PAYER_PRIVATE_KEY

# Source environment file
source .env.testnet
```

### Environment Not Detected

**Likely Cause**: TEST_ENVIRONMENT not set

```bash
# Explicitly set environment
export TEST_ENVIRONMENT=local  # or testnet

# Or let it default to local
unset TEST_ENVIRONMENT
```

### Service Not Responding

**Check**: Service URL configuration in `tests/config/environments.yaml`

```yaml
environment:
  local:
    services:
      settlement: "http://localhost:8000"  # Check port

  testnet:
    services:
      settlement: "${TESTNET_SETTLEMENT_SERVICE_URL}"  # Check env var
```

## 🎯 Best Practices

### DO ✅

1. **Write environment-agnostic tests** in `tests/workflows/`
2. **Use base class utilities** (wait_for_relayer, query_service, etc.)
3. **Handle missing services gracefully** (skip or log warnings)
4. **Test against REAL systems** (no mocks, no simulations)
5. **Document environment requirements** in test docstrings

### DON'T ❌

1. **Don't hardcode URLs** - use `self.settlement_url` from config
2. **Don't hardcode private keys** - use `self.payer_private_key` from env
3. **Don't assume service availability** - check and skip if missing
4. **Don't duplicate test logic** - extend base class instead
5. **Don't mix environment-specific code** - keep in wrappers only

## 📚 Related Documentation

- **[TESTING.md](/TESTING.md)** - Complete testing guide
- **[tests/config/environments.yaml](/tests/config/environments.yaml)** - Environment configuration
- **[tests/common/environment_manager.py](/tests/common/environment_manager.py)** - Environment manager implementation
- **[TDD_APPROACH.md](/tests/remote/testnet/TDD_APPROACH.md)** - Test-driven development strategy

## 🤝 Contributing

When adding new workflow tests:

1. Create shared test in `tests/workflows/`
2. Add local wrapper in `tests/local/`
3. Add testnet wrapper in `tests/remote/testnet/`
4. Update this README with test status
5. Ensure tests pass in ALL environments

---

**Key Takeaway**: Write your test logic ONCE in `tests/workflows/`, then run it EVERYWHERE by just changing `TEST_ENVIRONMENT`. 🎯
