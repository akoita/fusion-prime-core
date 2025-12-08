# Terraform Infrastructure Requirements

## Executive Summary

This document outlines what infrastructure components are already managed in Terraform versus what needs to be added to ensure complete infrastructure reproducibility across environments (dev, staging, production).

## Current Terraform Coverage

### ✅ Already Managed in Terraform

Based on `/infra/terraform/project/cloudsql.tf` and modules:

1. **Cloud SQL Databases**
   - Settlement Service database (`fp-settlement-db`)
   - Risk Engine database (`fp-risk-db`)
   - Compliance Service database (`fp-compliance-db`)
   - Database instances, databases, users, and passwords

2. **Secret Manager Secrets**
   - Database passwords (auto-generated)
   - Database connection strings
   - Managed by cloudsql module (lines 204-257 in `modules/cloudsql/main.tf`)

3. **Network Infrastructure**
   - VPC networks (module exists: `modules/network`)
   - Private VPC connections for Cloud SQL

4. **Service Accounts**
   - Module exists: `modules/service_accounts`
   - Cloud SQL Proxy service accounts (optional, in cloudsql module lines 186-202)

5. **Artifact Registry**
   - Configured in `project/artifact-registry.tf`

6. **Pub/Sub Topics**
   - Module exists: `modules/pubsub_settlement`

7. **Cloud Run Services (Partial)**
   - Module exists: `modules/cloud_run_service`
   - Need to verify if all services are deployed via Terraform

8. **Cloud Build Triggers (Partial)**
   - Module exists: `modules/cloud-build-triggers`

---

## ❌ Missing from Terraform (Needs to be Added)

### 1. IAM Bindings for Secret Access

**Current State**: Manually added via gcloud command
```bash
gcloud secrets add-iam-policy-binding fp-risk-db-connection-string \
  --member='serviceAccount:961424092563-compute@developer.gserviceaccount.com' \
  --role='roles/secretmanager.secretAccessor'
```

**What needs to be added**: IAM bindings for Cloud Run service accounts to access database secrets

**Terraform Resource Needed**:
```hcl
# In modules/cloudsql/main.tf or separate iam.tf

resource "google_secret_manager_secret_iam_member" "service_account_access" {
  count = var.grant_service_account_access ? 1 : 0

  secret_id = google_secret_manager_secret.db_connection_string[0].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.service_account_email}"
}

# Example usage in project/cloudsql.tf:
module "cloudsql_risk_engine" {
  source = "../modules/cloudsql"

  # Existing config...

  # NEW: Grant Cloud Run service account access to secrets
  grant_service_account_access = true
  service_account_email        = "${data.google_project.project.number}-compute@developer.gserviceaccount.com"
}
```

**Files to Modify**:
- `infra/terraform/modules/cloudsql/main.tf` - Add IAM binding resources
- `infra/terraform/modules/cloudsql/variables.tf` - Add variables
- `infra/terraform/project/cloudsql.tf` - Configure for each database

---

### 2. Cloud Run Service Deployments (Complete Configuration)

**Current State**: Services deployed via `cloudbuild.yaml` with `gcloud run deploy` commands

**Issue**: Cloud Run service configurations (environment variables, secrets, Cloud SQL connections) are in cloudbuild.yaml files, not Terraform

**Files Currently Managing Deployments**:
- `services/risk-engine/cloudbuild.yaml`
- `services/settlement/cloudbuild.yaml`
- `services/compliance/cloudbuild.yaml`
- `services/alert-notification/cloudbuild.yaml`
- `services/price-oracle/cloudbuild.yaml`
- `integrations/relayers/escrow/cloudbuild.yaml`

**What needs to be added**: Cloud Run service resources with complete configuration

**Terraform Resource Needed**:
```hcl
# Example: infra/terraform/project/cloud_run_services.tf

module "risk_engine_service" {
  source = "../modules/cloud_run_service"

  project_id   = var.project_id
  region       = var.region
  service_name = "risk-engine"
  image        = "us-central1-docker.pkg.dev/${var.project_id}/services/risk-engine-service:latest"

  # Environment variables
  env_vars = {
    ENVIRONMENT        = "production"
    GCP_PROJECT        = var.project_id
    RISK_SUBSCRIPTION  = "risk-events-consumer"
    PRICE_SUBSCRIPTION = "risk-engine-prices-consumer"
    PRICE_ORACLE_URL   = "https://price-oracle-service-${data.google_project.project.number}.us-central1.run.app"
  }

  # Secrets
  secrets = {
    RISK_DATABASE_URL = {
      secret_name = module.cloudsql_risk_engine.connection_string_secret_id
      version     = "latest"
    }
  }

  # Cloud SQL connection
  cloudsql_instances = [
    module.cloudsql_risk_engine.connection_name
  ]

  # Resource limits
  memory = "2Gi"
  cpu    = "2"

  # Scaling
  min_instances = 0
  max_instances = 10

  # Other settings
  timeout              = 300
  concurrency          = 100
  allow_unauthenticated = true
}
```

**Files to Create/Modify**:
- `infra/terraform/project/cloud_run_services.tf` - New file for all service deployments
- `infra/terraform/modules/cloud_run_service/main.tf` - Enhance existing module
- `infra/terraform/modules/cloud_run_service/variables.tf` - Add missing variables

---

### 3. Data Sources for Computed Values

**Current State**: Hardcoding project numbers and resource IDs

**What needs to be added**: Data sources to dynamically fetch values

**Terraform Data Sources Needed**:
```hcl
# infra/terraform/project/data.tf

data "google_project" "project" {
  project_id = var.project_id
}

data "google_compute_default_service_account" "default" {
  project = var.project_id
}

# Output the service account for use in modules
output "default_compute_service_account" {
  value = data.google_compute_default_service_account.default.email
}
```

---

### 4. Pub/Sub Topics and Subscriptions (Complete)

**Current State**: Some topics may exist, but subscriptions not fully managed

**What needs to be added**: Complete Pub/Sub infrastructure

**Terraform Resources Needed**:
```hcl
# infra/terraform/project/pubsub.tf

# Settlement events topic
resource "google_pubsub_topic" "settlement_events" {
  name    = "settlement.events.v1"
  project = var.project_id
}

# Risk Engine subscription to settlement events
resource "google_pubsub_subscription" "risk_engine_settlement_events" {
  name    = "risk-events-consumer"
  topic   = google_pubsub_topic.settlement_events.name
  project = var.project_id

  ack_deadline_seconds = 60

  push_config {
    push_endpoint = "${module.risk_engine_service.url}/api/v1/events/settlement"
  }
}

# Market prices topic
resource "google_pubsub_topic" "market_prices" {
  name    = "market.prices.v1"
  project = var.project_id
}

# Risk Engine subscription to price updates
resource "google_pubsub_subscription" "risk_engine_price_updates" {
  name    = "risk-engine-prices-consumer"
  topic   = google_pubsub_topic.market_prices.name
  project = var.project_id

  ack_deadline_seconds = 30
}

# Margin events topic
resource "google_pubsub_topic" "margin_events" {
  name    = "risk.margin.events.v1"
  project = var.project_id
}

# Alert Service subscription to margin events
resource "google_pubsub_subscription" "alert_margin_events" {
  name    = "alert-margin-events-consumer"
  topic   = google_pubsub_topic.margin_events.name
  project = var.project_id

  ack_deadline_seconds = 60

  push_config {
    push_endpoint = "${module.alert_service.url}/api/v1/alerts/margin"
  }
}
```

**Files to Create**:
- `infra/terraform/project/pubsub.tf` - Complete Pub/Sub infrastructure

---

### 5. Alert Notification Database (Optional)

**Current State**: According to audit, Alert Notification doesn't have a database yet

**Decision Needed**: Does Alert Service need persistent storage?

**If YES, add to `project/cloudsql.tf`**:
```hcl
module "cloudsql_alert_notification" {
  source = "../modules/cloudsql"

  project_id      = var.project_id
  region          = var.region
  instance_name   = "fp-alert-db"
  database_name   = "alert_db"
  app_user_name   = "alert_user"
  tier            = "db-f1-micro"
  disk_size_gb    = 10

  # Same configuration as other services...
}
```

---

## Implementation Plan

### Phase 1: Enhance CloudSQL Module (Week 1)

**Goal**: Add IAM bindings to existing CloudSQL module

**Tasks**:
1. Update `infra/terraform/modules/cloudsql/main.tf`:
   - Add `google_secret_manager_secret_iam_member` resource
   - Make it conditional based on new variable

2. Update `infra/terraform/modules/cloudsql/variables.tf`:
   ```hcl
   variable "grant_service_account_access" {
     description = "Grant service account access to database secrets"
     type        = bool
     default     = false
   }

   variable "service_account_email" {
     description = "Service account email to grant secret access"
     type        = string
     default     = ""
   }
   ```

3. Update `infra/terraform/project/cloudsql.tf`:
   - Add data source for default compute service account
   - Enable IAM binding for all three databases
   - Test with `terraform plan`

**Expected Outcome**: Service accounts automatically granted secret access

---

### Phase 2: Add Pub/Sub Infrastructure (Week 1-2)

**Goal**: Manage all Pub/Sub topics and subscriptions in Terraform

**Tasks**:
1. Create `infra/terraform/project/pubsub.tf`
2. Define all topics:
   - settlement.events.v1
   - market.prices.v1
   - risk.margin.events.v1
3. Define all subscriptions with proper ACKs and push configs
4. Import existing resources if they exist:
   ```bash
   terraform import google_pubsub_topic.settlement_events projects/fusion-prime/topics/settlement.events.v1
   ```

**Expected Outcome**: All Pub/Sub infrastructure managed in Terraform

---

### Phase 3: Add Cloud Run Services (Week 2-3)

**Goal**: Manage Cloud Run service deployments via Terraform

**Tasks**:
1. Review existing `modules/cloud_run_service`
2. Enhance module to support:
   - Environment variables
   - Secrets (from Secret Manager)
   - Cloud SQL connections
   - Resource limits
   - Scaling config

3. Create `infra/terraform/project/cloud_run_services.tf`
4. Define all services:
   - risk-engine
   - settlement-service
   - compliance-service
   - alert-notification
   - price-oracle
   - escrow-relayer

**Decision Point**:
- Should image tags be managed in Terraform or keep CI/CD updating them?
- **Recommendation**: Use Terraform for baseline deployment, CI/CD updates image tags

**Expected Outcome**: Infrastructure managed in Terraform, images updated by CI/CD

---

### Phase 4: Environment-Specific Configurations (Week 3-4)

**Goal**: Support dev, staging, and production environments

**Tasks**:
1. Create environment-specific variable files:
   - `infra/terraform/environments/dev/terraform.tfvars`
   - `infra/terraform/environments/staging/terraform.tfvars`
   - `infra/terraform/environments/production/terraform.tfvars`

2. Add environment-specific overrides:
   ```hcl
   # dev
   tier = "db-f1-micro"
   high_availability = false
   enable_deletion_protection = false

   # production
   tier = "db-n1-standard-2"
   high_availability = true
   enable_deletion_protection = true
   ```

3. Create workspace management strategy:
   ```bash
   terraform workspace new dev
   terraform workspace new staging
   terraform workspace new production
   ```

**Expected Outcome**: Easy environment replication

---

## Migration Strategy (Existing Resources)

### Approach 1: Terraform Import (Recommended)

For resources that already exist, import them into Terraform state:

```bash
# Example: Import existing database instances
cd infra/terraform/project
terraform import module.cloudsql_settlement.google_sql_database_instance.primary \
  fusion-prime/fp-settlement-db-590d836a

terraform import module.cloudsql_risk_engine.google_sql_database_instance.primary \
  fusion-prime/fp-risk-db-1d929830

terraform import module.cloudsql_compliance.google_sql_database_instance.primary \
  fusion-prime/fp-compliance-db-0b9f2040
```

### Approach 2: Recreate Resources (For dev only)

For dev environment, consider destroying and recreating with Terraform:
1. Backup data
2. Destroy manual resources
3. Apply Terraform configuration
4. Restore data

**WARNING**: Only do this in dev environment!

---

## Benefits of Complete Terraform Management

1. **Reproducibility**: Spin up identical environments easily
2. **Version Control**: Infrastructure changes tracked in Git
3. **Disaster Recovery**: Rebuild entire infrastructure from code
4. **Testing**: Test infrastructure changes in dev before production
5. **Documentation**: Terraform code serves as documentation
6. **Consistency**: No configuration drift between environments
7. **Auditability**: All changes tracked and reviewable

---

## Files That Need to Be Created/Modified

### New Files to Create
```
infra/terraform/project/
├── pubsub.tf                    # All Pub/Sub infrastructure
├── cloud_run_services.tf        # All Cloud Run services
├── data.tf                      # Data sources for computed values
└── iam.tf                       # IAM bindings not in modules

infra/terraform/environments/
├── dev/
│   └── terraform.tfvars
├── staging/
│   └── terraform.tfvars
└── production/
    └── terraform.tfvars
```

### Existing Files to Modify
```
infra/terraform/modules/cloudsql/
├── main.tf                      # Add IAM bindings
├── variables.tf                 # Add new variables
└── outputs.tf                   # Add connection_name output

infra/terraform/modules/cloud_run_service/
├── main.tf                      # Enhance with secrets, Cloud SQL
└── variables.tf                 # Add missing variables

infra/terraform/project/
├── cloudsql.tf                  # Add IAM config to each module
└── variables.tf                 # Add project-level variables
```

---

## Next Steps

### Immediate (After Dev Testing Complete)
1. ✅ Fix Risk Engine deployment (in progress)
2. ⏳ Fix Settlement and Compliance deployments
3. ⏳ Validate all services working in dev

### Short-term (Next 1-2 weeks)
1. Implement Phase 1: CloudSQL module IAM bindings
2. Implement Phase 2: Pub/Sub infrastructure
3. Test in dev environment

### Medium-term (Next 2-4 weeks)
1. Implement Phase 3: Cloud Run services
2. Implement Phase 4: Environment-specific configs
3. Import existing resources to Terraform state

### Long-term (Production Deployment)
1. Apply Terraform configuration to production
2. Document runbooks for Terraform operations
3. Set up Terraform CI/CD pipeline

---

## Terraform State Management

### Current State
- Need to verify where Terraform state is stored
- Should be using GCS backend for team collaboration

### Recommended Setup
```hcl
# infra/terraform/project/backend.tf
terraform {
  backend "gcs" {
    bucket = "fusion-prime-terraform-state"
    prefix = "terraform/state"
  }
}
```

### State Management Best Practices
1. Store state in GCS bucket
2. Enable versioning on state bucket
3. Use workspace for environments
4. Never commit `.tfstate` files to Git
5. Use state locking (automatic with GCS)

---

## Summary

**Current Coverage**: ~60% of infrastructure managed in Terraform
- Databases, networks, basic services

**Missing Coverage**: ~40% needs to be added
- IAM bindings, Pub/Sub, Cloud Run configs

**Effort Estimate**: 2-4 weeks to achieve 100% Terraform coverage

**Priority Order**:
1. 🔴 HIGH: IAM bindings (enables current deployments)
2. 🟡 MEDIUM: Pub/Sub infrastructure (enables service integration)
3. 🟡 MEDIUM: Cloud Run services (enables infrastructure as code)
4. 🟢 LOW: Environment-specific configs (enables production deployment)

**Status**: Ready to begin implementation after dev validation complete
