# Risk Analytics Pipeline Architecture

## Overview

The Risk Analytics Pipeline provides real-time portfolio exposure monitoring, cross-margin calculations, and liquidation triggers for the Fusion Prime platform. It consumes settlement events, on-chain position data, and market feeds to materialize risk metrics in BigQuery for analytics and dashboards.

## Architecture Components

### 1. Data Sources

#### Settlement Events (Pub/Sub)
- **Topic**: `settlement.events.v1`
- **Schema**: Protobuf `SettlementEvent`
- **Contains**: Command status updates, settlement confirmations, failures

#### On-Chain Position Data
- **Source**: Blockchain event relayers
- **Events**: `EscrowReleased`, `CollateralDeposited`, `CollateralWithdrawn`
- **Chains**: Ethereum, Polygon, Arbitrum, Base

#### Market Data Feed
- **Source**: Price oracle aggregator (Chainlink, Pyth, internal feeds)
- **Frequency**: 10-second intervals for real-time risk
- **Assets**: All supported stablecoins, crypto assets, and tokenized securities

### 2. Stream Processing (Dataflow)

#### Risk Computation Pipeline
- **Technology**: Apache Beam on Cloud Dataflow
- **Processing**: Windowed aggregations (1-minute, 5-minute, 1-hour, 1-day)
- **Computations**:
  - Portfolio-level exposure by account
  - Cross-chain collateral utilization
  - Margin health score (0-100)
  - Value-at-Risk (VaR) and Expected Shortfall (ES)
  - Liquidation thresholds

#### Event-Driven Triggers
- **Margin Call Alerts**: When health score drops below 30
- **Liquidation Triggers**: When health score drops below 15
- **Settlement Risk**: When settlement windows exceed thresholds

### 3. Data Warehouse (BigQuery)

#### Schema Design

**Table: `risk.portfolio_exposures`**
```sql
CREATE TABLE risk.portfolio_exposures (
  account_ref STRING NOT NULL,
  snapshot_timestamp TIMESTAMP NOT NULL,
  total_collateral_usd NUMERIC(38, 18),
  total_borrow_usd NUMERIC(38, 18),
  available_credit_usd NUMERIC(38, 18),
  margin_health_score FLOAT64,
  var_1d_99_usd NUMERIC(38, 18),
  expected_shortfall_1d_99_usd NUMERIC(38, 18),
  liquidation_price_btc NUMERIC(38, 18),
  liquidation_price_eth NUMERIC(38, 18),
  chains ARRAY<STRING>,
  last_settlement_timestamp TIMESTAMP,
  PRIMARY KEY (account_ref, snapshot_timestamp)
)
PARTITION BY DATE(snapshot_timestamp)
CLUSTER BY account_ref;
```

**Table: `risk.asset_exposures`**
```sql
CREATE TABLE risk.asset_exposures (
  account_ref STRING NOT NULL,
  asset_symbol STRING NOT NULL,
  chain_id STRING NOT NULL,
  snapshot_timestamp TIMESTAMP NOT NULL,
  balance_native NUMERIC(38, 18),
  balance_usd NUMERIC(38, 18),
  price_usd NUMERIC(38, 18),
  utilization_pct FLOAT64,
  PRIMARY KEY (account_ref, asset_symbol, chain_id, snapshot_timestamp)
)
PARTITION BY DATE(snapshot_timestamp)
CLUSTER BY account_ref, asset_symbol;
```

**Table: `risk.margin_events`**
```sql
CREATE TABLE risk.margin_events (
  event_id STRING NOT NULL PRIMARY KEY,
  account_ref STRING NOT NULL,
  event_type STRING NOT NULL, -- MARGIN_CALL, LIQUIDATION, RECOVERY
  event_timestamp TIMESTAMP NOT NULL,
  margin_health_before FLOAT64,
  margin_health_after FLOAT64,
  trigger_reason STRING,
  resolution_status STRING,
  resolved_at TIMESTAMP
)
PARTITION BY DATE(event_timestamp)
CLUSTER BY account_ref, event_type;
```

#### Materialized Views
- **Recent Portfolio Exposures**: Last 24 hours, refreshed every 1 minute
- **Aggregate Risk Metrics**: Platform-wide exposure, refreshed every 5 minutes
- **Historical VaR Trends**: Daily VaR/ES over trailing 90 days

### 4. Risk Dashboard (Frontend)

#### Key Views

**Portfolio Risk Overview**
- Multi-chain collateral visualization
- Real-time margin health gauge
- Position breakdown by asset and chain
- Historical PnL chart

**Margin Monitoring**
- Live margin calls and liquidation alerts
- Account-level risk ranking
- Concentration risk heatmap

**Analytics & Reports**
- VaR/ES trends
- Settlement latency distribution
- Cross-chain utilization patterns
- Regulatory reporting exports

#### Technology Stack
- **Framework**: React + TypeScript
- **Charting**: Recharts / Chart.js
- **State Management**: React Query for BigQuery API
- **Real-time**: WebSocket connection to backend service

### 5. Alert & Notification Service

#### Alert Rules Engine
- **Technology**: Cloud Functions + Pub/Sub
- **Triggers**:
  - Health score below threshold
  - Rapid collateral drawdown (>20% in 5 minutes)
  - Settlement failures
  - Oracle price deviation

#### Notification Channels
- Email (SendGrid)
- SMS (Twilio)
- Webhook callbacks
- In-app notifications

## Data Flow

```
Settlement Service → Pub/Sub (settlement.events.v1)
                          ↓
                    Dataflow Pipeline
                          ↓
                  BigQuery (risk.*)
                          ↓
            Dashboard API / Frontend
```

```
Blockchain Events → Event Relayer → Pub/Sub (chain.events.v1)
                                         ↓
                                   Dataflow Pipeline
                                         ↓
                                 BigQuery (risk.*)
```

```
Market Data → Price Oracle Service → Pub/Sub (market.prices.v1)
                                          ↓
                                    Dataflow Pipeline
                                          ↓
                                  BigQuery (risk.*)
```

## Implementation Phases

### Phase 1: Foundation (Weeks 1-2)
- [x] Settlement event schema and Pub/Sub topics
- [ ] BigQuery dataset and tables
- [ ] Basic Dataflow pipeline for settlement ingestion
- [ ] Simple dashboard with portfolio exposure

### Phase 2: Risk Metrics (Weeks 3-4)
- [ ] VaR/ES computation in Dataflow
- [ ] Margin health score calculation
- [ ] Liquidation threshold monitoring
- [ ] Alert service integration

### Phase 3: Advanced Analytics (Weeks 5-6)
- [ ] Historical trend analysis
- [ ] Concentration risk metrics
- [ ] Regulatory reporting templates
- [ ] Performance optimization

### Phase 4: Production Hardening (Weeks 7-8)
- [ ] Chaos engineering tests
- [ ] Disaster recovery playbooks
- [ ] SLO dashboards and alerting
- [ ] Security audit and penetration testing

## Configuration

### Environment Variables
```bash
# Dataflow
GCP_PROJECT=fusion-prime-prod
DATAFLOW_REGION=us-central1
DATAFLOW_TEMP_LOCATION=gs://fusion-prime-dataflow-temp
DATAFLOW_STAGING_LOCATION=gs://fusion-prime-dataflow-staging

# BigQuery
BIGQUERY_DATASET=risk
BIGQUERY_WRITE_DISPOSITION=WRITE_APPEND

# Pub/Sub
SETTLEMENT_EVENTS_SUBSCRIPTION=risk-pipeline-settlement-events
CHAIN_EVENTS_SUBSCRIPTION=risk-pipeline-chain-events
MARKET_PRICES_SUBSCRIPTION=risk-pipeline-market-prices

# Alert Thresholds
MARGIN_CALL_THRESHOLD=30.0
LIQUIDATION_THRESHOLD=15.0
RAPID_DRAWDOWN_PCT=20.0
RAPID_DRAWDOWN_WINDOW_MIN=5
```

## Monitoring & Observability

### Key Metrics
- **Pipeline Latency**: End-to-end latency from event to BigQuery insert (target: <30s p99)
- **Data Freshness**: Age of most recent snapshot in BigQuery (target: <60s)
- **Alert Delivery**: Time from trigger to notification (target: <10s)
- **Pipeline Throughput**: Events processed per second (target: >1000)

### SLOs
- **Dashboard Availability**: 99.9% uptime
- **Risk Calculation Accuracy**: 99.99% correctness (verified via golden dataset)
- **Alert Reliability**: 99.95% delivery rate

### Dashboards
- **Operational Dashboard**: Pipeline health, Dataflow job status, BigQuery query performance
- **Business Dashboard**: Portfolio risk metrics, margin calls, liquidation events

## Security & Compliance

### Data Access Control
- **BigQuery**: Row-level security by account ownership
- **Dashboard**: Role-based access control (RBAC) via Identity-Aware Proxy
- **API**: OAuth 2.0 with scoped permissions

### Audit Trail
- All risk computations logged with input data snapshots
- Margin call and liquidation decisions stored in `risk.margin_events`
- Access logs retained for 7 years (regulatory requirement)

### Privacy
- PII segregated from risk metrics (account_ref is pseudonymized)
- Data retention: 90 days hot storage, 7 years cold storage (Cloud Storage)

## References
- [Settlement Service README](../../services/settlement/README.md)
- [Protobuf Schemas](../../analytics/schemas/pubsub/fusionprime/settlement/v1/settlement.proto)
- [GCP Dataflow Best Practices](https://cloud.google.com/dataflow/docs/guides/best-practices)
- [BigQuery Schema Design](https://cloud.google.com/bigquery/docs/best-practices-performance-compute)

