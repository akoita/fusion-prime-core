# Cloud Run Service Module Outputs

output "service_name" {
  description = "Name of the Cloud Run service"
  value       = google_cloud_run_v2_service.service.name
}

output "service_url" {
  description = "URL of the deployed service"
  value       = google_cloud_run_v2_service.service.uri
}

output "service_id" {
  description = "Service ID"
  value       = google_cloud_run_v2_service.service.id
}

output "service_account_email" {
  description = "Email of the service account"
  value       = google_service_account.service.email
}

output "service_account_name" {
  description = "Name of the service account"
  value       = google_service_account.service.name
}

output "latest_revision" {
  description = "Latest revision name"
  value       = google_cloud_run_v2_service.service.latest_ready_revision
}

output "service_location" {
  description = "Location of the service"
  value       = google_cloud_run_v2_service.service.location
}

