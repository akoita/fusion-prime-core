# Escrow Indexer Terraform Configuration

Infrastructure-as-Code for the Escrow Indexer service.

## Resources Provisioned

### Cloud SQL PostgreSQL
- Instance: `escrow-indexer-db`
- Database: `escrow_indexer`
- User: `escrow_indexer` (auto-generated password)
- Features:
  - Automated backups (daily at 3 AM)
  - Point-in-time recovery (production)
  - Private IP connectivity via VPC
  - Read replica (production)
  - Query insights enabled

### Pub/Sub
- **Subscription**: `escrow-indexer-sub`
  - Subscribes to: `settlement.events.v1` topic
  - Ack deadline: 60 seconds
  - Message retention: 7 days
  - Retry policy with exponential backoff

- **Dead Letter Queue**: `escrow-indexer-dlq`
  - Receives messages after 5 failed delivery attempts
  - DLQ subscription for monitoring

### Cloud Run Service
- Service: `escrow-indexer`
- Resources:
  - CPU: 1-2 cores (dev/prod)
  - Memory: 512Mi-1Gi (dev/prod)
  - Timeout: 3600s (for long-running Pub/Sub subscriber)
- Scaling:
  - Min instances: 0 (dev), 1 (prod)
  - Max instances: 5 (dev), 10 (prod)
- VPC egress: Private ranges only
- Cloud SQL connection via Unix socket

### Secret Manager
- `escrow-indexer-db-password`: Database password
- `escrow-indexer-connection-string`: Full connection string

### IAM
- Service account for Cloud Run
- Pub/Sub subscriber role
- Cloud SQL client role
- Secret accessor role
- Monitoring/logging roles

## Prerequisites

1. **GCP Project**
   - Project ID: `fusion-prime`
   - APIs enabled: Cloud Run, Cloud SQL, Pub/Sub, Secret Manager

2. **VPC Network**
   - VPC: `fusion-prime-vpc`
   - VPC Connector for Cloud Run

3. **Pub/Sub Topic**
   - Topic `settlement.events.v1` (created by relayer service)

4. **Terraform State Bucket**
   - Bucket: `fusion-prime-terraform-state`

## Usage

### 1. Initialize Terraform

```bash
cd infra/terraform/project/escrow-indexer
terraform init
```

### 2. Configure Variables

```bash
# Copy example and customize
cp terraform.tfvars.example terraform.tfvars

# Edit variables for your environment
vim terraform.tfvars
```

### 3. Plan Deployment

```bash
# Development
terraform plan

# Production
terraform plan -var="environment=prod"
```

### 4. Apply Configuration

```bash
# Development
terraform apply

# Production (with approval)
terraform apply -var="environment=prod"
```

### 5. Get Outputs

```bash
# View all outputs
terraform output

# Get service URL
terraform output service_url

# Get database connection info
terraform output database_connection_name
```

## Environments

### Development (`environment = "dev"`)
- Cloud SQL: `db-f1-micro` (shared-core)
- No high availability
- Minimal backups (7 days retention)
- Min instances: 0 (scale to zero)
- Public IP: Optional for local testing

### Production (`environment = "prod"`)
- Cloud SQL: `db-n1-standard-1` (dedicated cores)
- High availability (REGIONAL)
- Full backups (30 days retention, PITR enabled)
- Read replica for scaling
- Min instances: 1 (always running)
- Monitoring alerts enabled
- Public IP: Disabled (private VPC only)

## Post-Deployment

### 1. Build and Deploy Container

```bash
cd services/escrow-indexer

# Build image
docker build -t gcr.io/fusion-prime/escrow-indexer:latest .

# Push to registry
docker push gcr.io/fusion-prime/escrow-indexer:latest

# Terraform will ignore image changes, deploy via Cloud Build or gcloud
gcloud run deploy escrow-indexer \
  --image gcr.io/fusion-prime/escrow-indexer:latest \
  --region us-central1
```

### 2. Initialize Database Schema

The database schema is automatically created by the application on first startup.

Alternatively, run migrations:

```bash
# Connect to database
gcloud sql connect escrow-indexer-db --user=escrow_indexer

# Schema is created automatically by SQLAlchemy
# on application startup via init_db()
```

### 3. Verify Deployment

```bash
# Get service URL
SERVICE_URL=$(terraform output -raw service_url)

# Health check
curl $SERVICE_URL/health

# Check stats
curl $SERVICE_URL/api/v1/escrows/stats
```

### 4. Monitor Pub/Sub

```bash
# Check subscription
gcloud pubsub subscriptions describe escrow-indexer-sub

# Check message backlog
gcloud pubsub subscriptions describe escrow-indexer-sub \
  --format='value(numUndeliveredMessages)'

# Check DLQ (should be empty)
gcloud pubsub subscriptions describe escrow-indexer-dlq-sub \
  --format='value(numUndeliveredMessages)'
```

## Updating Infrastructure

### Update Cloud Run Service

```bash
# Update container image
terraform apply -var="container_image=gcr.io/fusion-prime/escrow-indexer:v1.2.0"

# Or let CI/CD update it (terraform ignores image changes)
```

### Update Database

```bash
# Scale up database
terraform apply -var="environment=prod"

# Add database flags
# Edit main.tf database_flags and apply
```

### Update Scaling

```bash
# Edit variables.tf or terraform.tfvars
# Change min_instances, max_instances
terraform apply
```

## Troubleshooting

### Cloud SQL Connection Issues

```bash
# Check Cloud SQL status
gcloud sql instances describe escrow-indexer-db

# Check VPC connector
gcloud compute networks vpc-access connectors describe fusion-prime-vpc-connector \
  --region us-central1

# Test connection from Cloud Run
gcloud run services proxy escrow-indexer --port=8080
```

### Pub/Sub Issues

```bash
# Check subscription status
gcloud pubsub subscriptions describe escrow-indexer-sub

# Pull test message
gcloud pubsub subscriptions pull escrow-indexer-sub --limit=1

# Check DLQ for failed messages
gcloud pubsub subscriptions pull escrow-indexer-dlq-sub --limit=10
```

### Service Not Starting

```bash
# Check logs
gcloud run logs read escrow-indexer --limit=50

# Check service status
gcloud run services describe escrow-indexer --region=us-central1
```

## Cost Estimation

### Development
- Cloud SQL (db-f1-micro): ~$7/month
- Cloud Run (minimal usage): ~$0/month
- Pub/Sub: ~$0/month
- **Total: ~$7/month**

### Production
- Cloud SQL (db-n1-standard-1): ~$50/month
- Cloud SQL read replica: ~$50/month
- Cloud Run (1 instance always running): ~$15/month
- Pub/Sub: ~$5/month
- **Total: ~$120/month**

## Cleanup

```bash
# Destroy all resources (careful!)
terraform destroy

# Or destroy specific resource
terraform destroy -target=module.escrow_indexer_service
```

## CI/CD Integration

This infrastructure is meant to be deployed via CI/CD:

```yaml
# Example Cloud Build trigger
steps:
  - name: 'hashicorp/terraform:1.5'
    args:
      - 'apply'
      - '-auto-approve'
      - '-var=environment=prod'
```

## Security

- Database passwords are auto-generated and stored in Secret Manager
- All connections use private IP (VPC)
- Cloud Run uses dedicated service account with least-privilege IAM
- SSL/TLS enforced for database connections
- No public database access
- Secrets injected via Cloud Run environment variables

## Monitoring

Production environment includes:
- High error rate alerts (>10%)
- High latency alerts (>1000ms P95)
- Dead letter queue monitoring
- Cloud SQL performance insights
- Custom metrics via Cloud Monitoring

## Support

For issues with this infrastructure:
1. Check terraform plan output
2. Review Cloud Build logs
3. Check GCP Console for errors
4. Review service logs with `gcloud run logs read`
