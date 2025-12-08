# Artifact Registry for frontend container images (Risk Dashboard, etc.)

module "artifact_registry_frontend" {
  source = "../modules/artifact-registry"

  project_id      = var.project_id
  project_number  = data.google_project.project.number
  region          = var.region
  repository_name = "frontend"
  environment     = "dev"
  description     = "Docker repository for frontend applications (Risk Dashboard, etc.)"

  # Grant read access to Cloud Run service accounts
  service_accounts = {
    "risk-dashboard" = module.network.service_accounts["risk-dashboard"]
  }

  # Development cleanup policies (more aggressive to save costs)
  enable_cleanup_policies  = true
  untagged_retention_days  = 7  # Delete untagged after 7 days
  minimum_versions_to_keep = 10 # Keep at least 10 recent versions

  labels = {
    project = "fusion-prime"
    team    = "frontend"
    purpose = "frontend-applications"
  }
}

# Output for use in deployment scripts
output "frontend_artifact_registry_url" {
  description = "Base URL for frontend container images"
  value       = module.artifact_registry_frontend.repository_url
}

output "frontend_artifact_registry_console" {
  description = "Console URL to view frontend images"
  value       = module.artifact_registry_frontend.console_url
}
