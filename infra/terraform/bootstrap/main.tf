# Bootstrap configuration to create GCS bucket for Terraform state
# This uses local state to create the remote state bucket

terraform {
  required_version = ">= 1.7.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
  }

  # Uses local state - no backend configuration
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Create GCS bucket for Terraform state storage
resource "google_storage_bucket" "terraform_state" {
  name          = var.bucket_name
  location      = var.bucket_location
  force_destroy = false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      num_newer_versions = 3
    }
    action {
      type = "Delete"
    }
  }

  labels = {
    purpose    = "terraform-state"
    platform   = "fusion-prime"
    managed-by = "terraform"
  }
}

# Optional: Grant access to additional service accounts
# Uncomment and modify if you need to grant specific service accounts access
# resource "google_storage_bucket_iam_member" "terraform_state_admin" {
#   bucket = google_storage_bucket.terraform_state.name
#   role   = "roles/storage.admin"
#   member = "serviceAccount:YOUR_SERVICE_ACCOUNT@YOUR_PROJECT.iam.gserviceaccount.com"
# }
