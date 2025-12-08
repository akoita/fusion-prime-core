# Variables for Escrow Indexer Infrastructure

variable "project_id" {
  description = "GCP project ID"
  type        = string
  default     = "fusion-prime"
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "vpc_network_name" {
  description = "VPC network name for Cloud SQL private IP"
  type        = string
  default     = "fusion-prime-vpc"
}

variable "vpc_connector_id" {
  description = "VPC connector ID for Cloud Run"
  type        = string
  default     = "projects/fusion-prime/locations/us-central1/connectors/fusion-prime-vpc-connector"
}

variable "container_image" {
  description = "Container image for Cloud Run service"
  type        = string
  default     = "gcr.io/fusion-prime/escrow-indexer:latest"
}

variable "enable_db_public_ip" {
  description = "Enable public IP for Cloud SQL (use false for production)"
  type        = bool
  default     = false
}

variable "db_authorized_networks" {
  description = "Authorized networks for Cloud SQL (if public IP enabled)"
  type = list(object({
    name = string
    cidr = string
  }))
  default = []
}

variable "notification_channels" {
  description = "Notification channels for monitoring alerts"
  type        = list(string)
  default     = []
}
