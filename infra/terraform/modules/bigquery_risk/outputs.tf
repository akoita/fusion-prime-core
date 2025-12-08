# BigQuery Risk Analytics Module Outputs

output "dataset_id" {
  description = "BigQuery dataset ID"
  value       = google_bigquery_dataset.risk_analytics.dataset_id
}

output "dataset_self_link" {
  description = "Self link of the dataset"
  value       = google_bigquery_dataset.risk_analytics.self_link
}

output "dataset_location" {
  description = "Location of the dataset"
  value       = google_bigquery_dataset.risk_analytics.location
}

output "portfolio_exposures_table_id" {
  description = "Portfolio exposures table ID"
  value       = google_bigquery_table.portfolio_exposures.table_id
}

output "asset_exposures_table_id" {
  description = "Asset exposures table ID"
  value       = google_bigquery_table.asset_exposures.table_id
}

output "margin_events_table_id" {
  description = "Margin events table ID"
  value       = google_bigquery_table.margin_events.table_id
}

output "settlement_transactions_table_id" {
  description = "Settlement transactions table ID"
  value       = google_bigquery_table.settlement_transactions.table_id
}

output "risk_metrics_daily_table_id" {
  description = "Daily risk metrics table ID"
  value       = google_bigquery_table.risk_metrics_daily.table_id
}

output "current_portfolio_view_id" {
  description = "Current portfolio view ID"
  value       = google_bigquery_table.current_portfolio_view.table_id
}

# Fully qualified table names for queries
output "portfolio_exposures_table_fqn" {
  description = "Fully qualified name for portfolio exposures table"
  value       = "${var.project_id}.${google_bigquery_dataset.risk_analytics.dataset_id}.${google_bigquery_table.portfolio_exposures.table_id}"
}

output "asset_exposures_table_fqn" {
  description = "Fully qualified name for asset exposures table"
  value       = "${var.project_id}.${google_bigquery_dataset.risk_analytics.dataset_id}.${google_bigquery_table.asset_exposures.table_id}"
}

output "margin_events_table_fqn" {
  description = "Fully qualified name for margin events table"
  value       = "${var.project_id}.${google_bigquery_dataset.risk_analytics.dataset_id}.${google_bigquery_table.margin_events.table_id}"
}

output "settlement_transactions_table_fqn" {
  description = "Fully qualified name for settlement transactions table"
  value       = "${var.project_id}.${google_bigquery_dataset.risk_analytics.dataset_id}.${google_bigquery_table.settlement_transactions.table_id}"
}

output "current_portfolio_view_fqn" {
  description = "Fully qualified name for current portfolio view"
  value       = "${var.project_id}.${google_bigquery_dataset.risk_analytics.dataset_id}.${google_bigquery_table.current_portfolio_view.table_id}"
}

# Query examples
output "query_current_portfolio_example" {
  description = "Example query for current portfolio"
  value       = "SELECT * FROM `${var.project_id}.${google_bigquery_dataset.risk_analytics.dataset_id}.${google_bigquery_table.current_portfolio_view.table_id}` WHERE account_id = 'YOUR_ACCOUNT_ID'"
}

output "query_daily_metrics_example" {
  description = "Example query for daily risk metrics"
  value       = "SELECT * FROM `${var.project_id}.${google_bigquery_dataset.risk_analytics.dataset_id}.${google_bigquery_table.risk_metrics_daily.table_id}` WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) AND account_id = 'YOUR_ACCOUNT_ID' ORDER BY date DESC"
}

