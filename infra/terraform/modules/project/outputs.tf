output "project_id" {
  description = "The GCP project ID"
  value       = var.project_id
}

output "project_number" {
  description = "The GCP project number"
  value       = var.create_project ? google_project.fusion_prime[0].number : null
}

output "enabled_apis" {
  description = "List of enabled APIs"
  value       = [for api in google_project_service.required_apis : api.service]
}

