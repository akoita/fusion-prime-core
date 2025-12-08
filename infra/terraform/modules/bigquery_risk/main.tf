# BigQuery Risk Analytics Module for Fusion Prime
# Provisions datasets and tables for risk analytics, portfolio tracking, and compliance reporting

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# BigQuery dataset for risk analytics
resource "google_bigquery_dataset" "risk_analytics" {
  dataset_id    = var.dataset_id
  friendly_name = var.dataset_friendly_name
  description   = var.dataset_description
  location      = var.location
  project       = var.project_id

  # Access control
  default_table_expiration_ms = var.default_table_expiration_ms

  # Labels for organization
  labels = merge(
    {
      environment = var.environment
      managed_by  = "terraform"
      service     = "fusion-prime"
      purpose     = "risk-analytics"
    },
    var.labels
  )

  # Default encryption (can be overridden with CMEK)
  dynamic "default_encryption_configuration" {
    for_each = var.kms_key_name != "" ? [1] : []
    content {
      kms_key_name = var.kms_key_name
    }
  }

  # Access configuration
  dynamic "access" {
    for_each = var.dataset_access
    content {
      role          = access.value.role
      user_by_email = try(access.value.user_by_email, null)
      group_by_email = try(access.value.group_by_email, null)
      special_group = try(access.value.special_group, null)
    }
  }

  # Enable delete protection in production
  deletion_protection = var.enable_deletion_protection
}

# Portfolio exposures table
resource "google_bigquery_table" "portfolio_exposures" {
  dataset_id = google_bigquery_dataset.risk_analytics.dataset_id
  table_id   = "portfolio_exposures"
  project    = var.project_id

  description = "Real-time portfolio exposures by account, asset, and chain"

  # Time partitioning for efficient queries
  time_partitioning {
    type  = "DAY"
    field = "timestamp"
    expiration_ms = var.partition_expiration_days * 24 * 60 * 60 * 1000
  }

  # Clustering for query optimization
  clustering = ["account_id", "chain_id", "asset_address"]

  # Schema
  schema = file("${path.module}/schemas/portfolio_exposures.json")

  labels = {
    table_type  = "portfolio"
    data_source = "dataflow"
  }

  deletion_protection = var.enable_deletion_protection
}

# Asset exposures table
resource "google_bigquery_table" "asset_exposures" {
  dataset_id = google_bigquery_dataset.risk_analytics.dataset_id
  table_id   = "asset_exposures"
  project    = var.project_id

  description = "Aggregated exposure by asset across all accounts"

  time_partitioning {
    type  = "DAY"
    field = "timestamp"
    expiration_ms = var.partition_expiration_days * 24 * 60 * 60 * 1000
  }

  clustering = ["asset_address", "chain_id"]

  schema = file("${path.module}/schemas/asset_exposures.json")

  labels = {
    table_type  = "asset"
    data_source = "dataflow"
  }

  deletion_protection = var.enable_deletion_protection
}

# Margin events table
resource "google_bigquery_table" "margin_events" {
  dataset_id = google_bigquery_dataset.risk_analytics.dataset_id
  table_id   = "margin_events"
  project    = var.project_id

  description = "Margin call and liquidation events"

  time_partitioning {
    type  = "DAY"
    field = "timestamp"
    expiration_ms = var.partition_expiration_days * 24 * 60 * 60 * 1000
  }

  clustering = ["account_id", "event_type"]

  schema = file("${path.module}/schemas/margin_events.json")

  labels = {
    table_type  = "events"
    data_source = "pubsub"
  }

  deletion_protection = var.enable_deletion_protection
}

# Settlement transactions table
resource "google_bigquery_table" "settlement_transactions" {
  dataset_id = google_bigquery_dataset.risk_analytics.dataset_id
  table_id   = "settlement_transactions"
  project    = var.project_id

  description = "All settlement transactions for audit and analysis"

  time_partitioning {
    type  = "DAY"
    field = "timestamp"
    expiration_ms = var.partition_expiration_days * 24 * 60 * 60 * 1000
  }

  clustering = ["command_id", "chain_id", "status"]

  schema = file("${path.module}/schemas/settlement_transactions.json")

  labels = {
    table_type  = "transactions"
    data_source = "pubsub"
  }

  deletion_protection = var.enable_deletion_protection
}

# Risk metrics aggregated table (materialized view source)
resource "google_bigquery_table" "risk_metrics_daily" {
  dataset_id = google_bigquery_dataset.risk_analytics.dataset_id
  table_id   = "risk_metrics_daily"
  project    = var.project_id

  description = "Daily aggregated risk metrics"

  time_partitioning {
    type  = "DAY"
    field = "date"
    expiration_ms = 365 * 24 * 60 * 60 * 1000 # 1 year retention
  }

  schema = file("${path.module}/schemas/risk_metrics_daily.json")

  labels = {
    table_type  = "aggregated"
    data_source = "scheduled-query"
  }

  deletion_protection = var.enable_deletion_protection
}

# Scheduled query for daily risk metrics aggregation
resource "google_bigquery_data_transfer_config" "daily_risk_metrics" {
  count = var.enable_scheduled_queries ? 1 : 0

  display_name           = "Daily Risk Metrics Aggregation"
  location               = var.location
  data_source_id         = "scheduled_query"
  schedule               = "every day 01:00" # Run at 1 AM UTC
  destination_dataset_id = google_bigquery_dataset.risk_analytics.dataset_id
  project                = var.project_id

  params = {
    destination_table_name_template = "risk_metrics_daily"
    write_disposition               = "WRITE_APPEND"
    query                           = <<-SQL
      SELECT
        CURRENT_DATE() AS date,
        account_id,
        SUM(exposure_usd) AS total_exposure_usd,
        SUM(collateral_usd) AS total_collateral_usd,
        SAFE_DIVIDE(SUM(collateral_usd), SUM(exposure_usd)) AS collateral_ratio,
        COUNT(DISTINCT asset_address) AS unique_assets,
        COUNT(DISTINCT chain_id) AS unique_chains,
        MAX(risk_score) AS max_risk_score,
        AVG(risk_score) AS avg_risk_score
      FROM
        `${var.project_id}.${google_bigquery_dataset.risk_analytics.dataset_id}.portfolio_exposures`
      WHERE
        DATE(timestamp) = CURRENT_DATE()
      GROUP BY
        account_id
    SQL
  }
}

# View for current portfolio state (latest snapshot)
resource "google_bigquery_table" "current_portfolio_view" {
  dataset_id = google_bigquery_dataset.risk_analytics.dataset_id
  table_id   = "current_portfolio"
  project    = var.project_id

  description = "Current portfolio state (latest snapshot per account)"

  view {
    query = <<-SQL
      WITH latest_snapshots AS (
        SELECT
          account_id,
          chain_id,
          asset_address,
          MAX(timestamp) AS latest_timestamp
        FROM
          `${var.project_id}.${google_bigquery_dataset.risk_analytics.dataset_id}.portfolio_exposures`
        WHERE
          DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
        GROUP BY
          account_id, chain_id, asset_address
      )
      SELECT
        p.*
      FROM
        `${var.project_id}.${google_bigquery_dataset.risk_analytics.dataset_id}.portfolio_exposures` p
      INNER JOIN
        latest_snapshots l
      ON
        p.account_id = l.account_id
        AND p.chain_id = l.chain_id
        AND p.asset_address = l.asset_address
        AND p.timestamp = l.latest_timestamp
    SQL
    use_legacy_sql = false
  }

  labels = {
    table_type = "view"
    real_time  = "true"
  }
}

# IAM binding for Dataflow to write to BigQuery
resource "google_bigquery_dataset_iam_member" "dataflow_writer" {
  count = var.dataflow_service_account_email != "" ? 1 : 0

  dataset_id = google_bigquery_dataset.risk_analytics.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${var.dataflow_service_account_email}"
  project    = var.project_id
}

# IAM binding for Pub/Sub to write to BigQuery (for streaming inserts)
resource "google_bigquery_dataset_iam_member" "pubsub_writer" {
  count = var.pubsub_service_account_email != "" ? 1 : 0

  dataset_id = google_bigquery_dataset.risk_analytics.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${var.pubsub_service_account_email}"
  project    = var.project_id
}

# IAM binding for frontend/API read access
resource "google_bigquery_dataset_iam_member" "read_access" {
  for_each = toset(var.reader_members)

  dataset_id = google_bigquery_dataset.risk_analytics.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = each.value
  project    = var.project_id
}
