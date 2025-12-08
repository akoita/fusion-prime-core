resource "google_compute_network" "vpc" {
  name                    = var.network_name
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  name          = "${var.network_name}-primary"
  ip_cidr_range = var.subnet_cidr
  region        = var.region
  network       = google_compute_network.vpc.id
}

# Allocate IP address range for Google services (Cloud SQL, etc.)
resource "google_compute_global_address" "private_ip_address" {
  name          = "${var.network_name}-private-services"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
}

# Create private VPC connection for Google services
resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
}

resource "google_service_account" "service_accounts" {
  for_each = toset(var.service_account_ids)

  account_id   = each.value
  display_name = "${var.network_name}-${each.value}"
}

# VPC Access Connector for Cloud Run
resource "google_vpc_access_connector" "connector" {
  name          = "fusion-prime-connector"
  region        = var.region
  ip_cidr_range = var.vpc_connector_cidr
  network       = google_compute_network.vpc.name
  min_instances = 2
  max_instances = 3
  machine_type  = "e2-micro"
}

# Secret Manager IAM bindings for service accounts
resource "google_secret_manager_secret_iam_binding" "db_password_access" {
  count     = length(var.service_account_ids)
  secret_id = var.db_password_secret_id
  role      = "roles/secretmanager.secretAccessor"
  members = [
    "serviceAccount:${google_service_account.service_accounts[var.service_account_ids[count.index]].email}"
  ]
}

# Secret Manager IAM bindings for Cloud Build
resource "google_secret_manager_secret_iam_binding" "cloud_build_access" {
  count     = length(var.secret_ids)
  secret_id = var.secret_ids[count.index]
  role      = "roles/secretmanager.secretAccessor"
  members = [
    "serviceAccount:${var.project_number}@cloudbuild.gserviceaccount.com"
  ]
}

# Cloud Build IAM bindings for Cloud Run management
resource "google_project_iam_member" "cloud_build_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${var.project_number}@cloudbuild.gserviceaccount.com"
}

# Cloud Build IAM bindings for Cloud Run IAM policy management
resource "google_project_iam_member" "cloud_build_run_iam" {
  project = var.project_id
  role    = "roles/run.serviceAgent"
  member  = "serviceAccount:${var.project_number}@cloudbuild.gserviceaccount.com"
}

# Cloud Build IAM bindings for Service Account User
resource "google_project_iam_member" "cloud_build_service_account_user" {
  for_each = toset(var.service_account_ids)
  project  = var.project_id
  role     = "roles/iam.serviceAccountUser"
  member   = "serviceAccount:${var.project_number}@cloudbuild.gserviceaccount.com"
}

# Cloud Build IAM bindings for Cloud SQL Client
resource "google_project_iam_member" "cloud_build_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${var.project_number}@cloudbuild.gserviceaccount.com"
}

output "network_id" {
  value = google_compute_network.vpc.id
}

output "subnet_id" {
  value = google_compute_subnetwork.subnet.id
}

output "service_accounts" {
  value = { for k, v in google_service_account.service_accounts : k => v.email }
}

output "private_vpc_connection" {
  value       = google_service_networking_connection.private_vpc_connection.network
  description = "VPC connection for private services (Cloud SQL, etc.)"
}

output "vpc_connector_name" {
  value       = google_vpc_access_connector.connector.name
  description = "VPC Access Connector name for Cloud Run"
}

