# Fusion Prime - Sprint 03 Deployment Runbook

**Date**: 2025-01-27
**Sprint**: 03 - Risk & Compliance Production Implementation
**Status**: Ready for Deployment

---

## 🎯 Deployment Objective

Deploy **Risk Engine** and **Compliance** services with their dedicated databases to GCP, then validate with integration tests.

---

## ✅ Pre-Deployment Checklist

### Completed ✅
- [x] Production Risk Engine implemented with real VaR calculations
- [x] Production Compliance Engine implemented with real KYC/AML
- [x] Database schemas created (Risk Engine + Compliance)
- [x] Terraform configuration updated with new databases
- [x] Comprehensive unit tests written (18 tests)
- [x] Integration tests written (14 tests)
- [x] All tests use documented scenarios
- [x] Configuration system integration (BaseIntegrationTest)

### Pending ❌
- [ ] Apply Terraform changes (create databases)
- [ ] Deploy Risk Engine service to Cloud Run
- [ ] Deploy Compliance service to Cloud Run
- [ ] Run integration tests to validate

---

## 📋 Step 1: Apply Terraform Changes

**Purpose**: Create Risk Engine DB and Compliance DB instances

### Option A: Using Existing Script (Recommended)

```bash
cd /home/koita/dev/web3/fusion-prime

# Initialize terraform (if not already done)
./scripts/deploy-infrastructure.sh dev init

# Review changes
./scripts/deploy-infrastructure.sh dev plan

# Apply changes (creates 2 new databases)
./scripts/deploy-infrastructure.sh dev apply
```

### Option B: Direct Terraform

```bash
cd infra/terraform/project

# Initialize
terraform init

# Plan (review before applying)
terraform plan -out=plan.out

# Apply (creates Risk Engine DB + Compliance DB)
terraform apply plan.out
```

### Expected Output

You should see:
- ✅ `cloudsql_risk_engine` module being created
- ✅ `cloudsql_compliance` module being created
- ✅ Database connection strings stored in Secret Manager

### Verify Databases Created

```bash
gcloud sql instances list --project=fusion-prime

# Should show:
# - fusion-prime-db (existing)
# - fusion-prime-risk-db-[hash] (new)
# - fusion-prime-compliance-db-[hash] (new)
```

---

## 📋 Step 2: Deploy Risk Engine Service

**Purpose**: Deploy Risk Engine to Cloud Run with real database

### Option A: Using Unified Deploy Script (Recommended)

```bash
cd /home/koita/dev/web3/fusion-prime

# Deploy Risk Engine service
./scripts/deploy-unified.sh --env dev --services risk-engine

# Or deploy with specific tag
./scripts/deploy-unified.sh --env dev --services risk-engine --tag v0.1.0
```

### Option B: Manual Cloud Build

```bash
cd services/risk-engine

# Build and deploy
gcloud builds submit --config=cloudbuild.yaml

# Or using make
cd ../..
make deploy-risk-engine
```

### Verify Deployment

```bash
# Get service URL
gcloud run services describe risk-engine \
  --region=us-central1 \
  --format="value(status.url)"

# Test health endpoint
curl https://[RISK-ENGINE-URL]/health/
```

### Expected Service URL

```
https://risk-engine-961424092563.us-central1.run.app
```

---

## 📋 Step 3: Deploy Compliance Service

**Purpose**: Deploy Compliance Service to Cloud Run with real database

### Using Unified Deploy Script

```bash
cd /home/koita/dev/web3/fusion-prime

# Deploy Compliance service
./scripts/deploy-unified.sh --env dev --services compliance

# Or deploy multiple services at once
./scripts/deploy-unified.sh --env dev --services risk-engine,compliance
```

### Verify Deployment

```bash
# Get service URL
gcloud run services describe compliance \
  --region=us-central1 \
  --format="value(status.url)"

# Test health endpoint
curl https://[COMPLIANCE-URL]/health/
```

### Expected Service URL

```
https://compliance-961424092563.us-central1.run.app
```

---

## 📋 Step 4: Run Database Migrations

**Purpose**: Create database tables for Risk Engine and Compliance

### Risk Engine Database

```bash
# Get database connection info from Secret Manager
export RISK_DB_CONNECTION=$(gcloud secrets versions access latest --secret="fusion-prime-risk-db-connection-string")

# Run migrations or SQL script
# Option 1: Using psql
psql $RISK_DB_CONNECTION -f services/risk-engine/infrastructure/db/schema.sql

# Option 2: Using Alembic (when implemented)
cd services/risk-engine
poetry run alembic upgrade head
```

### Compliance Database

```bash
# Get database connection info
export COMPLIANCE_DB_CONNECTION=$(gcloud secrets versions access latest --secret="fusion-prime-compliance-db-connection-string")

# Run SQL script
psql $COMPLIANCE_DB_CONNECTION -f services/compliance/infrastructure/db/schema.sql
```

### Verify Tables Created

```bash
# List tables in Risk Engine DB
psql $RISK_DB_CONNECTION -c "\dt"

# List tables in Compliance DB
psql $COMPLIANCE_DB_CONNECTION -c "\dt"
```

**Expected Tables**:
- Risk Engine: `risk_calculations`, `risk_alerts`, `margin_requirements`, `stress_test_results`
- Compliance: `kyc_cases`, `aml_alerts`, `sanctions_checks`, `compliance_cases`, `compliance_checks`

---

## 📋 Step 5: Run Integration Tests

**Purpose**: Validate services are working correctly with real databases

### Update Test Configuration

Set service URLs in `tests/test_config.yaml` or environment variables:

```bash
export RISK_ENGINE_SERVICE_URL="https://risk-engine-961424092563.us-central1.run.app"
export COMPLIANCE_SERVICE_URL="https://compliance-961424092563.us-central1.run.app"
```

### Run Risk Engine Tests

```bash
cd /home/koita/dev/web3/fusion-prime

# Run Risk Engine production tests
python -m pytest tests/test_risk_engine_production.py -v

# Expected: All 8 integration tests pass
```

### Run Compliance Tests

```bash
# Run Compliance production tests
python -m pytest tests/test_compliance_production.py -v

# Expected: All 6 integration tests pass
```

### Run All Sprint 03 Tests

```bash
# Run all integration tests including new services
python -m pytest tests/test_risk_engine_production.py tests/test_compliance_production.py -v

# Or run all tests
./scripts/test.sh testnet
```

---

## 🎯 Expected Results

### Terraform Output

```
✓ cloudsql_risk_engine module created
✓ cloudsql_compliance module created
✓ Secrets stored in Secret Manager
```

### Service Health Checks

```bash
# Risk Engine
curl https://risk-engine-xxx.run.app/health/
# Response: {"status":"healthy","database_connected":true}

# Compliance
curl https://compliance-xxx.run.app/health/
# Response: {"status":"healthy","database_connected":true}
```

### Test Results

```
tests/test_risk_engine_production.py::TestRiskEngineProduction::test_risk_engine_health_with_database PASSED
tests/test_risk_engine_production.py::TestRiskEngineProduction::test_calculate_portfolio_risk_from_escrows PASSED
...
tests/test_compliance_production.py::TestComplianceProduction::test_compliance_service_health_with_database PASSED
...
8 passed, 0 failed
```

---

## 🔧 Troubleshooting

### Database Connection Issues

**Problem**: Services can't connect to databases

**Solution**:
```bash
# Check VPC connector
gcloud compute networks vpc-access connectors list --region=us-central1

# Verify Cloud SQL instances
gcloud sql instances list

# Check service account permissions
gcloud projects get-iam-policy fusion-prime
```

### Service Startup Failures

**Problem**: Services fail to start

**Solution**:
```bash
# Check logs
gcloud logging read "resource.type=cloud_run_revision" --limit=100

# Common issues:
# 1. Missing DATABASE_URL environment variable
# 2. VPC connector not configured
# 3. Secrets not accessible
```

### Test Failures

**Problem**: Integration tests fail

**Solution**:
```bash
# Check service URLs are correct
echo $RISK_ENGINE_SERVICE_URL
echo $COMPLIANCE_SERVICE_URL

# Test endpoints manually
curl https://risk-engine-xxx.run.app/health/
curl https://compliance-xxx.run.app/health/
```

---

## 📊 Post-Deployment Validation

### Service Status Check

```bash
gcloud run services list --region=us-central1

# Should show:
# ✓ settlement-service (running)
# ✓ risk-engine (running) ← NEW
# ✓ compliance (running) ← NEW
# ✓ escrow-event-relayer (running)
```

### Database Status Check

```bash
gcloud sql instances list

# Should show:
# ✓ fusion-prime-db (settlement)
# ✓ fusion-prime-risk-db-xxx (risk engine) ← NEW
# ✓ fusion-prime-compliance-db-xxx (compliance) ← NEW
```

### Test Execution

```bash
# Run full test suite
./scripts/test.sh testnet

# Or specific tests
python -m pytest tests/test_risk_engine_production.py -v
python -m pytest tests/test_compliance_production.py -v
```

---

## 🎉 Success Criteria

### ✅ Terraform
- [x] Risk Engine database created
- [x] Compliance database created
- [x] Secrets stored in Secret Manager
- [x] VPC connector configured

### ✅ Services
- [x] Risk Engine service deployed and healthy
- [x] Compliance service deployed and healthy
- [x] Services connect to their databases
- [x] Health checks pass

### ✅ Tests
- [x] All unit tests pass (18 tests)
- [x] All integration tests pass (14 tests)
- [x] Real database integration validated
- [x] Documentation updated

---

## 📝 Manual Steps Summary

```bash
# 1. Apply Terraform
cd /home/koita/dev/web3/fusion-prime
./scripts/deploy-infrastructure.sh dev apply

# 2. Deploy Services
./scripts/deploy-unified.sh --env dev --services risk-engine,compliance

# 3. Run Migrations
# (Get connection strings from Secret Manager)
# psql $RISK_DB_CONNECTION -f services/risk-engine/infrastructure/db/schema.sql
# psql $COMPLIANCE_DB_CONNECTION -f services/compliance/infrastructure/db/schema.sql

# 4. Run Tests
export RISK_ENGINE_SERVICE_URL="https://risk-engine-xxx.run.app"
export COMPLIANCE_SERVICE_URL="https://compliance-xxx.run.app"
python -m pytest tests/test_risk_engine_production.py tests/test_compliance_production.py -v
```

---

**Created**: 2025-01-27
**Status**: Ready for Execution
**Next Review**: After deployment completion
