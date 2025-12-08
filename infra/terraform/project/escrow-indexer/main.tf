# Escrow Indexer Infrastructure
# Provisions all required infrastructure for the Escrow Indexer service:
# - Cloud SQL PostgreSQL database
# - Pub/Sub subscription
# - Cloud Run service
# - Secret Manager secrets
# - IAM permissions

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }

  backend "gcs" {
    bucket = "fusion-prime-terraform-state"
    prefix = "services/escrow-indexer"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Data sources
data "google_project" "project" {
  project_id = var.project_id
}

data "google_compute_network" "vpc" {
  name = var.vpc_network_name
}

# Cloud SQL PostgreSQL Database
module "escrow_indexer_db" {
  source = "../../modules/cloudsql"

  project_id            = var.project_id
  region                = var.region
  environment           = var.environment
  instance_name         = "escrow-indexer-db"
  database_name         = "escrow_indexer"
  database_version      = "POSTGRES_15"

  # Tier - use db-f1-micro for dev, db-n1-standard-1+ for production
  tier                  = var.environment == "prod" ? "db-n1-standard-1" : "db-f1-micro"

  # High availability for production
  high_availability     = var.environment == "prod"

  # Disk configuration
  disk_type             = "PD_SSD"
  disk_size_gb          = var.environment == "prod" ? 20 : 10
  disk_autoresize       = true
  disk_autoresize_limit = 100

  # Network
  vpc_network_id        = data.google_compute_network.vpc.id
  enable_public_ip      = var.enable_db_public_ip
  authorized_networks   = var.db_authorized_networks

  # Backup configuration
  backup_start_time              = "03:00"
  enable_point_in_time_recovery  = var.environment == "prod"
  transaction_log_retention_days = var.environment == "prod" ? 7 : 1
  retained_backups               = var.environment == "prod" ? 30 : 7

  # Maintenance window (Sunday 3-4 AM)
  maintenance_window_day         = 7
  maintenance_window_hour        = 3
  maintenance_window_update_track = var.environment == "prod" ? "stable" : "canary"

  # Database user
  app_user_name                  = "escrow_indexer"
  app_user_password              = ""  # Auto-generated

  # Features
  enable_query_insights           = true
  enable_deletion_protection      = var.environment == "prod"
  store_password_in_secret_manager = true
  create_proxy_service_account    = true

  # Read replica for production
  enable_read_replica = var.environment == "prod"
  replica_tier        = "db-n1-standard-1"

  # Database flags for PostgreSQL optimization
  # Different values for dev (f1-micro) vs prod (n1-standard)
  database_flags = var.environment == "prod" ? [
    # Production flags (for db-n1-standard-1+)
    {
      name  = "max_connections"
      value = "100"
    },
    {
      name  = "shared_buffers"
      value = "262144"  # 256MB in 8KB pages
    },
    {
      name  = "work_mem"
      value = "4096"    # 4MB in KB
    },
    {
      name  = "maintenance_work_mem"
      value = "65536"   # 64MB in KB
    },
    {
      name  = "effective_cache_size"
      value = "1048576" # 1GB in 8KB pages
    },
  ] : [
    # Development flags (for db-f1-micro with 1GB RAM)
    {
      name  = "max_connections"
      value = "25"
    },
    {
      name  = "shared_buffers"
      value = "32768"   # 32MB in 8KB pages (safe for f1-micro)
    },
    {
      name  = "work_mem"
      value = "2048"    # 2MB in KB
    },
    {
      name  = "maintenance_work_mem"
      value = "16384"   # 16MB in KB
    },
    {
      name  = "effective_cache_size"
      value = "70000"   # ~70MB in 8KB pages (safe for f1-micro)
    },
  ]

  labels = {
    service    = "escrow-indexer"
    managed_by = "terraform"
  }
}

# Pub/Sub Subscription for Escrow Events
resource "google_pubsub_subscription" "escrow_indexer" {
  name  = "escrow-indexer-sub"
  topic = "settlement.events.v1"  # Topic created by relayer service
  project = var.project_id

  # Subscription configuration
  ack_deadline_seconds = 60
  message_retention_duration = "604800s"  # 7 days
  retain_acked_messages = false
  enable_message_ordering = false

  # Retry policy
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"  # 10 minutes
  }

  # Expiration policy (subscription won't expire)
  expiration_policy {
    ttl = ""
  }

  # Dead letter policy (after 5 retries, send to DLQ)
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.escrow_indexer_dlq.id
    max_delivery_attempts = 5
  }

  labels = {
    service    = "escrow-indexer"
    managed_by = "terraform"
    environment = var.environment
  }
}

# Dead Letter Queue topic for failed messages
resource "google_pubsub_topic" "escrow_indexer_dlq" {
  name    = "escrow-indexer-dlq"
  project = var.project_id

  labels = {
    service    = "escrow-indexer"
    managed_by = "terraform"
    type       = "dead-letter-queue"
  }
}

# DLQ subscription for monitoring
resource "google_pubsub_subscription" "escrow_indexer_dlq_sub" {
  name  = "escrow-indexer-dlq-sub"
  topic = google_pubsub_topic.escrow_indexer_dlq.name
  project = var.project_id

  # Never expire messages in DLQ
  message_retention_duration = "604800s"  # 7 days
  retain_acked_messages = true

  labels = {
    service    = "escrow-indexer"
    managed_by = "terraform"
    type       = "dead-letter-queue"
  }
}

# Cloud Run Service
module "escrow_indexer_service" {
  source = "../../modules/cloud_run_service"

  project_id   = var.project_id
  region       = var.region
  environment  = var.environment
  service_name = "escrow-indexer"

  # Container configuration
  container_image = var.container_image
  container_port  = 8080

  # Resources
  cpu_limit          = var.environment == "prod" ? "2" : "1"
  memory_limit       = var.environment == "prod" ? "1Gi" : "512Mi"
  cpu_always_allocated = false
  startup_cpu_boost    = true

  # Scaling
  min_instances = var.environment == "prod" ? 1 : 0
  max_instances = var.environment == "prod" ? 10 : 5

  # Timeout - long timeout for Pub/Sub subscriber
  timeout_seconds = 3600

  # VPC configuration
  vpc_connector_id = var.vpc_connector_id
  vpc_egress       = "private-ranges-only"

  # Environment variables
  env_vars = {
    PUBSUB_PROJECT_ID      = var.project_id
    PUBSUB_SUBSCRIPTION_ID = google_pubsub_subscription.escrow_indexer.name
    GCP_PROJECT            = var.project_id
    LOG_LEVEL              = var.environment == "prod" ? "INFO" : "DEBUG"
  }

  # Secrets from Secret Manager
  secret_env_vars = {
    DATABASE_URL = {
      secret_name = module.escrow_indexer_db.connection_string_secret_id
      version     = "latest"
    }
  }

  # Cloud SQL connection
  cloudsql_instances = [module.escrow_indexer_db.instance_connection_name]

  # Access
  allow_unauthenticated = true  # API is public
  invoker_members       = []

  # Health checks
  enable_health_check = true
  health_check_path   = "/health"

  # Monitoring
  enable_monitoring      = var.environment == "prod"
  error_rate_threshold   = 10
  latency_threshold_ms   = 1000
  notification_channels  = var.notification_channels

  labels = {
    service    = "escrow-indexer"
    managed_by = "terraform"
  }
}

# IAM for Pub/Sub subscription
resource "google_pubsub_subscription_iam_member" "escrow_indexer_subscriber" {
  subscription = google_pubsub_subscription.escrow_indexer.name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:${module.escrow_indexer_service.service_account_email}"
  project      = var.project_id
}

# IAM for DLQ topic (to publish failed messages)
resource "google_pubsub_topic_iam_member" "escrow_indexer_dlq_publisher" {
  topic   = google_pubsub_topic.escrow_indexer_dlq.name
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
  project = var.project_id
}

# Outputs
output "database_instance_name" {
  description = "Cloud SQL instance name"
  value       = module.escrow_indexer_db.instance_name
}

output "database_connection_name" {
  description = "Cloud SQL connection name"
  value       = module.escrow_indexer_db.instance_connection_name
}

output "database_private_ip" {
  description = "Database private IP address"
  value       = module.escrow_indexer_db.private_ip_address
}

output "pubsub_subscription_id" {
  description = "Pub/Sub subscription ID"
  value       = google_pubsub_subscription.escrow_indexer.id
}

output "service_url" {
  description = "Cloud Run service URL"
  value       = module.escrow_indexer_service.service_url
}

output "service_account_email" {
  description = "Service account email"
  value       = module.escrow_indexer_service.service_account_email
}
