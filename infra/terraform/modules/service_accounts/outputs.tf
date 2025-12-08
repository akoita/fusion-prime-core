output "terraform_admin_email" {
  description = "Email of the Terraform admin service account"
  value       = google_service_account.terraform_admin.email
}

output "settlement_service_email" {
  description = "Email of the settlement service account"
  value       = google_service_account.settlement_service.email
}

output "risk_service_email" {
  description = "Email of the risk service account"
  value       = google_service_account.risk_service.email
}

output "compliance_service_email" {
  description = "Email of the compliance service account"
  value       = google_service_account.compliance_service.email
}

output "bridge_service_email" {
  description = "Email of the bridge service account"
  value       = google_service_account.bridge_service.email
}

output "cicd_deployer_email" {
  description = "Email of the CI/CD deployer service account"
  value       = google_service_account.cicd_deployer.email
}

output "all_service_accounts" {
  description = "Map of all service account emails"
  value = {
    terraform_admin     = google_service_account.terraform_admin.email
    settlement_service  = google_service_account.settlement_service.email
    risk_service        = google_service_account.risk_service.email
    compliance_service  = google_service_account.compliance_service.email
    bridge_service      = google_service_account.bridge_service.email
    cicd_deployer       = google_service_account.cicd_deployer.email
  }
}

