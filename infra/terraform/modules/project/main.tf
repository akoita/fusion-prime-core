# Fusion Prime Project Module
# Manages GCP project configuration and API enablement

# Enable required GCP APIs for Fusion Prime platform
resource "google_project_service" "required_apis" {
  for_each = toset([
    "compute.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "sqladmin.googleapis.com",
    "pubsub.googleapis.com",
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "clouddeploy.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "cloudtrace.googleapis.com",
    "servicenetworking.googleapis.com",
    "vpcaccess.googleapis.com",
    "cloudkms.googleapis.com",
    "bigquery.googleapis.com",
    "dataflow.googleapis.com",
    "firestore.googleapis.com",
    "bigtable.googleapis.com",
    "container.googleapis.com",
    "cloudscheduler.googleapis.com",
    "cloudtasks.googleapis.com"
  ])

  project = var.project_id
  service = each.key

  disable_on_destroy = false
}

# Project-level IAM audit config
resource "google_project_iam_audit_config" "project" {
  project = var.project_id
  service = "allServices"

  audit_log_config {
    log_type = "ADMIN_READ"
  }

  audit_log_config {
    log_type = "DATA_READ"
  }

  audit_log_config {
    log_type = "DATA_WRITE"
  }
}

# Project metadata for labels and organization
resource "google_project" "fusion_prime" {
  count           = var.create_project ? 1 : 0
  name            = var.project_id
  project_id      = var.project_id
  billing_account = var.billing_account
  org_id          = var.org_id

  labels = {
    environment = "production"
    platform    = "fusion-prime"
    managed-by  = "terraform"
  }

  auto_create_network = false
}

