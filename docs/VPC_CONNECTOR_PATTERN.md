# VPC Connector Pattern for Database-Connected Cloud Run Services

**Date**: 2025-10-31
**Author**: Infrastructure Team
**Status**: Active Pattern

## Overview

This document describes the VPC connector pattern used in Fusion Prime to enable Cloud Run services to access Cloud SQL databases via private IP addresses. This is a critical infrastructure requirement for any service that needs to connect to Cloud SQL.

## Why VPC Connectors Are Required

### The Problem

Cloud Run services run in a fully managed environment and by default:
- Cannot access resources on private VPC networks
- Cannot connect to Cloud SQL instances via private IP
- Must use public IP or Cloud SQL Proxy

### The Solution

**VPC Access Connector** provides a bridge between Cloud Run and your VPC network, enabling:
- Direct access to Cloud SQL via private IP (faster, more secure)
- Lower latency database connections
- Reduced Cloud SQL Proxy overhead
- Better network isolation

## Infrastructure Architecture

### VPC Connector (Terraform-Managed)

The VPC connector is defined in Terraform and automatically provisioned:

**File**: `infra/terraform/modules/network/main.tf` (lines 37-45)

```hcl
resource "google_vpc_access_connector" "connector" {
  name          = "fusion-prime-connector"
  region        = var.region
  ip_cidr_range = var.vpc_connector_cidr  # 10.8.0.0/28
  network       = google_compute_network.vpc.name
  min_instances = 2
  max_instances = 3
  machine_type  = "e2-micro"
}
```

**Key Details**:
- **Name**: `fusion-prime-connector` (used in all Cloud Run services)
- **Region**: `us-central1` (must match Cloud Run service region)
- **CIDR**: `10.8.0.0/28` (16 IP addresses for connector instances)
- **Instances**: 2-3 auto-scaling connector instances
- **Machine Type**: `e2-micro` (sufficient for database traffic)

### Cloud SQL Databases (Terraform-Managed)

Three databases are defined in `infra/terraform/project/cloudsql.tf`:

1. **Settlement Database**: `fp-settlement-db-590d836a`
   - Private IP: Auto-assigned via VPC peering
   - Database: `settlement_db`
   - User: `settlement_user`

2. **Risk Engine Database**: `fp-risk-db-1d929830`
   - Private IP: Auto-assigned via VPC peering
   - Database: `risk_db`
   - User: `risk_user`

3. **Compliance Database**: `fp-compliance-db-0b9f2040`
   - Private IP: Auto-assigned via VPC peering
   - Database: `compliance_db`
   - User: `compliance_user`

## Service Configuration Pattern

### Required Cloud Build Configuration

For any Cloud Run service that needs database access, add these flags to the `gcloud run deploy` command in `cloudbuild.yaml`:

```yaml
- name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
  entrypoint: 'gcloud'
  args: [
    'run', 'deploy', '<service-name>',
    '--image', 'us-central1-docker.pkg.dev/$PROJECT_ID/services/<service-name>:latest',
    '--region', 'us-central1',
    '--platform', 'managed',

    # Database configuration
    '--set-secrets', 'DATABASE_URL=<secret-name>:latest',
    '--add-cloudsql-instances', 'fusion-prime:us-central1:<instance-name>',

    # VPC connector configuration (REQUIRED!)
    '--vpc-connector', 'fusion-prime-connector',
    '--vpc-egress', 'private-ranges-only',

    # Other flags...
  ]
```

### Configuration by Service

| Service | Instance | Secret | Cloud Build File |
|---------|----------|--------|------------------|
| Settlement | `fp-settlement-db-590d836a` | `fp-settlement-db-connection-string` | `services/settlement/cloudbuild.yaml:53-54` |
| Risk Engine | `fp-risk-db-1d929830` | `fp-risk-db-connection-string` | `services/risk-engine/cloudbuild.yaml:53-54` |
| Compliance | `fp-compliance-db-0b9f2040` | `fp-compliance-db-connection-string` | `services/compliance/cloudbuild.yaml:53-54` |
| Alert Notification | N/A (no database) | N/A | `services/alert-notification/cloudbuild.yaml:52-55` |

**Note**: Alert Notification Service has VPC connector for potential future database access.

## VPC Egress Modes

Two egress modes are available:

### `private-ranges-only` (Recommended)

- Routes only private IP traffic through VPC connector
- Public internet traffic goes directly from Cloud Run
- **Lower cost** (only internal traffic uses connector)
- **Better performance** for public APIs
- **Use this for database-connected services**

### `all-traffic`

- Routes all traffic through VPC connector
- Useful for services that need to access other private VPC resources
- Higher cost and latency
- Only use if specifically required

## Adding VPC Connector to a New Service

### Step 1: Update Cloud Build Configuration

Edit `services/<service-name>/cloudbuild.yaml` and add VPC connector flags:

```yaml
- name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
  entrypoint: 'gcloud'
  args: [
    # ... existing args ...
    '--add-cloudsql-instances', 'fusion-prime:us-central1:<instance-name>',
    '--vpc-connector', 'fusion-prime-connector',
    '--vpc-egress', 'private-ranges-only'
  ]
```

### Step 2: Update Database Connection String

Ensure the service uses private IP connection format:

```bash
# Cloud Run (Unix socket with VPC connector)
DATABASE_URL=postgresql+asyncpg://<user>:<password>@/<database>?host=/cloudsql/<project>:<region>:<instance>

# Example for Risk Engine
DATABASE_URL=postgresql+asyncpg://risk_user:PASSWORD@/risk_db?host=/cloudsql/fusion-prime:us-central1:fp-risk-db-1d929830
```

### Step 3: Deploy and Verify

```bash
# Build and deploy
cd services/<service-name>
gcloud builds submit --config=cloudbuild.yaml --project=fusion-prime

# Verify VPC connector is configured
gcloud run services describe <service-name> \
  --project=fusion-prime \
  --region=us-central1 \
  --format="value(spec.template.metadata.annotations['run.googleapis.com/vpc-access-connector'])"

# Expected output: fusion-prime-connector
```

### Step 4: Test Database Connectivity

```bash
# Check service logs for successful database connection
gcloud run services logs read <service-name> \
  --project=fusion-prime \
  --region=us-central1 \
  --limit=50 | grep -i "database\|connection\|pool"
```

## Troubleshooting

### Issue: Service Cannot Connect to Database

**Symptoms**:
- `asyncio.exceptions.CancelledError`
- `TimeoutError` during database connection
- "Failed to persist" errors in logs

**Diagnosis**:
```bash
# Check if VPC connector is configured
gcloud run services describe <service-name> \
  --format="get(spec.template.metadata.annotations)" | grep vpc

# Check Cloud SQL instance is accessible
gcloud sql instances describe <instance-name> \
  --project=fusion-prime \
  --format="get(ipAddresses)"
```

**Resolution**:
1. Verify VPC connector flags are in `cloudbuild.yaml`
2. Redeploy the service
3. Check service logs for connection success

### Issue: High Connector Costs

**Symptoms**:
- Unexpected VPC Access Connector charges
- High egress traffic costs

**Diagnosis**:
```bash
# Check VPC egress configuration
gcloud run services describe <service-name> \
  --format="get(spec.template.metadata.annotations['run.googleapis.com/vpc-access-egress'])"
```

**Resolution**:
- Ensure `--vpc-egress private-ranges-only` is set
- Review services that don't need VPC connector
- Consider removing connector from services without database access

### Issue: Connector Scaling

**Symptoms**:
- Connection timeouts during high traffic
- Connector instance limits reached

**Resolution**:
Update connector configuration in Terraform:

```hcl
resource "google_vpc_access_connector" "connector" {
  # ...
  min_instances = 3  # Increase from 2
  max_instances = 5  # Increase from 3
  machine_type  = "e2-standard-4"  # Upgrade if needed
}
```

Apply with `terraform apply` in `infra/terraform/project/`.

## Historical Context

### Original Issue (2025-10-31)

Three Risk DB tables had no data despite tests passing:
- `margin_health_snapshots`
- `margin_events`
- `alert_notifications`

**Root Cause**: Risk Engine and Alert Notification services were missing VPC connector configuration, preventing ALL database writes.

**Resolution**:
1. Added VPC connectors via `gcloud` (tactical fix)
2. Updated all `cloudbuild.yaml` files (strategic fix)
3. Documented pattern (this document)

### Files Modified (2025-10-31)

1. `services/risk-engine/cloudbuild.yaml` - Added VPC connector (lines 53-54)
2. `services/settlement/cloudbuild.yaml` - Added VPC connector (lines 53-54)
3. `services/compliance/cloudbuild.yaml` - Added VPC connector (lines 53-54)
4. `services/alert-notification/cloudbuild.yaml` - Added VPC connector (lines 52-55)

## Best Practices

1. **Always Configure VPC Connector** for database-connected services
2. **Use `private-ranges-only` Egress** unless you need all traffic routed through VPC
3. **Test Database Connectivity** after deployment by checking service logs
4. **Update Cloud Build Config** not manual gcloud commands (avoids infrastructure drift)
5. **Document Service Requirements** in service README files
6. **Monitor Connector Usage** via Cloud Monitoring

## Related Documentation

- [Cloud Run VPC Access](https://cloud.google.com/run/docs/configuring/vpc-connectors)
- [Cloud SQL for Cloud Run](https://cloud.google.com/sql/docs/postgres/connect-run)
- [Fusion Prime Database Architecture](./DATABASE_ARCHITECTURE.md)
- [Risk DB Persistence Investigation](/tmp/risk_db_persistence_investigation_summary.md)

## Checklist for New Database-Connected Services

- [ ] Database instance created in `infra/terraform/project/cloudsql.tf`
- [ ] Connection string secret created in Secret Manager
- [ ] Service has `--add-cloudsql-instances` flag in `cloudbuild.yaml`
- [ ] Service has `--vpc-connector` flag in `cloudbuild.yaml`
- [ ] Service has `--vpc-egress private-ranges-only` flag in `cloudbuild.yaml`
- [ ] Database URL uses Unix socket format (`/cloudsql/...`)
- [ ] Service deployed and logs show successful database connection
- [ ] Integration tests verify database writes
