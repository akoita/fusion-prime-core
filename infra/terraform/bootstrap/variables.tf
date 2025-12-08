variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "bucket_name" {
  description = "Name of the GCS bucket for Terraform state"
  type        = string
  default     = "fusion-prime-bucket-1"
}

variable "bucket_location" {
  description = "Location for the GCS bucket"
  type        = string
  default     = "US"
}

variable "region" {
  description = "Default GCP region"
  type        = string
  default     = "us-central1"
}

