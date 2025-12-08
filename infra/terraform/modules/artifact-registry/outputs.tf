# Artifact Registry Module Outputs

output "repository_id" {
  description = "The ID of the created repository"
  value       = google_artifact_registry_repository.services.repository_id
}

output "repository_name" {
  description = "The full name of the repository"
  value       = google_artifact_registry_repository.services.name
}

output "location" {
  description = "The location of the repository"
  value       = google_artifact_registry_repository.services.location
}

output "repository_url" {
  description = "The base URL for pushing/pulling images"
  value       = "${google_artifact_registry_repository.services.location}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.services.repository_id}"
}

output "console_url" {
  description = "URL to view the repository in Cloud Console"
  value       = "https://console.cloud.google.com/artifacts/docker/${var.project_id}/${google_artifact_registry_repository.services.location}/${google_artifact_registry_repository.services.repository_id}"
}

