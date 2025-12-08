variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "topic_name" {
  description = "Name of the settlement events topic"
  type        = string
}

variable "subscription_name" {
  description = "Name of the settlement events subscription"
  type        = string
}

variable "service_account_email" {
  description = "Service account email granted Pub/Sub access"
  type        = string
}
