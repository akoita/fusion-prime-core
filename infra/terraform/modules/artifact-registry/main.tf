# Artifact Registry Module for Fusion Prime
# Creates Docker repositories for container images

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# Docker repository for service containers
resource "google_artifact_registry_repository" "services" {
  location      = var.region
  repository_id = var.repository_name
  description   = var.description
  format        = "DOCKER"
  project       = var.project_id

  labels = merge(
    {
      environment = var.environment
      managed_by  = "terraform"
      purpose     = "container-images"
    },
    var.labels
  )

  # Cleanup policies for managing storage costs
  cleanup_policy_dry_run = false

  dynamic "cleanup_policies" {
    for_each = var.enable_cleanup_policies ? [1] : []
    content {
      id     = "delete-untagged"
      action = "DELETE"

      condition {
        tag_state    = "UNTAGGED"
        older_than   = "${var.untagged_retention_days * 24 * 60 * 60}s"
      }
    }
  }

  dynamic "cleanup_policies" {
    for_each = var.enable_cleanup_policies ? [1] : []
    content {
      id     = "keep-minimum-versions"
      action = "KEEP"

      most_recent_versions {
        keep_count = var.minimum_versions_to_keep
      }
    }
  }
}

# IAM binding for Cloud Build to push images
resource "google_artifact_registry_repository_iam_member" "cloudbuild_writer" {
  count = var.grant_cloudbuild_access ? 1 : 0

  project    = var.project_id
  location   = google_artifact_registry_repository.services.location
  repository = google_artifact_registry_repository.services.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${var.project_number}@cloudbuild.gserviceaccount.com"
}

# IAM binding for Cloud Run to pull images
resource "google_artifact_registry_repository_iam_member" "cloudrun_reader" {
  for_each = var.service_accounts

  project    = var.project_id
  location   = google_artifact_registry_repository.services.location
  repository = google_artifact_registry_repository.services.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${each.value}"
}
