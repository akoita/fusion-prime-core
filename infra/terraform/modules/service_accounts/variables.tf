variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "state_bucket_name" {
  description = "Name of the Terraform state bucket (optional)"
  type        = string
  default     = ""
}

