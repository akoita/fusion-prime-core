"""
Apache Beam Dataflow Pipeline for Settlement Events
Processes settlement events from Pub/Sub and writes to BigQuery for analytics
"""

import argparse
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

import apache_beam as beam
from apache_beam.io import ReadFromPubSub, WriteToBigQuery
from apache_beam.io.gcp.bigquery import BigQueryDisposition
from apache_beam.options.pipeline_options import (
    GoogleCloudOptions,
    PipelineOptions,
    StandardOptions,
    WorkerOptions,
)
from apache_beam.transforms.window import FixedWindows, TimestampedValue

# BigQuery schema for settlement transactions
SETTLEMENT_TRANSACTION_SCHEMA = {
    "fields": [
        {"name": "timestamp", "type": "TIMESTAMP", "mode": "REQUIRED"},
        {"name": "command_id", "type": "STRING", "mode": "REQUIRED"},
        {"name": "chain_id", "type": "STRING", "mode": "REQUIRED"},
        {"name": "payer", "type": "STRING", "mode": "REQUIRED"},
        {"name": "payee", "type": "STRING", "mode": "REQUIRED"},
        {"name": "amount", "type": "NUMERIC", "mode": "REQUIRED"},
        {"name": "amount_usd", "type": "NUMERIC", "mode": "NULLABLE"},
        {"name": "asset_address", "type": "STRING", "mode": "REQUIRED"},
        {"name": "asset_symbol", "type": "STRING", "mode": "NULLABLE"},
        {"name": "status", "type": "STRING", "mode": "REQUIRED"},
        {"name": "transaction_hash", "type": "STRING", "mode": "NULLABLE"},
        {"name": "block_number", "type": "INTEGER", "mode": "NULLABLE"},
        {"name": "gas_used", "type": "INTEGER", "mode": "NULLABLE"},
        {"name": "gas_price", "type": "NUMERIC", "mode": "NULLABLE"},
        {"name": "fee_usd", "type": "NUMERIC", "mode": "NULLABLE"},
        {"name": "settlement_type", "type": "STRING", "mode": "REQUIRED"},
        {"name": "account_id", "type": "STRING", "mode": "NULLABLE"},
        {"name": "reference_id", "type": "STRING", "mode": "NULLABLE"},
        {"name": "created_at", "type": "TIMESTAMP", "mode": "REQUIRED"},
        {"name": "confirmed_at", "type": "TIMESTAMP", "mode": "NULLABLE"},
        {"name": "metadata", "type": "JSON", "mode": "NULLABLE"},
    ]
}


class ParsePubSubMessage(beam.DoFn):
    """Parse Pub/Sub message from JSON"""

    def process(self, element):
        try:
            # Parse JSON payload
            data = json.loads(element.decode("utf-8"))

            # Extract timestamp for windowing
            timestamp = datetime.fromisoformat(
                data.get("timestamp", datetime.now(timezone.utc).isoformat())
            )

            # Yield with event timestamp
            yield TimestampedValue(data, timestamp.timestamp())

        except Exception as e:
            logging.error(f"Error parsing message: {e}, element: {element}")
            # Log to dead letter queue or metrics
            yield beam.pvalue.TaggedOutput(
                "dead_letter",
                {
                    "error": str(e),
                    "raw_message": element.decode("utf-8", errors="replace"),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )


class EnrichSettlementEvent(beam.DoFn):
    """Enrich settlement event with additional data"""

    def process(self, element):
        try:
            enriched = element.copy()

            # Parse amounts if needed
            if "amount" in enriched and isinstance(enriched["amount"], str):
                enriched["amount"] = float(enriched["amount"])

            # Determine settlement type from event data
            if "event_name" in enriched:
                event_map = {
                    "EscrowReleased": "escrow_release",
                    "EscrowRefunded": "escrow_refund",
                    "MarginCall": "margin_call",
                    "Liquidation": "liquidation",
                }
                enriched["settlement_type"] = event_map.get(enriched.get("event_name"), "unknown")
            else:
                enriched["settlement_type"] = enriched.get("settlement_type", "unknown")

            # Add processing timestamp
            enriched["processed_at"] = datetime.now(timezone.utc).isoformat()

            # Extract args if present (from smart contract events)
            if "args" in enriched and isinstance(enriched["args"], dict):
                enriched["payer"] = enriched["args"].get("payer", enriched.get("payer"))
                enriched["payee"] = enriched["args"].get("payee", enriched.get("payee"))
                enriched["amount"] = enriched["args"].get("amount", enriched.get("amount"))

            yield enriched

        except Exception as e:
            logging.error(f"Error enriching event: {e}, element: {element}")
            yield beam.pvalue.TaggedOutput(
                "dead_letter",
                {
                    "error": str(e),
                    "event": element,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )


class TransformToBigQueryRow(beam.DoFn):
    """Transform enriched event to BigQuery row format"""

    def process(self, element):
        try:
            row = {
                "timestamp": element.get("timestamp", datetime.now(timezone.utc).isoformat()),
                "command_id": element.get("command_id", element.get("transaction_hash", "unknown")),
                "chain_id": str(element.get("chain_id", "0")),
                "payer": element.get("payer", "0x0000000000000000000000000000000000000000"),
                "payee": element.get("payee", "0x0000000000000000000000000000000000000000"),
                "amount": str(element.get("amount", "0")),
                "amount_usd": (
                    str(element.get("amount_usd")) if element.get("amount_usd") else None
                ),
                "asset_address": element.get(
                    "asset_address", element.get("contract_address", "0x0")
                ),
                "asset_symbol": element.get("asset_symbol"),
                "status": element.get("status", "confirmed"),
                "transaction_hash": element.get("transaction_hash"),
                "block_number": element.get("block_number"),
                "gas_used": element.get("gas_used"),
                "gas_price": (str(element.get("gas_price")) if element.get("gas_price") else None),
                "fee_usd": (str(element.get("fee_usd")) if element.get("fee_usd") else None),
                "settlement_type": element.get("settlement_type", "unknown"),
                "account_id": element.get("account_id"),
                "reference_id": element.get("reference_id"),
                "created_at": element.get("created_at", element.get("timestamp")),
                "confirmed_at": element.get("confirmed_at"),
                "metadata": (
                    json.dumps(element.get("metadata", {})) if element.get("metadata") else None
                ),
            }

            yield row

        except Exception as e:
            logging.error(f"Error transforming to BigQuery row: {e}, element: {element}")
            yield beam.pvalue.TaggedOutput(
                "dead_letter",
                {
                    "error": str(e),
                    "event": element,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )


class ComputeMetrics(beam.DoFn):
    """Compute metrics for monitoring"""

    def process(self, element):
        # Yield the element unchanged
        yield element

        # Yield side output for metrics
        metrics = {
            "chain_id": element.get("chain_id"),
            "settlement_type": element.get("settlement_type"),
            "status": element.get("status"),
            "amount_usd": (float(element.get("amount_usd", 0)) if element.get("amount_usd") else 0),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        yield beam.pvalue.TaggedOutput("metrics", metrics)


def run_pipeline(argv=None):
    """Main pipeline execution"""

    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, help="GCP project ID")
    parser.add_argument("--region", default="us-central1", help="GCP region")
    parser.add_argument(
        "--input_subscription",
        required=True,
        help="Pub/Sub subscription to read from (projects/PROJECT/subscriptions/SUB)",
    )
    parser.add_argument(
        "--output_table",
        required=True,
        help="BigQuery output table (PROJECT:DATASET.TABLE)",
    )
    parser.add_argument(
        "--dead_letter_table",
        default=None,
        help="BigQuery dead letter table for failed records",
    )
    parser.add_argument("--window_size", type=int, default=60, help="Fixed window size in seconds")
    parser.add_argument(
        "--runner",
        default="DirectRunner",
        help="Pipeline runner (DirectRunner or DataflowRunner)",
    )
    parser.add_argument("--temp_location", default=None, help="GCS temp location for Dataflow")
    parser.add_argument(
        "--staging_location", default=None, help="GCS staging location for Dataflow"
    )

    known_args, pipeline_args = parser.parse_known_args(argv)

    # Pipeline options
    pipeline_options = PipelineOptions(pipeline_args)
    pipeline_options.view_as(StandardOptions).runner = known_args.runner

    # Google Cloud options
    google_cloud_options = pipeline_options.view_as(GoogleCloudOptions)
    google_cloud_options.project = known_args.project
    google_cloud_options.region = known_args.region
    if known_args.temp_location:
        google_cloud_options.temp_location = known_args.temp_location
    if known_args.staging_location:
        google_cloud_options.staging_location = known_args.staging_location

    # Worker options
    worker_options = pipeline_options.view_as(WorkerOptions)
    worker_options.autoscaling_algorithm = "THROUGHPUT_BASED"
    worker_options.max_num_workers = 10

    # Build and run pipeline
    with beam.Pipeline(options=pipeline_options) as p:
        # Read from Pub/Sub
        raw_messages = p | "Read from Pub/Sub" >> ReadFromPubSub(
            subscription=known_args.input_subscription
        )

        # Parse messages
        parsed_results = raw_messages | "Parse Messages" >> beam.ParDo(
            ParsePubSubMessage()
        ).with_outputs("dead_letter", main="parsed")

        # Enrich events
        enriched_results = parsed_results.parsed | "Enrich Events" >> beam.ParDo(
            EnrichSettlementEvent()
        ).with_outputs("dead_letter", main="enriched")

        # Transform to BigQuery rows
        bigquery_rows = enriched_results.enriched | "Transform to BigQuery" >> beam.ParDo(
            TransformToBigQueryRow()
        ).with_outputs("dead_letter", main="rows")

        # Compute metrics
        metrics_results = bigquery_rows.rows | "Compute Metrics" >> beam.ParDo(
            ComputeMetrics()
        ).with_outputs("metrics", main="final_rows")

        # Write to BigQuery
        _ = metrics_results.final_rows | "Write to BigQuery" >> WriteToBigQuery(
            known_args.output_table,
            schema=SETTLEMENT_TRANSACTION_SCHEMA,
            write_disposition=BigQueryDisposition.WRITE_APPEND,
            create_disposition=BigQueryDisposition.CREATE_IF_NEEDED,
        )

        # Handle dead letter queue if configured
        if known_args.dead_letter_table:
            dead_letter_schema = {
                "fields": [
                    {"name": "error", "type": "STRING", "mode": "REQUIRED"},
                    {"name": "timestamp", "type": "TIMESTAMP", "mode": "REQUIRED"},
                    {"name": "raw_data", "type": "JSON", "mode": "NULLABLE"},
                ]
            }

            # Combine all dead letter outputs
            all_dead_letters = (
                parsed_results.dead_letter,
                enriched_results.dead_letter,
                bigquery_rows.dead_letter,
            ) | "Flatten Dead Letters" >> beam.Flatten()

            _ = all_dead_letters | "Write Dead Letters" >> WriteToBigQuery(
                known_args.dead_letter_table,
                schema=dead_letter_schema,
                write_disposition=BigQueryDisposition.WRITE_APPEND,
                create_disposition=BigQueryDisposition.CREATE_IF_NEEDED,
            )


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    run_pipeline()
