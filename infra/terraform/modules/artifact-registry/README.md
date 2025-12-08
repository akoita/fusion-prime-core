# Artifact Registry Terraform Module

Creates and configures Google Cloud Artifact Registry repositories for container images.

## Features

- ✅ **Docker Repository** - Stores container images
- ✅ **IAM Bindings** - Automatic access for Cloud Build and Cloud Run
- ✅ **Cleanup Policies** - Automatic deletion of old/untagged images
- ✅ **Cost Management** - Configurable retention policies
- ✅ **Labels** - Organized with environment and purpose labels

## Usage

### Basic Configuration

```hcl
module "artifact_registry" {
  source = "../modules/artifact-registry"

  project_id      = "fusion-prime"
  region          = "us-central1"
  repository_name = "services"
  environment     = "dev"
}
```

### With Service Accounts

```hcl
module "artifact_registry" {
  source = "../modules/artifact-registry"

  project_id      = "fusion-prime"
  region          = "us-central1"
  repository_name = "services"
  environment     = "production"

  # Grant read access to Cloud Run service accounts
  service_accounts = {
    settlement = "settlement-service@fusion-prime.iam.gserviceaccount.com"
    risk       = "risk-service@fusion-prime.iam.gserviceaccount.com"
  }

  # Cost management
  enable_cleanup_policies    = true
  untagged_retention_days    = 7
  minimum_versions_to_keep   = 20
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| project_id | GCP project ID | string | - | yes |
| project_number | GCP project number (for Cloud Build) | string | "" | no |
| region | GCP region | string | us-central1 | no |
| repository_name | Repository name | string | services | no |
| description | Repository description | string | "Container images..." | no |
| environment | Environment | string | dev | no |
| grant_cloudbuild_access | Grant Cloud Build write access | bool | true | no |
| service_accounts | Service accounts needing read access | map(string) | {} | no |
| enable_cleanup_policies | Enable automatic cleanup | bool | true | no |
| untagged_retention_days | Days to keep untagged images | number | 30 | no |
| minimum_versions_to_keep | Minimum versions to keep | number | 10 | no |

## Outputs

| Name | Description |
|------|-------------|
| repository_id | Repository ID |
| repository_name | Full repository name |
| location | Repository location |
| repository_url | Base URL for images |
| console_url | Cloud Console URL |

## Cleanup Policies

The module includes automatic cleanup policies to manage storage costs:

### Policy 1: Delete Untagged Images
- Deletes images without tags after N days (default: 30)
- Helps remove intermediate/temporary builds
- Configurable via `untagged_retention_days`

### Policy 2: Keep Minimum Versions
- Always keeps N most recent versions (default: 10)
- Prevents accidental deletion of recent builds
- Configurable via `minimum_versions_to_keep`

**Cost Impact:**
- Without cleanup: ~$0.10/GB/month (grows over time)
- With cleanup: Fixed cost based on `minimum_versions_to_keep`

## IAM Permissions

The module automatically grants:

1. **Cloud Build** (if `grant_cloudbuild_access = true`):
   - `roles/artifactregistry.writer` - Can push images

2. **Service Accounts** (from `service_accounts` map):
   - `roles/artifactregistry.reader` - Can pull images

## Example: Complete Setup

```hcl
# Get project number for Cloud Build SA
data "google_project" "project" {
  project_id = var.project_id
}

# Create service accounts first
module "network" {
  source = "../modules/network"
  # ... network config
}

# Create Artifact Registry
module "artifact_registry" {
  source = "../modules/artifact-registry"

  project_id     = var.project_id
  project_number = data.google_project.project.number
  region         = var.region
  environment    = var.environment

  # Grant access to Cloud Run services
  service_accounts = module.network.service_accounts

  # Production: keep more versions
  minimum_versions_to_keep = 20
  untagged_retention_days  = 7
}

# Outputs for use in other modules
output "artifact_registry_url" {
  value = module.artifact_registry.repository_url
}
```

## Viewing Images

After creation, view images at:
```bash
# List repositories
gcloud artifacts repositories list --location=us-central1

# List images in repository
gcloud artifacts docker images list \
  us-central1-docker.pkg.dev/fusion-prime/services

# View repository in console
echo ${module.artifact_registry.console_url}
```

## Cost Management

### Storage Costs
- **Price**: $0.10/GB/month
- **Average image size**: ~500MB
- **Without cleanup**: Costs grow linearly with builds
- **With cleanup**: Fixed cost (~10 images × 500MB = $0.50/month)

### Example Monthly Costs

| Scenario | Images | Storage | Monthly Cost |
|----------|--------|---------|--------------|
| No cleanup, 100 builds | 100 | 50 GB | $5.00 |
| With cleanup (keep 10) | 10 | 5 GB | $0.50 |
| With cleanup (keep 20) | 20 | 10 GB | $1.00 |

**Recommendation**: Enable cleanup policies for dev/staging, optional for production.

## Security

### Best Practices
1. ✅ Use service accounts (not personal credentials)
2. ✅ Least-privilege IAM (reader for runtime, writer for build)
3. ✅ Enable Binary Authorization for production
4. ✅ Scan images for vulnerabilities
5. ✅ Use VPC Service Controls for sensitive projects

### Vulnerability Scanning
Enable automatic scanning:
```bash
gcloud services enable containerscanning.googleapis.com
gcloud artifacts repositories update services \
  --location=us-central1 \
  --enable-vulnerability-scanning
```

## Troubleshooting

### Permission Denied on Push

**Error**: `denied: Permission "artifactregistry.repositories.uploadArtifacts" denied`

**Solution**: Ensure Cloud Build has write access:
```hcl
grant_cloudbuild_access = true
```

### Permission Denied on Pull

**Error**: `denied: Permission "artifactregistry.repositories.downloadArtifacts" denied`

**Solution**: Add service account to `service_accounts` map.

### Repository Not Found

**Error**: `name unknown: Repository "services" not found`

**Solution**: Run `terraform apply` to create the repository first.

## Migration from GCR

If migrating from Container Registry (gcr.io):

```bash
# Copy images from GCR to Artifact Registry
gcloud container images list --repository=gcr.io/fusion-prime | \
  while read image; do
    docker pull $image
    new_tag=$(echo $image | sed 's/gcr.io/us-central1-docker.pkg.dev/fusion-prime/services/')
    docker tag $image $new_tag
    docker push $new_tag
  done
```

## See Also

- [Artifact Registry Documentation](https://cloud.google.com/artifact-registry/docs)
- [Container Registry Migration Guide](https://cloud.google.com/artifact-registry/docs/transition/transition-from-gcr)
- [Cleanup Policies](https://cloud.google.com/artifact-registry/docs/repositories/cleanup-policy)

