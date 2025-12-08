# Cloud SQL PostgreSQL Terraform Module

Production-ready Terraform module for provisioning Google Cloud SQL PostgreSQL instances with high availability, automated backups, and security best practices.

## Features

- ✅ **High Availability**: Regional configuration with automatic failover
- ✅ **Automated Backups**: Daily backups with configurable retention
- ✅ **Point-in-Time Recovery**: Transaction log-based recovery
- ✅ **Private IP**: VPC-native connectivity for security
- ✅ **Read Replicas**: Optional read replicas for scaling reads
- ✅ **Security**: SSL required, password stored in Secret Manager
- ✅ **Monitoring**: Query Insights enabled for performance tracking
- ✅ **Maintenance Windows**: Configurable maintenance schedules
- ✅ **Auto-scaling**: Disk autoresize with limits
- ✅ **Service Account**: Cloud SQL Proxy service account

## Usage

### Basic Configuration (Development)

```hcl
module "cloudsql_dev" {
  source = "./modules/cloudsql"

  project_id     = "your-gcp-project"
  region         = "us-central1"
  instance_name  = "fusion-prime-dev"
  environment    = "dev"

  # VPC network for private IP
  vpc_network_id = google_compute_network.vpc.id

  # Small instance for development
  tier                = "db-g1-small"
  disk_size_gb        = 10
  high_availability   = false
  enable_read_replica = false

  # Relax deletion protection for dev
  enable_deletion_protection = false
}
```

### Production Configuration

```hcl
module "cloudsql_prod" {
  source = "./modules/cloudsql"

  project_id     = "your-gcp-project"
  region         = "us-central1"
  instance_name  = "fusion-prime-prod"
  environment    = "production"

  # VPC network for private IP
  vpc_network_id = google_compute_network.vpc.id

  # Production-grade instance
  tier                = "db-n1-standard-2" # 2 vCPU, 7.5 GB RAM
  disk_size_gb        = 100
  disk_autoresize_limit = 500
  high_availability   = true # Regional HA

  # Read replica for scaling
  enable_read_replica = true
  replica_region      = "us-east1"
  replica_tier        = "db-n1-standard-1"

  # Backup configuration
  backup_start_time              = "03:00"
  retained_backups               = 30
  enable_point_in_time_recovery  = true
  transaction_log_retention_days = 7

  # Maintenance window (Sunday 3 AM)
  maintenance_window_day  = 7
  maintenance_window_hour = 3

  # Security
  enable_deletion_protection        = true
  store_password_in_secret_manager  = true
  create_proxy_service_account      = true

  # Performance tuning
  database_flags = [
    {
      name  = "max_connections"
      value = "200"
    },
    {
      name  = "shared_buffers"
      value = "524288" # 512MB
    },
    {
      name  = "effective_cache_size"
      value = "1572864" # 1.5GB
    },
    {
      name  = "work_mem"
      value = "8192" # 8MB
    },
    {
      name  = "maintenance_work_mem"
      value = "131072" # 128MB
    },
  ]

  labels = {
    cost_center = "engineering"
    team        = "platform"
  }
}
```

### With Public IP (Not Recommended)

```hcl
module "cloudsql_public" {
  source = "./modules/cloudsql"

  project_id     = "your-gcp-project"
  region         = "us-central1"
  instance_name  = "fusion-prime-public"

  vpc_network_id = google_compute_network.vpc.id

  # Enable public IP with authorized networks
  enable_public_ip = true
  authorized_networks = [
    {
      name = "office-network"
      cidr = "203.0.113.0/24"
    },
    {
      name = "vpn-gateway"
      cidr = "198.51.100.1/32"
    }
  ]
}
```

## Outputs

### Connection Information

```hcl
output "db_connection_name" {
  value = module.cloudsql_prod.instance_connection_name
}

output "db_private_ip" {
  value = module.cloudsql_prod.private_ip_address
}

output "db_connection_string" {
  value     = module.cloudsql_prod.connection_string
  sensitive = true
}
```

### Using Connection String

The connection string is available in two formats:

1. **Private IP** (recommended):
```
postgresql://fusion_prime_app:PASSWORD@10.0.0.3:5432/fusion_prime
```

2. **Secret Manager**:
```bash
gcloud secrets versions access latest \
  --secret fusion-prime-prod-connection-string
```

## Connecting to Cloud SQL

### Method 1: Cloud SQL Proxy (Recommended)

```bash
# Download Cloud SQL Proxy
curl -o cloud-sql-proxy \
  https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.linux.amd64

chmod +x cloud-sql-proxy

# Run proxy
./cloud-sql-proxy \
  --private-ip \
  PROJECT:REGION:INSTANCE
```

Then connect via:
```bash
psql -h 127.0.0.1 -U fusion_prime_app fusion_prime
```

### Method 2: Private IP (from same VPC)

```bash
psql -h 10.0.0.3 -U fusion_prime_app fusion_prime
```

### Method 3: From Cloud Run / GKE

**Cloud Run** (add to service):
```yaml
spec:
  template:
    metadata:
      annotations:
        run.googleapis.com/cloudsql-instances: PROJECT:REGION:INSTANCE
    spec:
      serviceAccountName: cloudsql-proxy-sa
```

**GKE** (use Cloud SQL Proxy sidecar):
```yaml
containers:
- name: cloud-sql-proxy
  image: gcr.io/cloud-sql-connectors/cloud-sql-proxy:2.8.0
  args:
    - "--structured-logs"
    - "--private-ip"
    - "PROJECT:REGION:INSTANCE"
  securityContext:
    runAsNonRoot: true
```

## Database Flags Reference

### Connection Settings
```hcl
{
  name  = "max_connections"
  value = "100"  # Adjust based on workload
}
```

### Memory Settings
```hcl
# Shared buffers (25% of RAM)
{
  name  = "shared_buffers"
  value = "262144"  # 256MB in 8KB pages
}

# Effective cache size (50-75% of RAM)
{
  name  = "effective_cache_size"
  value = "524288"  # 512MB in 8KB pages
}

# Work memory per query
{
  name  = "work_mem"
  value = "4096"  # 4MB in KB
}

# Maintenance work memory
{
  name  = "maintenance_work_mem"
  value = "65536"  # 64MB in KB
}
```

### Performance Monitoring
```hcl
# Log slow queries
{
  name  = "log_min_duration_statement"
  value = "1000"  # ms
}

# Auto explain slow queries
{
  name  = "auto_explain.log_min_duration"
  value = "1000"  # ms
}
```

## Cost Estimation

### Development

| Component | Configuration | Monthly Cost (USD) |
|-----------|--------------|-------------------|
| Instance | db-g1-small (1 vCPU, 1.7 GB) | ~$25 |
| Storage | 10 GB SSD | ~$2 |
| Backups | 7 days | ~$1 |
| **Total** | | **~$28/month** |

### Production

| Component | Configuration | Monthly Cost (USD) |
|-----------|--------------|-------------------|
| Primary | db-n1-standard-2 (2 vCPU, 7.5 GB) | ~$135 |
| HA Standby | Same as primary | ~$135 |
| Read Replica | db-n1-standard-1 (1 vCPU, 3.75 GB) | ~$70 |
| Storage | 100 GB SSD (primary + standby) | ~$34 |
| Backups | 30 days, ~50 GB | ~$10 |
| Network (egress) | ~100 GB/month | ~$12 |
| **Total** | | **~$396/month** |

*Costs are estimates and may vary by region and actual usage.*

## Monitoring

### Key Metrics to Monitor

1. **CPU Utilization**: Keep < 80%
2. **Memory Utilization**: Keep < 90%
3. **Disk Utilization**: Keep < 80%
4. **Connection Count**: Monitor vs. max_connections
5. **Replication Lag**: For read replicas

### Cloud Monitoring Queries

**CPU Utilization**:
```
resource.type="cloudsql_database"
metric.type="cloudsql.googleapis.com/database/cpu/utilization"
```

**Active Connections**:
```
resource.type="cloudsql_database"
metric.type="cloudsql.googleapis.com/database/postgresql/num_backends"
```

**Disk Usage**:
```
resource.type="cloudsql_database"
metric.type="cloudsql.googleapis.com/database/disk/utilization"
```

## Security Best Practices

1. ✅ **Private IP Only**: Disable public IP
2. ✅ **SSL Required**: Always enforce SSL connections
3. ✅ **Secret Manager**: Store passwords in Secret Manager
4. ✅ **Service Accounts**: Use Cloud SQL Proxy with service accounts
5. ✅ **IAM**: Use least-privilege IAM roles
6. ✅ **Deletion Protection**: Enable in production
7. ✅ **Automated Backups**: Configure and test backups
8. ✅ **VPC Peering**: Use VPC peering for private connectivity

## Backup & Recovery

### Manual Backup

```bash
gcloud sql backups create \
  --instance INSTANCE_NAME \
  --project PROJECT_ID
```

### Point-in-Time Recovery

```bash
gcloud sql backups restore BACKUP_ID \
  --backup-instance SOURCE_INSTANCE \
  --backup-project PROJECT_ID \
  --target-instance TARGET_INSTANCE
```

### Export to Cloud Storage

```bash
gcloud sql export sql INSTANCE_NAME gs://BUCKET/backup.sql \
  --database=fusion_prime \
  --offload
```

## Troubleshooting

### Connection Refused

**Check**:
1. Private IP is correctly configured
2. VPC network allows connections
3. Cloud SQL Proxy is running
4. Service account has `cloudsql.client` role

### High CPU Usage

**Solutions**:
1. Upgrade instance tier
2. Optimize slow queries (use Query Insights)
3. Add read replica for read-heavy workloads
4. Increase connection pooling

### Out of Disk Space

**Solutions**:
1. Enable disk autoresize
2. Increase autoresize limit
3. Manually increase disk size
4. Archive/delete old data

## Migration

### From Existing PostgreSQL

```bash
# Export from source
pg_dump -h SOURCE_HOST -U USER -d DB_NAME > dump.sql

# Import to Cloud SQL
psql -h CLOUDSQL_HOST -U fusion_prime_app fusion_prime < dump.sql
```

### From Cloud SQL to Cloud SQL

```bash
gcloud sql instances clone SOURCE_INSTANCE TARGET_INSTANCE \
  --project PROJECT_ID
```

## Requirements

| Name | Version |
|------|---------|
| terraform | >= 1.5.0 |
| google | ~> 5.0 |

## Providers

| Name | Version |
|------|---------|
| google | ~> 5.0 |
| random | ~> 3.5 |

## License

MIT License - See root LICENSE file

