# Cloud Run Service Module Variables

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run service"
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Name of the Cloud Run service"
  type        = string
}

variable "container_image" {
  description = "Container image URL (e.g., gcr.io/project/image:tag)"
  type        = string
}

variable "container_port" {
  description = "Port the container listens on"
  type        = number
  default     = 8000
}

variable "min_instances" {
  description = "Minimum number of instances"
  type        = number
  default     = 1
}

variable "max_instances" {
  description = "Maximum number of instances"
  type        = number
  default     = 10
}

variable "cpu_limit" {
  description = "CPU limit (e.g., '1000m', '2000m')"
  type        = string
  default     = "1000m"
}

variable "memory_limit" {
  description = "Memory limit (e.g., '512Mi', '1Gi')"
  type        = string
  default     = "512Mi"
}

variable "cpu_always_allocated" {
  description = "Keep CPU allocated when idle"
  type        = bool
  default     = false
}

variable "startup_cpu_boost" {
  description = "Enable startup CPU boost"
  type        = bool
  default     = true
}

variable "timeout_seconds" {
  description = "Request timeout in seconds"
  type        = number
  default     = 300
}

variable "vpc_connector_id" {
  description = "VPC connector ID (full path)"
  type        = string
}

variable "vpc_egress" {
  description = "VPC egress setting (private-ranges-only or all-traffic)"
  type        = string
  default     = "private-ranges-only"

  validation {
    condition     = contains(["private-ranges-only", "all-traffic"], var.vpc_egress)
    error_message = "VPC egress must be 'private-ranges-only' or 'all-traffic'."
  }
}

variable "cloudsql_instances" {
  description = "List of Cloud SQL instance connection names"
  type        = list(string)
  default     = []
}

variable "env_vars" {
  description = "Environment variables as key-value pairs"
  type        = map(string)
  default     = {}
}

variable "secret_env_vars" {
  description = "Environment variables from Secret Manager"
  type = map(object({
    secret_name = string
    version     = string
  }))
  default = {}
}

variable "enable_health_check" {
  description = "Enable liveness and startup probes"
  type        = bool
  default     = true
}

variable "health_check_path" {
  description = "Path for health check endpoint"
  type        = string
  default     = "/health/readiness"
}

variable "allow_unauthenticated" {
  description = "Allow unauthenticated access (public)"
  type        = bool
  default     = false
}

variable "invoker_members" {
  description = "List of members allowed to invoke the service"
  type        = list(string)
  default     = []
}

variable "enable_monitoring" {
  description = "Enable monitoring alerts"
  type        = bool
  default     = true
}

variable "error_rate_threshold" {
  description = "Error rate threshold for alerts (%)"
  type        = number
  default     = 5
}

variable "latency_threshold_ms" {
  description = "P95 latency threshold for alerts (ms)"
  type        = number
  default     = 1000
}

variable "notification_channels" {
  description = "List of notification channel IDs for alerts"
  type        = list(string)
  default     = []
}

variable "environment" {
  description = "Environment (dev, staging, production)"
  type        = string
  default     = "dev"
}

variable "labels" {
  description = "Additional labels"
  type        = map(string)
  default     = {}
}

