# Cloud SQL Module Outputs

output "instance_name" {
  description = "Name of the Cloud SQL instance"
  value       = google_sql_database_instance.primary.name
}

output "instance_connection_name" {
  description = "Connection name for Cloud SQL Proxy (PROJECT:REGION:INSTANCE)"
  value       = google_sql_database_instance.primary.connection_name
}

output "instance_self_link" {
  description = "Self link of the Cloud SQL instance"
  value       = google_sql_database_instance.primary.self_link
}

output "private_ip_address" {
  description = "Private IP address of the instance"
  value       = google_sql_database_instance.primary.private_ip_address
}

output "public_ip_address" {
  description = "Public IP address of the instance (if enabled)"
  value       = var.enable_public_ip ? google_sql_database_instance.primary.public_ip_address : null
}

output "database_name" {
  description = "Name of the primary database"
  value       = google_sql_database.primary_db.name
}

output "app_user_name" {
  description = "Username for the application database user"
  value       = google_sql_user.app_user.name
}

output "app_user_password" {
  description = "Password for the application user (sensitive)"
  value       = var.app_user_password != "" ? var.app_user_password : random_password.app_user_password[0].result
  sensitive   = true
}

output "connection_string" {
  description = "PostgreSQL connection string (sensitive)"
  value = format(
    "postgresql://%s:%s@%s:%s/%s",
    google_sql_user.app_user.name,
    var.app_user_password != "" ? var.app_user_password : random_password.app_user_password[0].result,
    google_sql_database_instance.primary.private_ip_address,
    5432,
    google_sql_database.primary_db.name
  )
  sensitive = true
}

output "connection_string_public" {
  description = "PostgreSQL connection string with public IP (if enabled, sensitive)"
  value = var.enable_public_ip ? format(
    "postgresql://%s:%s@%s:%s/%s",
    google_sql_user.app_user.name,
    var.app_user_password != "" ? var.app_user_password : random_password.app_user_password[0].result,
    google_sql_database_instance.primary.public_ip_address,
    5432,
    google_sql_database.primary_db.name
  ) : null
  sensitive = true
}

output "read_replica_connection_name" {
  description = "Connection name for read replica (if enabled)"
  value       = var.enable_read_replica ? google_sql_database_instance.read_replica[0].connection_name : null
}

output "read_replica_private_ip" {
  description = "Private IP address of read replica (if enabled)"
  value       = var.enable_read_replica ? google_sql_database_instance.read_replica[0].private_ip_address : null
}

output "proxy_service_account_email" {
  description = "Email of the Cloud SQL Proxy service account"
  value       = var.create_proxy_service_account ? google_service_account.cloudsql_proxy[0].email : null
}

output "proxy_service_account_key" {
  description = "Key name of the Cloud SQL Proxy service account"
  value       = var.create_proxy_service_account ? google_service_account.cloudsql_proxy[0].name : null
}

output "password_secret_id" {
  description = "Secret Manager secret ID for database password"
  value       = var.store_password_in_secret_manager ? google_secret_manager_secret.db_password[0].secret_id : null
}

output "connection_string_secret_id" {
  description = "Secret Manager secret ID for connection string"
  value       = var.store_password_in_secret_manager ? google_secret_manager_secret.db_connection_string[0].secret_id : null
}

# Useful for monitoring and alerting
output "instance_id" {
  description = "Instance ID for monitoring"
  value       = google_sql_database_instance.primary.id
}

output "instance_region" {
  description = "Region where the instance is deployed"
  value       = google_sql_database_instance.primary.region
}

output "instance_tier" {
  description = "Machine tier of the instance"
  value       = google_sql_database_instance.primary.settings[0].tier
}

output "backup_enabled" {
  description = "Whether backups are enabled"
  value       = google_sql_database_instance.primary.settings[0].backup_configuration[0].enabled
}

output "high_availability" {
  description = "Whether high availability is enabled"
  value       = var.high_availability
}

