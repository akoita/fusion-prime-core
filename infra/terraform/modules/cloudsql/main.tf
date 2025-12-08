# Cloud SQL PostgreSQL Module for Fusion Prime
# Provisions a highly available PostgreSQL instance with:
# - Automatic backups
# - Point-in-time recovery
# - Read replicas (optional)
# - Private IP connectivity
# - Automated maintenance
# - Security best practices

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# Random suffix for unique instance naming
resource "random_id" "db_suffix" {
  byte_length = 4
}

# Cloud SQL PostgreSQL Instance
resource "google_sql_database_instance" "primary" {
  name             = "${var.instance_name}-${random_id.db_suffix.hex}"
  database_version = var.database_version
  region           = var.region
  project          = var.project_id

  # Deletion protection
  deletion_protection = var.enable_deletion_protection

  settings {
    tier              = var.tier
    availability_type = var.high_availability ? "REGIONAL" : "ZONAL"
    disk_type         = var.disk_type
    disk_size         = var.disk_size_gb
    disk_autoresize   = var.disk_autoresize
    disk_autoresize_limit = var.disk_autoresize_limit

    # Backup configuration
    backup_configuration {
      enabled                        = true
      start_time                     = var.backup_start_time # e.g., "03:00"
      point_in_time_recovery_enabled = var.enable_point_in_time_recovery
      transaction_log_retention_days = var.transaction_log_retention_days
      backup_retention_settings {
        retained_backups = var.retained_backups
        retention_unit   = "COUNT"
      }
    }

    # IP configuration (private IP)
    ip_configuration {
      ipv4_enabled    = var.enable_public_ip
      private_network = var.vpc_network_id
      ssl_mode        = "ENCRYPTED_ONLY"

      # Authorized networks (if public IP is enabled)
      dynamic "authorized_networks" {
        for_each = var.authorized_networks
        content {
          name  = authorized_networks.value.name
          value = authorized_networks.value.cidr
        }
      }
    }

    # Maintenance window
    maintenance_window {
      day          = var.maintenance_window_day # 1 = Monday, 7 = Sunday
      hour         = var.maintenance_window_hour
      update_track = var.maintenance_window_update_track # "stable" or "canary"
    }

    # Database flags
    dynamic "database_flags" {
      for_each = var.database_flags
      content {
        name  = database_flags.value.name
        value = database_flags.value.value
      }
    }

    # Insights configuration (for performance monitoring)
    insights_config {
      query_insights_enabled  = var.enable_query_insights
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = true
    }

    # User labels for cost tracking and organization
    user_labels = merge(
      {
        environment = var.environment
        managed_by  = "terraform"
        service     = "fusion-prime"
      },
      var.labels
    )
  }

  # Lifecycle
  lifecycle {
    prevent_destroy = false # Set to true in production
    ignore_changes = [
      settings[0].disk_size, # Ignore disk size changes from autoresize
    ]
  }

  # Timeouts
  timeouts {
    create = "30m"
    update = "30m"
    delete = "30m"
  }
}

# Primary database
resource "google_sql_database" "primary_db" {
  name     = var.database_name
  instance = google_sql_database_instance.primary.name
  project  = var.project_id
}

# Application user
resource "google_sql_user" "app_user" {
  name     = var.app_user_name
  instance = google_sql_database_instance.primary.name
  password = var.app_user_password != "" ? var.app_user_password : random_password.app_user_password[0].result
  project  = var.project_id
}

# Random password for app user (if not provided)
resource "random_password" "app_user_password" {
  count   = var.app_user_password == "" ? 1 : 0
  length  = 32
  special = true
}

# Read replica (optional, for production)
resource "google_sql_database_instance" "read_replica" {
  count = var.enable_read_replica ? 1 : 0

  name                 = "${var.instance_name}-replica-${random_id.db_suffix.hex}"
  master_instance_name = google_sql_database_instance.primary.name
  database_version     = var.database_version
  region               = var.replica_region != "" ? var.replica_region : var.region
  project              = var.project_id

  replica_configuration {
    failover_target = false
  }

  settings {
    tier              = var.replica_tier != "" ? var.replica_tier : var.tier
    availability_type = "ZONAL"
    disk_type         = var.disk_type
    disk_autoresize   = true

    ip_configuration {
      ipv4_enabled    = false
      private_network = var.vpc_network_id
      ssl_mode        = "ENCRYPTED_ONLY"
    }

    user_labels = merge(
      {
        environment = var.environment
        managed_by  = "terraform"
        service     = "fusion-prime"
        replica     = "true"
      },
      var.labels
    )
  }

  lifecycle {
    prevent_destroy = false
  }
}

# Service account for Cloud SQL Proxy (optional)
resource "google_service_account" "cloudsql_proxy" {
  count = var.create_proxy_service_account ? 1 : 0

  account_id   = "${var.instance_name}-proxy-sa"
  display_name = "Cloud SQL Proxy Service Account for ${var.instance_name}"
  project      = var.project_id
}

# IAM binding for Cloud SQL Client role
resource "google_project_iam_member" "cloudsql_client" {
  count = var.create_proxy_service_account ? 1 : 0

  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cloudsql_proxy[0].email}"
}

# Secret Manager secret for database password
resource "google_secret_manager_secret" "db_password" {
  count = var.store_password_in_secret_manager ? 1 : 0

  secret_id = "${var.instance_name}-db-password"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    service     = "fusion-prime"
  }
}

resource "google_secret_manager_secret_version" "db_password" {
  count = var.store_password_in_secret_manager ? 1 : 0

  secret      = google_secret_manager_secret.db_password[0].id
  secret_data = var.app_user_password != "" ? var.app_user_password : random_password.app_user_password[0].result
}

# Secret for connection string
resource "google_secret_manager_secret" "db_connection_string" {
  count = var.store_password_in_secret_manager ? 1 : 0

  secret_id = "${var.instance_name}-connection-string"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    service     = "fusion-prime"
  }
}

resource "google_secret_manager_secret_version" "db_connection_string" {
  count = var.store_password_in_secret_manager ? 1 : 0

  secret = google_secret_manager_secret.db_connection_string[0].id
  # Connection string format:
  # - For Cloud Run with VPC egress: Use private IP TCP connection
  # - For Cloud Run without VPC: Use Unix socket
  # - For local/dev: Use TCP connection
  #
  # Note: Using psycopg2 for synchronous database connections
  # when using VPC egress='private-ranges-only'
  #
  # Format: postgresql+psycopg2://user:pass@PRIVATE_IP:5432/dbname
  # URL-encode the password to handle special characters
  secret_data = format(
    "postgresql+psycopg2://%s:%s@%s:5432/%s",
    urlencode(var.app_user_name),
    urlencode(var.app_user_password != "" ? var.app_user_password : random_password.app_user_password[0].result),
    google_sql_database_instance.primary.private_ip_address,
    var.database_name
  )
}
