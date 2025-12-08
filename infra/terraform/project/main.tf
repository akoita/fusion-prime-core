terraform {
  required_version = ">= 1.7.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }

    google-beta = {
      source  = "hashicorp/google-beta"
      version = ">= 5.0"
    }
  }

  backend "gcs" {}
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

module "fusion_prime_project" {
  source = "../modules/project"

  project_id      = var.project_id
  billing_account = var.billing_account
  org_id          = var.org_id
}

module "network" {
  source = "../modules/network"

  network_name          = "fusion-prime-vpc"
  subnet_cidr           = "10.10.0.0/24"
  region                = var.region
  service_account_ids   = ["settlement-service", "risk-service", "relayer-service", "risk-dashboard"]
  project_id            = var.project_id
  project_number        = var.project_number
  vpc_connector_cidr    = "10.8.0.0/28"
  db_password_secret_id = "fusion-prime-db-db-password"
  secret_ids            = ["settlement-service-config-test", "relayer-service-config-test", "fusion-prime-db-db-password"]
}


module "pubsub_settlement" {
  source = "../modules/pubsub_settlement"

  project_id            = var.project_id
  topic_name            = "settlement.events.v1"
  subscription_name     = "settlement-events-consumer"
  service_account_email = module.network.service_accounts["settlement-service"]
}

# Risk Engine subscription to settlement events topic
resource "google_pubsub_subscription" "risk_events_consumer" {
  name  = "risk-events-consumer"
  topic = module.pubsub_settlement.topic_name

  ack_deadline_seconds = 60
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
}

# Grant Risk Engine service account subscriber role
resource "google_pubsub_subscription_iam_member" "risk_consumer_role" {
  subscription = google_pubsub_subscription.risk_events_consumer.name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:${module.network.service_accounts["risk-service"]}"
}

# Temporarily disabled Cloud Build triggers until GitHub integration is set up
# module "cloud_build_triggers" {
#   source = "../modules/cloud-build-triggers"
#
#   github_owner = "fusion-prime"  # Update with actual GitHub owner
#   github_repo  = "fusion-prime"  # Update with actual repository name
# }

module "bigquery" {
  source = "../modules/bigquery"

  environment                = "test"
  region                     = "US"
  settlement_service_account = module.network.service_accounts["settlement-service"]
  relayer_service_account    = module.network.service_accounts["relayer-service"]
  analytics_readers          = [] # Add analytics team members here
}

# Cloud Build logs bucket for VPC-SC compliance
module "cloud_build_logs" {
  source = "../modules/cloud-build-logs"

  project_id     = var.project_id
  project_number = var.project_number
  bucket_name    = "fusion-prime-cloud-build-logs"
  location       = "US"

  # GitHub Actions service account for log access
  github_service_account_email = "github@fusion-prime.iam.gserviceaccount.com"

  # Log retention and lifecycle
  log_retention_days = 30
  versioning_enabled = true

  labels = {
    purpose     = "cloud-build-logs"
    environment = "shared"
    managed-by  = "terraform"
    vpc-sc      = "compliant"
  }
}
