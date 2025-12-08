# Artifact Registry for container images

# Get project number for Cloud Build service account
data "google_project" "project" {
  project_id = var.project_id
}

module "artifact_registry" {
  source = "../modules/artifact-registry"

  project_id      = var.project_id
  project_number  = data.google_project.project.number
  region          = var.region
  repository_name = "services"
  environment     = "dev"

  # Grant read access to Cloud Run service accounts
  service_accounts = module.network.service_accounts

  # Development cleanup policies (more aggressive to save costs)
  enable_cleanup_policies  = true
  untagged_retention_days  = 7  # Delete untagged after 7 days
  minimum_versions_to_keep = 10 # Keep at least 10 recent versions

  labels = {
    project = "fusion-prime"
    team    = "platform"
  }
}

# Output for use in deployment scripts
output "artifact_registry_url" {
  description = "Base URL for container images"
  value       = module.artifact_registry.repository_url
}

output "artifact_registry_console" {
  description = "Console URL to view images"
  value       = module.artifact_registry.console_url
}
