# Risk Dashboard Cloud Run Service
# Frontend application for risk monitoring and analytics

module "risk_dashboard" {
  source = "../modules/cloud_run_service"

  project_id  = var.project_id
  region      = var.region
  environment = "dev"

  service_name = "risk-dashboard"

  # Container image (will be updated by Cloud Build)
  container_image = "us-central1-docker.pkg.dev/${var.project_id}/frontend/risk-dashboard:latest"
  container_port  = 80

  # Resource limits (frontend is lightweight)
  cpu_limit            = "1000m"
  memory_limit         = "512Mi"
  cpu_always_allocated = false
  startup_cpu_boost    = true

  # Auto-scaling
  min_instances = 0
  max_instances = 10

  # Timeout
  timeout_seconds = 300

  # VPC connector (full path required for Cloud Run v2)
  vpc_connector_id = "projects/${var.project_id}/locations/${var.region}/connectors/${module.network.vpc_connector_name}"
  vpc_egress       = "private-ranges-only"

  # No Cloud SQL needed for frontend
  cloudsql_instances = []

  # Public access (frontend needs to be accessible)
  allow_unauthenticated = true
  invoker_members       = []

  # Environment variables
  env_vars = {
    VITE_API_BASE_URL           = "https://risk-engine-service-961424092563.us-central1.run.app"
    VITE_WS_URL                 = "wss://risk-engine-service-961424092563.us-central1.run.app"
    VITE_ALERT_NOTIFICATION_URL = "https://alert-notification-service-961424092563.us-central1.run.app"
  }

  # No secrets needed for frontend (public URLs)
  secret_env_vars = {}

  # Health check
  enable_health_check = true
  health_check_path   = "/health"

  labels = {
    component = "frontend"
    app       = "risk-dashboard"
    team      = "frontend"
  }
}

# Output service URL
output "risk_dashboard_url" {
  description = "Risk Dashboard service URL"
  value       = module.risk_dashboard.service_url
}
