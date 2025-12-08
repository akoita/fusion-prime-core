# Fusion Prime - Testing Guide

**Complete testing strategy for all environments**
**Last Updated**: 2025-10-27

---

## Quick Start

### Run All Sprint 03 Integration Tests

```bash
# Set service URLs
export RISK_ENGINE_SERVICE_URL="https://risk-engine-961424092563.us-central1.run.app"
export COMPLIANCE_SERVICE_URL="https://compliance-ggats6pubq-uc.a.run.app"
export ALERT_NOTIFICATION_SERVICE_URL="https://alert-notification-961424092563.us-central1.run.app"

# Run Sprint 03 tests
cd tests
pytest test_margin_health_integration.py -v
pytest test_alert_notification_integration.py -v
pytest test_end_to_end_margin_alerting.py -v

# Or run all Sprint 03 tests at once
pytest test_margin_health_integration.py test_alert_notification_integration.py test_end_to_end_margin_alerting.py -v
```

---

## Sprint 03 Test Coverage

### 1. Margin Health Integration Tests (`test_margin_health_integration.py`)

**7 test scenarios covering:**
- Basic margin health calculation
- Margin call detection (< 30%)
- Liquidation detection (< 15%)
- Batch processing for multiple users
- Multi-asset portfolios (ETH + BTC)
- Margin events API
- Margin statistics API

**What's tested:**
- Health score formula: `(collateral_usd - borrow_usd) / borrow_usd * 100`
- Status classification: HEALTHY, WARNING, MARGIN_CALL, LIQUIDATION
- Real-time USD valuation from Price Oracle
- Event detection and alerting
- Batch processing efficiency

### 2. Alert Notification Integration Tests (`test_alert_notification_integration.py`)

**7 test scenarios covering:**
- Service health check
- Manual notification sending
- User preferences management
- Notification history retrieval
- Severity-based routing (CRITICAL, HIGH, MEDIUM, LOW)
- Detailed health check
- Multi-channel delivery (email, SMS, webhook)

### 3. End-to-End Margin Alerting Tests (`test_end_to_end_margin_alerting.py`)

**4 test scenarios covering:**
- Complete margin call workflow
- Complete liquidation workflow
- Batch margin monitoring
- All services health check

**Complete pipeline tested:**
1. Risk Engine calculates margin health
2. Margin event detected
3. Alert published to Pub/Sub (`alerts.margin.v1`)
4. Alert Notification Service consumes
5. Notification delivered via multiple channels

---

## Test Environment Configuration

### Deployed Services (Production)

Test against deployed Cloud Run services:

```bash
export RISK_ENGINE_SERVICE_URL="https://risk-engine-961424092563.us-central1.run.app"
export COMPLIANCE_SERVICE_URL="https://compliance-ggats6pubq-uc.a.run.app"
export ALERT_NOTIFICATION_SERVICE_URL="https://alert-notification-961424092563.us-central1.run.app"
```

### Local Services (Development)

Test against local Docker Compose services:

```bash
export RISK_ENGINE_SERVICE_URL="http://localhost:8001"
export COMPLIANCE_SERVICE_URL="http://localhost:8002"
export ALERT_NOTIFICATION_SERVICE_URL="http://localhost:8003"
```

---

## Running Tests

### All Sprint 03 Tests

```bash
pytest tests/test_margin_health_integration.py \
       tests/test_alert_notification_integration.py \
       tests/test_end_to_end_margin_alerting.py -v
```

### Specific Test Categories

```bash
# Margin health tests only
pytest tests/test_margin_health_integration.py -v

# Alert notification tests only
pytest tests/test_alert_notification_integration.py -v

# End-to-end workflow tests
pytest tests/test_end_to_end_margin_alerting.py -v
```

### With Coverage

```bash
pytest tests/test_margin_health_integration.py \
       tests/test_alert_notification_integration.py \
       tests/test_end_to_end_margin_alerting.py \
       --cov=services/risk-engine \
       --cov=services/alert-notification \
       --cov-report=html
```

---

## Test Documentation

For detailed testing documentation, see:
- **[tests/SPRINT_03_INTEGRATION_TESTS.md](./tests/SPRINT_03_INTEGRATION_TESTS.md)** - Complete test documentation
- **[docs/operations/TESTING.md](./docs/operations/TESTING.md)** - Full testing guide

---

## What's Being Validated

### Margin Health Features ✅
- Health score calculation accuracy
- USD valuation from real prices
- Status classification (4 levels)
- Event detection logic
- Batch processing
- Multi-asset support
- Historical events

### Alert Notification Features ✅
- Service health and availability
- Manual notification triggering
- User preferences management
- Notification history
- Severity-based routing
- Multi-channel delivery

### End-to-End Workflow ✅
- Complete alert pipeline
- Risk Engine → Pub/Sub → Alerts
- Service integration
- Batch monitoring

**Total**: 18 test scenarios, 1,036 lines of test code

---

## Success Criteria

Tests pass if:
- ✅ All service health checks return 200
- ✅ Margin health calculations are accurate
- ✅ Status classifications are correct
- ✅ Events detected appropriately
- ✅ Notifications delivered successfully
- ✅ End-to-end workflow completes

---

For more information, see the [full testing documentation](./docs/operations/TESTING.md).
