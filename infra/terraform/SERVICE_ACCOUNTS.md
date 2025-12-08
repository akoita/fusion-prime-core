# GCP Service Accounts - Quick Reference

## TL;DR

**Compute Engine service account** is **automatically created** when you enable the Compute Engine API (`compute.googleapis.com`) via Terraform.

## Types of Service Accounts

### 1. Default Service Accounts (Auto-Created by GCP)

| Service Account | Format | When Created | Terraform Action |
|----------------|--------|--------------|------------------|
| **Compute Engine** | `PROJECT_NUMBER-compute@developer.gserviceaccount.com` | When `compute.googleapis.com` is enabled | ✅ Auto-created by `google_project_service` |
| **App Engine** | `PROJECT_ID@appspot.gserviceaccount.com` | When App Engine is initialized | ❌ Not used in Fusion Prime |
| **Cloud Build** | `PROJECT_NUMBER@cloudbuild.gserviceaccount.com` | When `cloudbuild.googleapis.com` is enabled | ✅ Auto-created by `google_project_service` |

### 2. Custom Service Accounts (Created by Terraform)

Located in: `infra/terraform/modules/service_accounts/`

| Account ID | Email Format | Purpose |
|-----------|--------------|---------|
| `terraform-admin` | `terraform-admin@PROJECT_ID.iam.gserviceaccount.com` | Terraform operations |
| `settlement-service` | `settlement-service@PROJECT_ID.iam.gserviceaccount.com` | Settlement microservice |
| `risk-service` | `risk-service@PROJECT_ID.iam.gserviceaccount.com` | Risk analytics |
| `compliance-service` | `compliance-service@PROJECT_ID.iam.gserviceaccount.com` | KYC/AML operations |
| `bridge-service` | `bridge-service@PROJECT_ID.iam.gserviceaccount.com` | Cross-chain integration |
| `cicd-deployer` | `cicd-deployer@PROJECT_ID.iam.gserviceaccount.com` | CI/CD pipelines |

## How They're Created in Fusion Prime

### In `modules/project/main.tf`

```hcl
# Lines 5-36: Enable APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "compute.googleapis.com",        # ← Creates Compute Engine SA
    "cloudbuild.googleapis.com",     # ← Creates Cloud Build SA
    # ... other APIs
  ])
}
```

**Result**: When you run `terraform apply`, GCP automatically creates:
- `PROJECT_NUMBER-compute@developer.gserviceaccount.com`
- `PROJECT_NUMBER@cloudbuild.gserviceaccount.com`

### Custom Service Accounts

Add to your `project/main.tf`:

```hcl
module "service_accounts" {
  source = "../modules/service_accounts"

  project_id        = var.project_id
  state_bucket_name = "fusion-prime-bucket-1"
}
```

## Common Commands

### List all service accounts in your project
```bash
gcloud iam service-accounts list --project=YOUR_PROJECT_ID
```

### Check if Compute Engine SA exists
```bash
gcloud iam service-accounts describe \
  PROJECT_NUMBER-compute@developer.gserviceaccount.com
```

### Find your project number
```bash
gcloud projects describe YOUR_PROJECT_ID --format="value(projectNumber)"
```

### Create a service account key (local dev only)
```bash
gcloud iam service-accounts keys create key.json \
  --iam-account=settlement-service@YOUR_PROJECT.iam.gserviceaccount.com
```

## Best Practices

✅ **DO**
- Use custom service accounts for each microservice
- Grant minimal permissions (principle of least privilege)
- Use Workload Identity for GKE
- Use Application Default Credentials for local development

❌ **DON'T**
- Share service accounts between services
- Use default service accounts for production workloads
- Commit service account keys to git
- Grant overly broad permissions like `roles/owner`

## For Fusion Prime Developers

When deploying microservices:

```hcl
# In cloud-run module or deployment
resource "google_cloud_run_service" "example" {
  template {
    spec {
      # Use the custom service account, not the default
      service_account_name = module.service_accounts.settlement_service_email
    }
  }
}
```

## Troubleshooting

**Problem**: "Service account does not exist"

**Solutions**:
1. Ensure API is enabled: `gcloud services enable compute.googleapis.com`
2. Check it exists: `gcloud iam service-accounts list`
3. Verify project number: `gcloud projects describe PROJECT_ID`
4. For custom SAs, ensure `service_accounts` module is applied

**Problem**: "Permission denied"

**Solutions**:
1. Check IAM permissions: `gcloud projects get-iam-policy PROJECT_ID`
2. Grant necessary role: `gcloud projects add-iam-policy-binding ...`
3. Wait 1-2 minutes for IAM changes to propagate

## References

- [GCP Service Accounts](https://cloud.google.com/iam/docs/service-accounts)
- [Default Service Accounts](https://cloud.google.com/iam/docs/service-accounts#default)
- Fusion Prime modules: `infra/terraform/modules/service_accounts/`

