variable "project_id" {
  description = "GCP project ID to host Fusion Prime resources"
  type        = string
}

variable "billing_account" {
  description = "Billing account ID linked to the project"
  type        = string
}

variable "org_id" {
  description = "Organization ID for project linkage"
  type        = string
}

variable "region" {
  description = "Default GCP region for regional resources"
  type        = string
  default     = "us-central1"
}

variable "project_number" {
  description = "GCP project number (numeric ID)"
  type        = string
}

variable "escrow_factory_address" {
  description = "Address of the deployed EscrowFactory contract"
  type        = string
  default     = ""
}

