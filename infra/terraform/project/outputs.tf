# Terraform Outputs for Fusion Prime Project

# Cloud SQL Database Outputs
output "fiat_gateway_db_connection_name" {
  description = "Cloud SQL connection name for Fiat Gateway database"
  value       = module.cloudsql_fiat_gateway.instance_connection_name
}

output "fiat_gateway_db_connection_string_secret" {
  description = "Secret Manager secret ID for Fiat Gateway connection string"
  value       = module.cloudsql_fiat_gateway.connection_string_secret_id
}

output "cross_chain_db_connection_name" {
  description = "Cloud SQL connection name for Cross-Chain Integration database"
  value       = module.cloudsql_cross_chain.instance_connection_name
}

output "cross_chain_db_connection_string_secret" {
  description = "Secret Manager secret ID for Cross-Chain Integration connection string"
  value       = module.cloudsql_cross_chain.connection_string_secret_id
}

# Existing database outputs (if not already defined)
output "settlement_db_connection_name" {
  description = "Cloud SQL connection name for Settlement database"
  value       = module.cloudsql_settlement.instance_connection_name
}

output "risk_engine_db_connection_name" {
  description = "Cloud SQL connection name for Risk Engine database"
  value       = module.cloudsql_risk_engine.instance_connection_name
}

output "compliance_db_connection_name" {
  description = "Cloud SQL connection name for Compliance database"
  value       = module.cloudsql_compliance.instance_connection_name
}
