variable "environment" {
  description = "Environment name (dev, test, prod)"
  type        = string
  default     = "test"
}

variable "region" {
  description = "GCP region for BigQuery datasets"
  type        = string
  default     = "US"
}

variable "settlement_service_account" {
  description = "Settlement service account email"
  type        = string
}

variable "relayer_service_account" {
  description = "Relayer service account email"
  type        = string
}

variable "analytics_readers" {
  description = "List of members who can read analytics data"
  type        = list(string)
  default     = []
}
