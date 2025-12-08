variable "network_name" {
  description = "Name of the VPC network"
  type        = string
}

variable "subnet_cidr" {
  description = "CIDR range for the primary subnet"
  type        = string
}

variable "region" {
  description = "Region in which to create the subnet"
  type        = string
}

variable "service_account_ids" {
  description = "List of service account IDs to create"
  type        = list(string)
  default     = []
}

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "project_number" {
  description = "GCP Project Number"
  type        = string
}

variable "vpc_connector_cidr" {
  description = "CIDR range for VPC Access Connector"
  type        = string
  default     = "10.8.0.0/28"
}

variable "db_password_secret_id" {
  description = "Secret Manager secret ID for database password"
  type        = string
}

variable "secret_ids" {
  description = "List of Secret Manager secret IDs for Cloud Build access"
  type        = list(string)
  default     = []
}

