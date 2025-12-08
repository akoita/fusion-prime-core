# Fusion Prime Service Accounts Module
# Creates custom service accounts for different platform components

# Terraform state management service account
resource "google_service_account" "terraform_admin" {
  account_id   = "terraform-admin"
  display_name = "Terraform State Admin"
  description  = "Service account for Terraform state management and deployments"
  project      = var.project_id
}

# Settlement service account
resource "google_service_account" "settlement_service" {
  account_id   = "settlement-service"
  display_name = "Settlement Service"
  description  = "Service account for settlement microservice"
  project      = var.project_id
}

# Risk analytics service account
resource "google_service_account" "risk_service" {
  account_id   = "risk-service"
  display_name = "Risk Analytics Service"
  description  = "Service account for risk analytics and treasury operations"
  project      = var.project_id
}

# Compliance service account
resource "google_service_account" "compliance_service" {
  account_id   = "compliance-service"
  display_name = "Compliance Service"
  description  = "Service account for KYC/AML and compliance operations"
  project      = var.project_id
}

# Cross-chain integration service account
resource "google_service_account" "bridge_service" {
  account_id   = "bridge-service"
  display_name = "Cross-Chain Bridge Service"
  description  = "Service account for cross-chain messaging and settlement"
  project      = var.project_id
}

# Cloud Build service account for CI/CD
resource "google_service_account" "cicd_deployer" {
  account_id   = "cicd-deployer"
  display_name = "CI/CD Deployer"
  description  = "Service account for automated deployments via Cloud Build"
  project      = var.project_id
}

# Grant Terraform admin access to the state bucket
resource "google_storage_bucket_iam_member" "terraform_state_access" {
  count  = var.state_bucket_name != "" ? 1 : 0
  bucket = var.state_bucket_name
  role   = "roles/storage.admin"
  member = "serviceAccount:${google_service_account.terraform_admin.email}"
}

# Grant Cloud Run deployment permissions
resource "google_project_iam_member" "settlement_cloud_run" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.settlement_service.email}"
}

resource "google_project_iam_member" "risk_cloud_run" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.risk_service.email}"
}

# Grant Pub/Sub permissions
resource "google_project_iam_member" "settlement_pubsub" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.settlement_service.email}"
}

# Grant Secret Manager access
resource "google_project_iam_member" "settlement_secrets" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.settlement_service.email}"
}

resource "google_project_iam_member" "bridge_secrets" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.bridge_service.email}"
}

# Grant Cloud SQL access
resource "google_project_iam_member" "settlement_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.settlement_service.email}"
}

# Grant CI/CD deployer permissions
resource "google_project_iam_member" "cicd_clouddeploy" {
  project = var.project_id
  role    = "roles/clouddeploy.operator"
  member  = "serviceAccount:${google_service_account.cicd_deployer.email}"
}

resource "google_project_iam_member" "cicd_artifact_registry" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.cicd_deployer.email}"
}

