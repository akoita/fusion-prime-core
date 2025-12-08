# Artifact Registry Module Variables

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "project_number" {
  description = "GCP project number (for Cloud Build service account)"
  type        = string
  default     = ""
}

variable "region" {
  description = "GCP region for the Artifact Registry"
  type        = string
  default     = "us-central1"
}

variable "repository_name" {
  description = "Name of the Artifact Registry repository"
  type        = string
  default     = "services"
}

variable "description" {
  description = "Description of the repository"
  type        = string
  default     = "Container images for Fusion Prime services"
}

variable "environment" {
  description = "Environment (dev, staging, production)"
  type        = string
  default     = "dev"
}

variable "labels" {
  description = "Additional labels to apply to the repository"
  type        = map(string)
  default     = {}
}

variable "grant_cloudbuild_access" {
  description = "Grant Cloud Build service account write access"
  type        = bool
  default     = true
}

variable "service_accounts" {
  description = "Map of service accounts that need read access (name => email)"
  type        = map(string)
  default     = {}
}

variable "enable_cleanup_policies" {
  description = "Enable automatic cleanup policies for cost management"
  type        = bool
  default     = true
}

variable "untagged_retention_days" {
  description = "Number of days to keep untagged images"
  type        = number
  default     = 30
}

variable "minimum_versions_to_keep" {
  description = "Minimum number of versions to keep regardless of age"
  type        = number
  default     = 10
}

