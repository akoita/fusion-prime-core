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

variable "create_project" {
  description = "Whether to create a new project or use an existing one"
  type        = bool
  default     = false
}

