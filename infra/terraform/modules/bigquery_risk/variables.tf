# BigQuery Risk Analytics Module Variables

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "location" {
  description = "BigQuery dataset location (US, EU, asia-northeast1, etc.)"
  type        = string
  default     = "US"
}

variable "dataset_id" {
  description = "BigQuery dataset ID"
  type        = string
  default     = "fusion_prime_risk"
}

variable "dataset_friendly_name" {
  description = "Human-readable dataset name"
  type        = string
  default     = "Fusion Prime Risk Analytics"
}

variable "dataset_description" {
  description = "Dataset description"
  type        = string
  default     = "Risk analytics, portfolio tracking, and compliance data for Fusion Prime"
}

variable "default_table_expiration_ms" {
  description = "Default table expiration in milliseconds (0 = never)"
  type        = number
  default     = 0
}

variable "partition_expiration_days" {
  description = "Number of days to retain partitions (0 = never)"
  type        = number
  default     = 90

  validation {
    condition     = var.partition_expiration_days >= 0 && var.partition_expiration_days <= 3650
    error_message = "Partition expiration must be between 0 and 3650 days."
  }
}

variable "kms_key_name" {
  description = "Cloud KMS key name for encryption (leave empty for Google-managed)"
  type        = string
  default     = ""
}

variable "dataset_access" {
  description = "Access control list for the dataset"
  type = list(object({
    role           = string
    user_by_email  = optional(string)
    group_by_email = optional(string)
    special_group  = optional(string)
  }))
  default = []
}

variable "enable_scheduled_queries" {
  description = "Enable scheduled queries for daily aggregations"
  type        = bool
  default     = true
}

variable "dataflow_service_account_email" {
  description = "Service account email for Dataflow (for IAM binding)"
  type        = string
  default     = ""
}

variable "pubsub_service_account_email" {
  description = "Service account email for Pub/Sub (for streaming inserts)"
  type        = string
  default     = ""
}

variable "reader_members" {
  description = "List of members to grant read access (e.g., user:email@example.com, serviceAccount:sa@project.iam.gserviceaccount.com)"
  type        = list(string)
  default     = []
}

variable "enable_deletion_protection" {
  description = "Enable deletion protection for tables"
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

