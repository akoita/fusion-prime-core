# Cloud SQL Module Variables

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for the Cloud SQL instance"
  type        = string
  default     = "us-central1"
}

variable "instance_name" {
  description = "Name of the Cloud SQL instance (will be suffixed with random ID)"
  type        = string
  default     = "fusion-prime-db"
}

variable "database_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "POSTGRES_16"

  validation {
    condition     = can(regex("^POSTGRES_\\d+$", var.database_version))
    error_message = "Database version must be in format POSTGRES_XX (e.g., POSTGRES_16)."
  }
}

variable "tier" {
  description = "Machine type for the instance (e.g., db-f1-micro, db-g1-small, db-n1-standard-1)"
  type        = string
  default     = "db-g1-small"
}

variable "high_availability" {
  description = "Enable high availability (REGIONAL) or single zone (ZONAL)"
  type        = bool
  default     = true
}

variable "disk_type" {
  description = "Disk type (PD_SSD or PD_HDD)"
  type        = string
  default     = "PD_SSD"

  validation {
    condition     = contains(["PD_SSD", "PD_HDD"], var.disk_type)
    error_message = "Disk type must be either PD_SSD or PD_HDD."
  }
}

variable "disk_size_gb" {
  description = "Initial disk size in GB"
  type        = number
  default     = 10

  validation {
    condition     = var.disk_size_gb >= 10 && var.disk_size_gb <= 65536
    error_message = "Disk size must be between 10 GB and 65536 GB."
  }
}

variable "disk_autoresize" {
  description = "Enable automatic disk size increase"
  type        = bool
  default     = true
}

variable "disk_autoresize_limit" {
  description = "Maximum disk size in GB for autoresize (0 = unlimited)"
  type        = number
  default     = 100
}

variable "enable_public_ip" {
  description = "Enable public IP address"
  type        = bool
  default     = false
}

variable "vpc_network_id" {
  description = "VPC network ID for private IP (required if enable_public_ip = false)"
  type        = string
}

variable "authorized_networks" {
  description = "List of authorized networks (only used if public IP is enabled)"
  type = list(object({
    name = string
    cidr = string
  }))
  default = []
}

variable "backup_start_time" {
  description = "Backup start time in UTC (HH:MM format)"
  type        = string
  default     = "03:00"

  validation {
    condition     = can(regex("^([01]\\d|2[0-3]):[0-5]\\d$", var.backup_start_time))
    error_message = "Backup start time must be in HH:MM format."
  }
}

variable "enable_point_in_time_recovery" {
  description = "Enable point-in-time recovery (requires transaction logs)"
  type        = bool
  default     = true
}

variable "transaction_log_retention_days" {
  description = "Number of days to retain transaction logs for point-in-time recovery"
  type        = number
  default     = 7

  validation {
    condition     = var.transaction_log_retention_days >= 1 && var.transaction_log_retention_days <= 7
    error_message = "Transaction log retention must be between 1 and 7 days."
  }
}

variable "retained_backups" {
  description = "Number of automated backups to retain"
  type        = number
  default     = 7

  validation {
    condition     = var.retained_backups >= 1 && var.retained_backups <= 365
    error_message = "Retained backups must be between 1 and 365."
  }
}

variable "maintenance_window_day" {
  description = "Day of week for maintenance window (1=Monday, 7=Sunday)"
  type        = number
  default     = 7

  validation {
    condition     = var.maintenance_window_day >= 1 && var.maintenance_window_day <= 7
    error_message = "Maintenance window day must be between 1 (Monday) and 7 (Sunday)."
  }
}

variable "maintenance_window_hour" {
  description = "Hour of day for maintenance window (0-23)"
  type        = number
  default     = 3

  validation {
    condition     = var.maintenance_window_hour >= 0 && var.maintenance_window_hour <= 23
    error_message = "Maintenance window hour must be between 0 and 23."
  }
}

variable "maintenance_window_update_track" {
  description = "Maintenance update track (stable or canary)"
  type        = string
  default     = "stable"

  validation {
    condition     = contains(["stable", "canary"], var.maintenance_window_update_track)
    error_message = "Maintenance update track must be either 'stable' or 'canary'."
  }
}

variable "database_flags" {
  description = "Database flags to set on the instance"
  type = list(object({
    name  = string
    value = string
  }))
  default = [
    {
      name  = "max_connections"
      value = "100"
    },
    {
      name  = "shared_buffers"
      value = "262144" # 256MB in 8KB pages
    },
    {
      name  = "work_mem"
      value = "4096" # 4MB in KB
    },
    {
      name  = "maintenance_work_mem"
      value = "65536" # 64MB in KB
    },
    {
      name  = "effective_cache_size"
      value = "524288" # 512MB in 8KB pages
    },
    {
      name  = "log_min_duration_statement"
      value = "1000" # Log queries taking > 1 second
    },
  ]
}

variable "enable_query_insights" {
  description = "Enable Query Insights for performance monitoring"
  type        = bool
  default     = true
}

variable "database_name" {
  description = "Name of the primary database to create"
  type        = string
  default     = "fusion_prime"
}

variable "app_user_name" {
  description = "Username for the application database user"
  type        = string
  default     = "fusion_prime_app"
}

variable "app_user_password" {
  description = "Password for the application user (leave empty to auto-generate)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "enable_read_replica" {
  description = "Enable read replica for increased read performance"
  type        = bool
  default     = false
}

variable "replica_region" {
  description = "Region for read replica (leave empty to use same as primary)"
  type        = string
  default     = ""
}

variable "replica_tier" {
  description = "Machine type for read replica (leave empty to use same as primary)"
  type        = string
  default     = ""
}

variable "create_proxy_service_account" {
  description = "Create a service account for Cloud SQL Proxy"
  type        = bool
  default     = true
}

variable "store_password_in_secret_manager" {
  description = "Store database password in Secret Manager"
  type        = bool
  default     = true
}

variable "enable_deletion_protection" {
  description = "Enable deletion protection (recommended for production)"
  type        = bool
  default     = true
}

variable "environment" {
  description = "Environment (dev, staging, production)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be one of: dev, staging, production."
  }
}

variable "labels" {
  description = "Additional labels to apply to resources"
  type        = map(string)
  default     = {}
}

