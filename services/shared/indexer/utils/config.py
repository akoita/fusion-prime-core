"""
Configuration utilities for indexers

Provides standard environment variable loading and validation.
"""

import logging
import os
import sys
from typing import Optional

logger = logging.getLogger(__name__)


class IndexerConfig:
    """Base configuration for indexers."""

    def __init__(self, service_name: str):
        """
        Initialize configuration.

        Args:
            service_name: Name of the service
        """
        self.service_name = service_name

        # Pub/Sub configuration
        self.pubsub_project_id = os.getenv("PUBSUB_PROJECT_ID") or os.getenv(
            "GCP_PROJECT", "fusion-prime"
        )
        self.pubsub_subscription_id = os.getenv("PUBSUB_SUBSCRIPTION_ID")
        if not self.pubsub_subscription_id:
            logger.warning(f"PUBSUB_SUBSCRIPTION_ID not set, using default: {service_name}-sub")
            self.pubsub_subscription_id = f"{service_name}-sub"

        # Database configuration
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            # Fallback to individual components
            db_user = os.getenv("DB_USER", "postgres")
            db_password = os.getenv("DB_PASSWORD", "postgres")
            db_host = os.getenv("DB_HOST", "localhost")
            db_port = os.getenv("DB_PORT", "5432")
            db_name = os.getenv("DB_NAME", service_name.replace("-", "_"))
            self.database_url = (
                f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            )

        # Server configuration
        self.port = int(os.getenv("PORT", "8080"))

        # Logging
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

    def validate(self):
        """Validate configuration and exit if invalid."""
        errors = []

        if not self.pubsub_project_id:
            errors.append("PUBSUB_PROJECT_ID or GCP_PROJECT is required")

        if not self.pubsub_subscription_id:
            errors.append("PUBSUB_SUBSCRIPTION_ID is required")

        if not self.database_url:
            errors.append("DATABASE_URL or DB_* environment variables are required")

        if errors:
            logger.error(f"❌ Configuration validation failed for {self.service_name}:")
            for error in errors:
                logger.error(f"  - {error}")
            sys.exit(1)

        logger.info(f"✅ {self.service_name} configuration validated")

    def log_config(self):
        """Log configuration (excluding sensitive data)."""
        logger.info(f"Configuration for {self.service_name}:")
        logger.info(f"  Pub/Sub Project: {self.pubsub_project_id}")
        logger.info(f"  Pub/Sub Subscription: {self.pubsub_subscription_id}")
        logger.info(
            f"  Database: {self.database_url.split('@')[1] if '@' in self.database_url else 'configured'}"
        )
        logger.info(f"  Port: {self.port}")
        logger.info(f"  Log Level: {self.log_level}")
