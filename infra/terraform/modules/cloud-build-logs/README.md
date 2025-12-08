# Cloud Build Logs Module

This Terraform module creates a custom Cloud Build logs bucket that is VPC-SC compliant, resolving the limitation where the default Cloud Build logs bucket is always outside any VPC-SC security perimeter.

## Problem Solved

When VPC-SC (Virtual Private Cloud Service Controls) is enabled, the default Cloud Build logs bucket (`gs://[PROJECT_NUMBER].cloudbuild-logs.googleusercontent.com`) is always outside the security perimeter. This causes:

- `gcloud builds submit` commands to fail with VPC-SC errors
- GitHub Actions workflows to fail when trying to stream build logs
- CI/CD pipelines to break due to logging restrictions

## Solution

This module creates a custom logs bucket that can be placed inside your VPC-SC perimeter, allowing:

- ✅ Cloud Build to write logs to a VPC-SC compliant bucket
- ✅ GitHub Actions to access build logs without VPC-SC restrictions
- ✅ CI/CD pipelines to work normally with proper log streaming

## Usage

```hcl
module "cloud_build_logs" {
  source = "../modules/cloud-build-logs"

  project_id     = "your-project-id"
  project_number = "123456789"
  bucket_name    = "your-project-cloud-build-logs"
  location       = "US"

  # GitHub Actions service account for log access
  github_service_account_email = "github@your-project.iam.gserviceaccount.com"

  # Log retention and lifecycle
  log_retention_days = 30
  versioning_enabled = true
  deletion_protection = true
}
```

## Features

- **VPC-SC Compliant**: Bucket can be placed inside VPC-SC security perimeter
- **IAM Permissions**: Automatic setup of Cloud Build and GitHub Actions permissions
- **Lifecycle Management**: Configurable log retention and cleanup
- **Versioning**: Optional versioning for log history
- **Security**: Deletion protection and uniform bucket-level access
- **Monitoring**: Proper labeling for organization and cost tracking

## GitHub Actions Integration

After applying this module, update your GitHub Actions workflows to use the custom logs bucket:

```yaml
- name: Build with custom logs bucket
  run: |
    gcloud builds submit \
      --gcs-log-dir=gs://your-project-cloud-build-logs \
      --config cloudbuild.yaml \
      .
```

## Outputs

- `bucket_name`: Name of the created bucket
- `bucket_url`: URL of the created bucket
- `bucket_self_link`: Self-link of the created bucket

## Security Considerations

- The bucket is created with uniform bucket-level access for consistent IAM
- Cloud Build service account gets `objectCreator` and `objectViewer` roles
- GitHub Actions service account gets `objectViewer` role for log access
- Project owners get `storage.admin` role for bucket management
- Deletion protection is enabled by default to prevent accidental data loss
