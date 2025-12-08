# BigQuery module for Fusion Prime analytics
# Provides datasets and tables for settlement analytics

# Settlement events dataset
resource "google_bigquery_dataset" "settlement_events" {
  dataset_id    = "settlement_events"
  friendly_name = "Settlement Events"
  description   = "Dataset for settlement transaction events and analytics"
  location      = var.region

  # Default table expiration (90 days)
  default_table_expiration_ms = 90 * 24 * 60 * 60 * 1000

  # Labels
  labels = {
    environment = var.environment
    service     = "settlement"
    purpose     = "analytics"
  }
}

# Settlement commands table
resource "google_bigquery_table" "settlement_commands" {
  dataset_id = google_bigquery_dataset.settlement_events.dataset_id
  table_id   = "settlement_commands"

  description = "Settlement command events from the settlement service"
  schema = jsonencode([
    {
      name = "command_id"
      type = "STRING"
      mode = "REQUIRED"
      description = "Unique command identifier"
    },
    {
      name = "timestamp"
      type = "TIMESTAMP"
      mode = "REQUIRED"
      description = "Event timestamp"
    },
    {
      name = "event_type"
      type = "STRING"
      mode = "REQUIRED"
      description = "Type of settlement event"
    },
    {
      name = "payer_address"
      type = "STRING"
      mode = "NULLABLE"
      description = "Payer wallet address"
    },
    {
      name = "payee_address"
      type = "STRING"
      mode = "NULLABLE"
      description = "Payee wallet address"
    },
    {
      name = "amount"
      type = "NUMERIC"
      mode = "NULLABLE"
      description = "Settlement amount in wei"
    },
    {
      name = "token_address"
      type = "STRING"
      mode = "NULLABLE"
      description = "Token contract address"
    },
    {
      name = "chain_id"
      type = "STRING"
      mode = "REQUIRED"
      description = "Blockchain chain ID"
    },
    {
      name = "status"
      type = "STRING"
      mode = "REQUIRED"
      description = "Command status"
    },
    {
      name = "metadata"
      type = "JSON"
      mode = "NULLABLE"
      description = "Additional event metadata"
    }
  ])

  # Partitioning by timestamp
  time_partitioning {
    type  = "DAY"
    field = "timestamp"
  }

  # Clustering for better query performance
  clustering = ["event_type", "status", "chain_id"]

  # Labels
  labels = {
    environment = var.environment
    service     = "settlement"
    table_type  = "events"
  }
}

# Settlement analytics dataset
resource "google_bigquery_dataset" "settlement_analytics" {
  dataset_id    = "settlement_analytics"
  friendly_name = "Settlement Analytics"
  description   = "Aggregated analytics and reporting for settlement data"
  location      = var.region

  # Default table expiration (365 days)
  default_table_expiration_ms = 365 * 24 * 60 * 60 * 1000

  # Labels
  labels = {
    environment = var.environment
    service     = "analytics"
    purpose     = "reporting"
  }
}

# Daily settlement summary table
resource "google_bigquery_table" "daily_settlement_summary" {
  dataset_id = google_bigquery_dataset.settlement_analytics.dataset_id
  table_id   = "daily_settlement_summary"

  description = "Daily aggregated settlement statistics"
  schema = jsonencode([
    {
      name = "date"
      type = "DATE"
      mode = "REQUIRED"
      description = "Summary date"
    },
    {
      name = "chain_id"
      type = "STRING"
      mode = "REQUIRED"
      description = "Blockchain chain ID"
    },
    {
      name = "total_commands"
      type = "INTEGER"
      mode = "REQUIRED"
      description = "Total settlement commands"
    },
    {
      name = "successful_commands"
      type = "INTEGER"
      mode = "REQUIRED"
      description = "Successfully processed commands"
    },
    {
      name = "failed_commands"
      type = "INTEGER"
      mode = "REQUIRED"
      description = "Failed commands"
    },
    {
      name = "total_volume_wei"
      type = "NUMERIC"
      mode = "REQUIRED"
      description = "Total settlement volume in wei"
    },
    {
      name = "unique_payers"
      type = "INTEGER"
      mode = "REQUIRED"
      description = "Number of unique payers"
    },
    {
      name = "unique_payees"
      type = "INTEGER"
      mode = "REQUIRED"
      description = "Number of unique payees"
    },
    {
      name = "avg_processing_time_ms"
      type = "NUMERIC"
      mode = "NULLABLE"
      description = "Average processing time in milliseconds"
    }
  ])

  # Partitioning by date
  time_partitioning {
    type  = "DAY"
    field = "date"
  }

  # Clustering for better query performance
  clustering = ["chain_id"]

  # Labels
  labels = {
    environment = var.environment
    service     = "analytics"
    table_type  = "summary"
  }
}

# IAM bindings for service accounts
resource "google_bigquery_dataset_iam_member" "settlement_service_access" {
  dataset_id = google_bigquery_dataset.settlement_events.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${var.settlement_service_account}"
}

resource "google_bigquery_dataset_iam_member" "relayer_service_access" {
  dataset_id = google_bigquery_dataset.settlement_events.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${var.relayer_service_account}"
}

resource "google_bigquery_dataset_iam_member" "analytics_readers" {
  for_each   = toset(var.analytics_readers)
  dataset_id = google_bigquery_dataset.settlement_analytics.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = each.value
}
