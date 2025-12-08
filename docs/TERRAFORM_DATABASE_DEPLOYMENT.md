# Terraform Database Deployment Guide

**Created**: 2025-11-02
**Purpose**: Manage Sprint 04 databases via Infrastructure as Code

---

## 🎯 Overview

All databases for Sprint 04 services are now managed via Terraform, allowing you to:
- ✅ Reproduce environments consistently (dev, staging, production)
- ✅ Version control infrastructure changes
- ✅ Automatically create connection strings in Secret Manager
- ✅ Track infrastructure costs and changes
- ✅ Apply/destroy resources safely

---

## 📋 Databases Managed by Terraform

### Sprint 04 Databases

1. **Fiat Gateway Database** (`fp-fiat-gateway-db`)
   - Database name: `fiat_gateway`
   - User: `fiat_gateway_user`
   - Secret: `fp-fiat-gateway-db-connection-string`

2. **Cross-Chain Integration Database** (`fp-cross-chain-db`)
   - Database name: `cross_chain`
   - User: `cross_chain_user`
   - Secret: `fp-cross-chain-db-connection-string`

### Existing Databases (Already Managed)

- Settlement Database (`fp-settlement-db`)
- Risk Engine Database (`fp-risk-db`)
- Compliance Database (`fp-compliance-db`)

---

## 🚀 Quick Start

### 1. Initialize Terraform (if not done)

```bash
cd infra/terraform/project

# Initialize backend (first time only)
terraform init

# If using GCS backend, configure it:
terraform init \
  -backend-config="bucket=your-terraform-state-bucket" \
  -backend-config="prefix=terraform/state"
```

### 2. Plan the Changes

```bash
# Review what will be created
terraform plan

# Or with specific environment variables
terraform plan -var-file=terraform.dev.tfvars
```

### 3. Apply Terraform

```bash
# Create the databases
terraform apply

# Or with auto-approve
terraform apply -auto-approve
```

### 4. Verify Outputs

```bash
# Get connection names
terraform output fiat_gateway_db_connection_name
terraform output cross_chain_db_connection_name

# Get secret IDs
terraform output fiat_gateway_db_connection_string_secret
terraform output cross_chain_db_connection_string_secret
```

---

## 📁 File Structure

```
infra/terraform/
├── modules/
│   └── cloudsql/
│       ├── main.tf          # Cloud SQL instance resources
│       ├── variables.tf     # Module variables
│       └── outputs.tf       # Module outputs
└── project/
    ├── cloudsql.tf          # Database module definitions
    ├── outputs.tf          # Project outputs (NEW)
    ├── variables.tf         # Project variables
    └── terraform.*.tfvars  # Environment-specific values
```

---

## 🔧 Configuration

### Database Module Features

The Cloud SQL module automatically:
- ✅ Creates PostgreSQL instance (configurable version)
- ✅ Creates database and application user
- ✅ Generates secure password (if not provided)
- ✅ Stores password in Secret Manager
- ✅ Creates connection string secret (asyncpg format for Cloud Run)
- ✅ Configures VPC private IP
- ✅ Sets up automated backups
- ✅ Configures maintenance windows

### Connection String Format

The connection string uses the Cloud SQL Unix socket format for Cloud Run:

```
postgresql+asyncpg://USER:PASSWORD@/DATABASE_NAME?host=/cloudsql/CONNECTION_NAME
```

This format is compatible with Cloud Run's Cloud SQL Proxy integration.

---

## 🏗️ Environment Management

### Dev Environment

```bash
terraform apply -var-file=terraform.dev.tfvars
```

**Settings**:
- Tier: `db-f1-micro` (cheapest)
- HA: Disabled
- Deletion protection: Disabled

### Staging Environment

```bash
terraform apply -var-file=terraform.staging.tfvars
```

**Settings**:
- Tier: `db-g1-small`
- HA: Enabled
- Deletion protection: Enabled

### Production Environment

```bash
terraform apply -var-file=terraform.production.tfvars
```

**Settings**:
- Tier: `db-n1-standard-1` (or higher)
- HA: Enabled
- Deletion protection: Enabled
- Read replicas: Optional

---

## 🔄 Migration from Scripts to Terraform

### If Databases Already Exist

If you've already created databases using the shell scripts:

1. **Import Existing Resources** (optional):

```bash
# Import Fiat Gateway database
terraform import \
  module.cloudsql_fiat_gateway.google_sql_database_instance.primary \
  PROJECT_ID:REGION:INSTANCE_NAME

terraform import \
  module.cloudsql_fiat_gateway.google_sql_database.primary_db \
  PROJECT_ID:INSTANCE_NAME:fiat_gateway

# Import Cross-Chain database
terraform import \
  module.cloudsql_cross_chain.google_sql_database_instance.primary \
  PROJECT_ID:REGION:INSTANCE_NAME

terraform import \
  module.cloudsql_cross_chain.google_sql_database.primary_db \
  PROJECT_ID:INSTANCE_NAME:cross_chain
```

2. **Or Destroy and Recreate** (recommended for dev):

```bash
# Remove manually created databases
# Then run terraform apply to create via IaC
```

---

## 📝 Updating Cloud Build Configs

After Terraform creates the databases, update your `cloudbuild.yaml` files to use the connection names:

```yaml
# In services/fiat-gateway/cloudbuild.yaml
- '--add-cloudsql-instances'
- '${_FIAT_GATEWAY_CONNECTION_NAME}'

# In services/cross-chain-integration/cloudbuild.yaml
- '--add-cloudsql-instances'
- '${_CROSS_CHAIN_CONNECTION_NAME}'
```

You can reference Terraform outputs in Cloud Build:

```bash
# Get connection name
CONN_NAME=$(terraform output -raw fiat_gateway_db_connection_name)

# Use in Cloud Build substitution
gcloud builds submit \
  --substitutions=_FIAT_GATEWAY_CONNECTION_NAME=$CONN_NAME
```

---

## 🔍 Verification

### Check Database Status

```bash
# List Cloud SQL instances
gcloud sql instances list --project=$PROJECT_ID

# Verify databases
gcloud sql databases list --instance=fp-fiat-gateway-db-XXXXX

# Verify secrets
gcloud secrets list --filter="name:fp-*-db-*"
```

### Test Connection

```bash
# Using Cloud SQL Proxy
cloud-sql-proxy CONNECTION_NAME &
psql -h localhost -U fiat_gateway_user -d fiat_gateway
```

---

## 🗑️ Destroying Resources

### Destroy Specific Databases

```bash
# Remove Sprint 04 databases only
terraform destroy -target=module.cloudsql_fiat_gateway
terraform destroy -target=module.cloudsql_cross_chain
```

### Destroy All Databases (⚠️ DANGEROUS)

```bash
terraform destroy
```

---

## 🔐 Security Best Practices

1. **Passwords**: Auto-generated and stored in Secret Manager
2. **Private IP**: All databases use VPC private IP (no public access)
3. **SSL**: Connection encryption enforced
4. **IAM**: Cloud Run services use service accounts with minimal permissions
5. **Backups**: Automated daily backups with retention

---

## 📊 Cost Management

### Dev Environment (Current)
- Tier: `db-f1-micro`
- Cost: ~$7/month per instance
- Total for Sprint 04: ~$14/month (2 instances)

### Staging/Production
- Tier: `db-g1-small` or higher
- Cost: Varies by tier ($25-$200+/month per instance)

---

## 🐛 Troubleshooting

### Terraform Plan Shows Changes

This is normal for:
- Random suffixes in instance names
- Auto-generated passwords

Use `terraform refresh` to sync state with actual resources.

### Connection String Format

Ensure Cloud Build uses the correct connection string format:
- For Cloud Run: Use Unix socket format (auto-created by module)
- For local dev: Use Cloud SQL Proxy with TCP format

### Secret Manager Permissions

Ensure Cloud Build and Cloud Run service accounts have:
- `roles/secretmanager.secretAccessor` on the connection string secrets

---

## ✅ Next Steps

After databases are created via Terraform:

1. ✅ Run Alembic migrations for Fiat Gateway
2. ✅ Deploy services via Cloud Build
3. ✅ Update service configurations to use connection names
4. ✅ Verify service connectivity

---

## 📚 References

- [Cloud SQL Module README](../../modules/cloudsql/README.md)
- [Terraform Google Provider Docs](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/sql_database_instance)
- [Cloud SQL Best Practices](https://cloud.google.com/sql/docs/postgres/best-practices)
