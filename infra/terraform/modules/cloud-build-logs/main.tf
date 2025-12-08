# Cloud Build Logs Bucket for VPC-SC Compliance
# This module creates a custom logs bucket for Cloud Build that can be placed
# inside a VPC-SC security perimeter, resolving the default logs bucket limitation.

resource "google_storage_bucket" "cloud_build_logs" {
  name          = var.bucket_name
  location      = var.location
  project       = var.project_id
  force_destroy = var.force_destroy

  # Enable versioning for log retention
  versioning {
    enabled = var.versioning_enabled
  }

  # Lifecycle management for log cleanup
  lifecycle_rule {
    condition {
      age = var.log_retention_days
    }
    action {
      type = "Delete"
    }
  }

  # Ensure uniform bucket-level access
  uniform_bucket_level_access = true

  # Labels for organization
  labels = var.labels
}

# IAM binding for Cloud Build service account to write logs
resource "google_storage_bucket_iam_member" "cloud_build_writer" {
  bucket = google_storage_bucket.cloud_build_logs.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${var.project_number}@cloudbuild.gserviceaccount.com"
}

# IAM binding for Cloud Build service account to read logs (for debugging)
resource "google_storage_bucket_iam_member" "cloud_build_reader" {
  bucket = google_storage_bucket.cloud_build_logs.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${var.project_number}@cloudbuild.gserviceaccount.com"
}

# IAM binding for GitHub Actions service account to read logs
resource "google_storage_bucket_iam_member" "github_actions_reader" {
  count  = var.github_service_account_email != null ? 1 : 0
  bucket = google_storage_bucket.cloud_build_logs.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${var.github_service_account_email}"
}

# IAM binding for project owners to manage logs
resource "google_storage_bucket_iam_member" "project_owners" {
  bucket = google_storage_bucket.cloud_build_logs.name
  role   = "roles/storage.admin"
  member = "group:${var.project_id}-owners@googlegroups.com"
}
