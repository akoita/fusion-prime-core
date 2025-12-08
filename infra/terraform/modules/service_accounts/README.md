# Service Accounts Module

Creates and manages custom service accounts for Fusion Prime platform components.

## Overview

This module creates purpose-specific service accounts following the **principle of least privilege**. Each microservice gets its own service account with only the permissions it needs.

## Service Accounts Created

| Account ID | Purpose | Key Permissions |
|------------|---------|----------------|
| `terraform-admin` | Terraform state & deployments | Storage Admin (state bucket) |
| `settlement-service` | Settlement microservice | Cloud Run, Pub/Sub, Secret Manager, Cloud SQL |
| `risk-service` | Risk analytics service | Cloud Run, BigQuery, Cloud SQL |
| `compliance-service` | KYC/AML compliance | Cloud Run, Firestore, Secret Manager |
| `bridge-service` | Cross-chain integration | Cloud Run, Secret Manager |
| `cicd-deployer` | CI/CD pipelines | Cloud Deploy, Artifact Registry |

## How GCP Service Accounts Work

### Default Service Accounts (Auto-Created)

When you enable certain GCP services, default service accounts are **automatically created**:

1. **Compute Engine Default SA**
   - Format: `PROJECT_NUMBER-compute@developer.gserviceaccount.com`
   - Created when: You enable `compute.googleapis.com`
   - Use case: VMs that don't specify a service account

2. **App Engine Default SA**
   - Format: `PROJECT_ID@appspot.gserviceaccount.com`
   - Created when: You initialize App Engine
   - Use case: App Engine applications

3. **Cloud Build Default SA**
   - Format: `PROJECT_NUMBER@cloudbuild.gserviceaccount.com`
   - Created when: You enable Cloud Build
   - Use case: CI/CD pipelines

### Custom Service Accounts (This Module)

**Best practice**: Create custom service accounts for each workload with specific, minimal permissions.

Benefits:
- ✅ Better security isolation
- ✅ Easier audit trails
- ✅ Fine-grained access control
- ✅ Workload identity for GKE

## Usage in Main Configuration

```hcl
module "service_accounts" {
  source = "../modules/service_accounts"

  project_id        = var.project_id
  state_bucket_name = "fusion-prime-bucket-1"
}

# Use the service account in Cloud Run
resource "google_cloud_run_service" "settlement" {
  name     = "settlement-service"
  location = var.region

  template {
    spec {
      service_account_name = module.service_accounts.settlement_service_email
      # ... rest of config
    }
  }
}
```

## Creating Service Account Keys (For Local Development)

⚠️ **Warning**: Service account keys are long-lived credentials. Avoid them in production!

```bash
# Create a key for local testing
gcloud iam service-accounts keys create key.json \
  --iam-account=settlement-service@YOUR_PROJECT.iam.gserviceaccount.com

# Use it locally
export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/key.json"

# NEVER commit this key to git!
```

## Workload Identity (Recommended for GKE)

For GKE workloads, use **Workload Identity** instead of service account keys:

```bash
# Bind Kubernetes service account to GCP service account
gcloud iam service-accounts add-iam-policy-binding \
  settlement-service@YOUR_PROJECT.iam.gserviceaccount.com \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:YOUR_PROJECT.svc.id.goog[NAMESPACE/KSA_NAME]"
```

## Security Best Practices

1. **One service account per workload** - Don't share service accounts
2. **Minimal permissions** - Only grant what's needed
3. **Audit regularly** - Review permissions quarterly
4. **Rotate keys** - If you must use keys, rotate them frequently
5. **Use Workload Identity** - Avoid keys entirely for GKE workloads
6. **Monitor usage** - Set up Cloud Audit Logs alerts

## See Also

- [GCP Service Account Documentation](https://cloud.google.com/iam/docs/service-accounts)
- [Workload Identity](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)
- [Best Practices for Service Accounts](https://cloud.google.com/iam/docs/best-practices-service-accounts)

