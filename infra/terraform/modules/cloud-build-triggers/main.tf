# Cloud Build Triggers for Fusion Prime
# Automated deployment triggers for CI/CD

# Settlement Service Trigger
resource "google_cloudbuild_trigger" "settlement_service" {
  name        = "settlement-service-deploy"
  description = "Deploy settlement service on push to main branch"

  # Manual trigger (no GitHub integration)
  # github {
  #   owner = var.github_owner
  #   name  = var.github_repo
  #   push {
  #     branch = "^main$"
  #   }
  # }

  # Build configuration
  filename = "cloudbuild-deploy.yaml"

  # Substitutions
  substitutions = {
    _SERVICE = "settlement"
    _CONFIG_SECRET = "settlement-service-config-test"
  }

  # Include only settlement service files
  included_files = [
    "services/settlement/**",
    "cloudbuild-deploy.yaml",
    "services/settlement/cloudbuild-minimal.yaml"
  ]

  # Ignore other service changes
  ignored_files = [
    "services/relayer/**",
    "services/risk/**",
    "integrations/**"
  ]
}

# Event Relayer Trigger
resource "google_cloudbuild_trigger" "event_relayer" {
  name        = "event-relayer-deploy"
  description = "Deploy event relayer on push to main branch"

  # Manual trigger (no GitHub integration)
  # github {
  #   owner = var.github_owner
  #   name  = var.github_repo
  #   push {
  #     branch = "^main$"
  #   }
  # }

  # Build configuration
  filename = "cloudbuild-deploy.yaml"

  # Substitutions
  substitutions = {
    _SERVICE = "relayer"
    _CONFIG_SECRET = "relayer-service-config-test"
  }

  # Include only relayer files
  included_files = [
    "integrations/relayers/escrow/**",
    "cloudbuild-deploy.yaml"
  ]

  # Ignore other service changes
  ignored_files = [
    "services/settlement/**",
    "services/risk/**"
  ]
}

# Multi-service build trigger (for testing)
resource "google_cloudbuild_trigger" "multi_service_build" {
  name        = "multi-service-build"
  description = "Build all services on push to main branch"

  # Manual trigger (no GitHub integration)
  # github {
  #   owner = var.github_owner
  #   name  = var.github_repo
  #   push {
  #     branch = "^main$"
  #   }
  # }

  # Build configuration
  filename = "cloudbuild.yaml"

  # Build all services
  substitutions = {
    _TAG = "latest"
    _REGION = "us-central1"
    _REPOSITORY = "services"
    _SERVICES = "all"
  }
}
