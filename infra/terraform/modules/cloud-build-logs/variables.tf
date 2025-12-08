variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "project_number" {
  description = "The GCP project number"
  type        = string
}

variable "bucket_name" {
  description = "Name of the Cloud Build logs bucket"
  type        = string
  default     = "fusion-prime-cloud-build-logs"
}

variable "location" {
  description = "Location for the bucket"
  type        = string
  default     = "US"
}

variable "force_destroy" {
  description = "When deleting a bucket, this boolean option will delete all contained objects"
  type        = bool
  default     = false
}

variable "versioning_enabled" {
  description = "Enable versioning for the bucket"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "Number of days to retain build logs"
  type        = number
  default     = 30
}

variable "labels" {
  description = "Labels to apply to the bucket"
  type        = map(string)
  default = {
    purpose     = "cloud-build-logs"
    environment = "shared"
    managed-by  = "terraform"
  }
}

variable "github_service_account_email" {
  description = "GitHub Actions service account email for log access"
  type        = string
  default     = null
}
