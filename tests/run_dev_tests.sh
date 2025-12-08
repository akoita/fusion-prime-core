#!/bin/bash
# Helper script to run tests against dev environment

set -e

# Load environment from .env.dev using Python (handles special characters safely)
if [ -f ".env.dev" ]; then
    echo "Loading environment from .env.dev..."
    eval "$(python3 -c "
import os
with open('.env.dev') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            # Escape single quotes in value for bash
            value = value.replace(\"'\", \"'\\\\''\" )
            print(f\"export {key}='{value}'\")
")"
else
    echo "Error: .env.dev not found"
    exit 1
fi

# Set test environment
export TEST_ENVIRONMENT=dev

# Show configuration
echo ""
echo "==================================="
echo "Environment Configuration:"
echo "==================================="
echo "TEST_ENVIRONMENT: $TEST_ENVIRONMENT"
echo "SETTLEMENT_SERVICE_URL: $SETTLEMENT_SERVICE_URL"
echo "RISK_ENGINE_SERVICE_URL: $RISK_ENGINE_SERVICE_URL"
echo "COMPLIANCE_SERVICE_URL: $COMPLIANCE_SERVICE_URL"
echo "ESCROW_FACTORY_ADDRESS: $ESCROW_FACTORY_ADDRESS"
echo "CHAIN_ID: $CHAIN_ID"
echo "==================================="
echo ""

# Run tests based on argument
case "${1:-all}" in
    connectivity)
        echo "Running connectivity tests..."
        pytest tests/test_blockchain_connectivity.py tests/test_database_connectivity.py -v
        ;;
    config)
        echo "Running configuration tests..."
        pytest tests/test_environment_configuration.py tests/test_pubsub_configuration.py tests/test_auto_config.py -v
        ;;
    production)
        echo "Running production service tests..."
        pytest tests/test_compliance_production.py tests/test_risk_engine_production.py -v
        ;;
    integration)
        echo "Running integration tests..."
        pytest tests/test_service_integration.py tests/test_pubsub_integration.py tests/test_margin_health_integration.py tests/test_alert_notification_integration.py tests/test_end_to_end_margin_alerting.py -v
        ;;
    workflow)
        echo "Running E2E workflow tests (WARNING: Uses real testnet gas)..."
        echo "This will create actual blockchain transactions on Sepolia testnet"
        echo ""
        echo "Step 1: Checking relayer readiness..."
        pytest tests/test_relayer_readiness.py -v -s
        if [ $? -ne 0 ]; then
            echo ""
            echo "❌ RELAYER READINESS CHECK FAILED"
            echo "   Workflow tests require a healthy, caught-up relayer"
            echo "   Fix relayer issues before running workflow tests"
            exit 1
        fi
        echo ""
        echo "✅ Relayer is ready. Proceeding with workflow tests..."
        echo ""
        pytest tests/test_escrow_creation_workflow.py tests/test_escrow_approval_workflow.py tests/test_escrow_release_workflow.py tests/test_escrow_refund_workflow.py -v -s
        ;;
    quick)
        echo "Running quick smoke tests..."
        pytest tests/test_blockchain_connectivity.py tests/test_database_connectivity.py -v
        ;;
    fast)
        echo "Running fast test suite (excludes slow workflow tests)..."
        echo "This skips tests marked with @pytest.mark.slow"
        pytest tests/ -v --ignore=tests/scripts --ignore=tests/workflows --ignore=tests/common -m "not slow"
        ;;
    all)
        echo "Running all tests except workflows..."
        pytest tests/test_*_connectivity.py tests/test_*_configuration.py tests/test_auto_config.py tests/test_*_production.py tests/test_service_integration.py tests/test_pubsub_integration.py tests/test_*_integration.py -v
        ;;
    complete)
        echo "Running COMPLETE test suite including workflows..."
        pytest tests/ -v --ignore=tests/scripts --ignore=tests/workflows --ignore=tests/common
        ;;
    *)
        echo "Usage: $0 {connectivity|config|production|integration|workflow|quick|fast|all|complete}"
        echo ""
        echo "Test Categories:"
        echo "  connectivity  - Blockchain & database connectivity (~5 sec)"
        echo "  config        - Environment & configuration validation (~5 sec)"
        echo "  production    - Production service tests with DB (~15 sec)"
        echo "  integration   - Cross-service & margin integration (~30 sec)"
        echo "  workflow      - E2E workflows (uses testnet gas, ~90 sec)"
        echo "  quick         - Quick smoke tests (~3 sec)"
        echo "  fast          - All tests except slow workflows (~2-3 min)"
        echo "  all           - All tests except workflows (~50 sec)"
        echo "  complete      - Everything including workflows (~30-40 min)"
        exit 1
        ;;
esac
