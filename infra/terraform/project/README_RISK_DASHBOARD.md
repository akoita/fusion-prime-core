# Risk Dashboard Infrastructure

This document describes the Terraform-managed infrastructure for the Risk Dashboard frontend application.

## Infrastructure Components

### 1. Artifact Registry Repository

**Resource**: `module.artifact_registry_frontend`

Creates a Docker repository for frontend container images:
- **Repository Name**: `frontend`
- **Location**: `us-central1`
- **Format**: Docker
- **Cleanup Policies**:
  - Delete untagged images after 7 days
  - Keep minimum 10 recent versions

**Access Control**:
- Cloud Build: Write access (push images)
- Risk Dashboard Service Account: Read access (pull images)

### 2. Service Account

**Resource**: Created via `module.network`

Service account for Risk Dashboard Cloud Run service:
- **ID**: `risk-dashboard`
- **Email**: `risk-dashboard@${project_id}.iam.gserviceaccount.com`

**IAM Roles**:
- Artifact Registry Reader (pull images)

### 3. Cloud Run Service

**Resource**: `module.risk_dashboard`

Deploys the Risk Dashboard as a Cloud Run service:
- **Service Name**: `risk-dashboard`
- **Port**: 80 (Nginx)
- **Memory**: 512Mi
- **CPU**: 1000m
- **Scaling**: 0-10 instances (scale to zero)
- **Access**: Public (unauthenticated)

**Environment Variables**:
- `VITE_API_BASE_URL`: Risk Engine API URL
- `VITE_WS_URL`: WebSocket URL for real-time updates
- `VITE_ALERT_NOTIFICATION_URL`: Alert Notification Service URL

## Deployment

### Initial Setup

```bash
cd infra/terraform/project

# Initialize Terraform
terraform init

# Plan changes
terraform plan -var-file=terraform.dev.tfvars

# Apply infrastructure
terraform apply -var-file=terraform.dev.tfvars
```

### Manual Deployment (via Cloud Build)

After Terraform creates the infrastructure:

```bash
cd frontend/risk-dashboard
gcloud builds submit --config=cloudbuild.yaml --project=fusion-prime
```

The Cloud Build will:
1. Build Docker image
2. Push to Artifact Registry (`frontend` repository)
3. Deploy to Cloud Run service

## Environment-Specific Configuration

### Dev Environment
- **Project**: `fusion-prime`
- **Repository**: `frontend`
- **Service**: `risk-dashboard`

### Stage Environment
- **Project**: `fusion-prime-stage`
- Update `terraform.staging.tfvars` with stage-specific values
- Update environment variables in `risk-dashboard.tf`

### Production Environment
- **Project**: `fusion-prime-production`
- Update `terraform.production.tfvars` with production values
- Update environment variables in `risk-dashboard.tf`
- Consider authentication/IAP for production

## Maintenance

### Updating Infrastructure

1. Modify Terraform files
2. Run `terraform plan` to preview changes
3. Run `terraform apply` to apply changes

### Updating Application Code

1. Code changes are deployed via Cloud Build
2. Terraform is configured to ignore image changes:
   ```hcl
   lifecycle {
     ignore_changes = [
       template[0].containers[0].image
     ]
   }
   ```

### Viewing Resources

```bash
# View Cloud Run service
gcloud run services describe risk-dashboard --region=us-central1

# View Artifact Registry
gcloud artifacts repositories describe frontend --location=us-central1

# View service account
gcloud iam service-accounts describe risk-dashboard@fusion-prime.iam.gserviceaccount.com
```

## Cost Considerations

- **Cloud Run**: Pay-per-use (scales to zero)
- **Artifact Registry**: Storage costs (~$0.10/GB/month)
- **Network Egress**: Minimal (static assets cached via CDN)

Total estimated monthly cost: < $5 for dev environment
