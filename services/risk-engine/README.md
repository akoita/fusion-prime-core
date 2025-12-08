# Risk Engine Service

**Team A: Risk & Analytics**

## Overview

The Risk Engine Service provides real-time risk calculation, portfolio analytics, and risk management capabilities for the Fusion Prime platform.

## Features

- **Portfolio Risk Assessment**: Real-time risk scoring for user portfolios
- **Collateral Valuation**: Multi-asset collateral risk calculation
- **Margin Requirements**: Dynamic margin calculation based on risk
- **Stress Testing**: Scenario-based risk analysis
- **Risk Metrics**: VaR, CVaR, correlation analysis
- **Risk API**: RESTful endpoints for risk queries

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Risk Engine   │    │   Analytics     │    │   Risk API      │
│   Service       │◄──►│   Pipeline      │◄──►│   Gateway       │
│   (FastAPI)     │    │   (Dataflow)    │    │   (FastAPI)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Risk Database │    │   BigQuery      │    │   Risk Cache    │
│   (PostgreSQL)  │    │   (Analytics)   │    │   (Redis)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Quick Start

```bash
# Install dependencies
cd services/risk-engine
pip install -r requirements.txt

# Run locally
python -m app.main

# Run tests
pytest tests/

# Build Docker image
docker build -t risk-engine .
```

## API Endpoints

### Risk Assessment
- `GET /risk/portfolio/{portfolio_id}` - Get portfolio risk score
- `POST /risk/calculate` - Calculate risk for custom portfolio
- `GET /risk/metrics` - Get risk metrics and KPIs

### Portfolio Analytics
- `GET /analytics/portfolio/{portfolio_id}/history` - Portfolio performance history
- `POST /analytics/stress-test` - Run stress test scenarios
- `GET /analytics/correlation` - Asset correlation analysis

### Risk Management
- `GET /risk/margin/{user_id}` - Get margin requirements
- `POST /risk/alerts` - Set up risk alerts
- `GET /risk/alerts/{user_id}` - Get user risk alerts

## Development

### Team A Responsibilities
1. **Risk Engine Service** - Core risk calculation engine
2. **Analytics Pipeline** - Data processing and analytics
3. **Risk Dashboard** - Risk visualization and monitoring
4. **Risk API** - RESTful API for risk operations

### Integration Points
- **Settlement Service**: Risk data for settlement decisions
- **Compliance Service**: Risk data for compliance monitoring
- **Frontend**: Risk data for user dashboards
- **Database**: Shared user and portfolio data

## Testing

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# E2E tests
pytest tests/e2e/

# Performance tests
pytest tests/performance/
```

## Deployment

```bash
# Build and deploy
make build-risk-engine
make deploy-risk-engine

# Check status
make status-risk-engine
make logs-risk-engine
```
