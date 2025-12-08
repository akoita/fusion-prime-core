"""
Dependency injection for Risk Engine Service.
"""

import logging
import os
from typing import AsyncGenerator, Optional

from app.core.analytics_engine import AnalyticsEngine
from app.core.risk_calculator import RiskCalculator
from app.infrastructure.db.session import create_engine, create_session_factory
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Global instances
_risk_calculator: Optional[RiskCalculator] = None
_analytics_engine: Optional[AnalyticsEngine] = None
_engine = None
_session_factory = None

# Initialize database connection
DATABASE_URL_ENV = "RISK_DATABASE_URL"
FALLBACK_DATABASE_URL_ENV = "DATABASE_URL"
DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///./risk.db"

# Get database URL with fallback
database_url = os.environ.get(DATABASE_URL_ENV) or os.environ.get(
    FALLBACK_DATABASE_URL_ENV, DEFAULT_DATABASE_URL
)
logger.info(
    f"Using database URL: {database_url.split('@')[0]}@***"
    if "@" in database_url
    else f"Using database URL: {database_url}"
)

try:
    _engine = create_engine(database_url)
    _session_factory = create_session_factory(_engine)
    logger.info("Database engine and session factory created successfully")
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    # Don't raise - let the service start and handle errors gracefully


def get_risk_calculator() -> RiskCalculator:
    """Get or create risk calculator instance."""
    global _risk_calculator

    if _risk_calculator is None:
        # Get configuration from environment
        database_url = os.getenv("DATABASE_URL", "")
        cache_url = os.getenv("CACHE_URL", "memory://")  # Use in-memory cache as fallback
        market_data_url = os.getenv("MARKET_DATA_URL", "https://api.marketdata.com")
        price_oracle_url = os.getenv("PRICE_ORACLE_URL", "")
        gcp_project = os.getenv("GCP_PROJECT", "")

        # Determine if we should use production or mock calculator
        use_production = database_url and "postgresql" in database_url.lower()

        if use_production:
            logger.info(f"Initializing Risk Calculator with database")
            if price_oracle_url:
                logger.info(f"Price Oracle URL configured: {price_oracle_url}")
            else:
                logger.warning(
                    "Price Oracle URL not configured - margin health features will be disabled"
                )

            try:
                from app.core.risk_calculator import RiskCalculator

                _risk_calculator = RiskCalculator(
                    database_url=database_url,
                    price_oracle_url=price_oracle_url if price_oracle_url else None,
                    gcp_project=gcp_project if gcp_project else None,
                )
                # Note: initialize() will be called in lifespan
                logger.info("Risk Calculator created")
            except Exception as e:
                logger.warning(f"Failed to initialize Risk Calculator: {e}")
                # Fall back to mock calculator
                from app.core.mock_risk_calculator import MockRiskCalculator

                _risk_calculator = MockRiskCalculator()
        else:
            logger.info(f"Using Mock Risk Calculator (no database configured)")
            from app.core.mock_risk_calculator import MockRiskCalculator

            _risk_calculator = MockRiskCalculator()

    return _risk_calculator


def get_analytics_engine() -> AnalyticsEngine:
    """Get or create analytics engine instance."""
    global _analytics_engine

    if _analytics_engine is None:
        # Get configuration from environment
        database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./risk.db")
        bigquery_project = os.getenv("BIGQUERY_PROJECT", "fusion-prime")
        bigquery_dataset = os.getenv("BIGQUERY_DATASET", "analytics")

        logger.info(
            f"Initializing AnalyticsEngine with BigQuery: {bigquery_project}.{bigquery_dataset}"
        )

        try:
            _analytics_engine = AnalyticsEngine(
                database_url=database_url,
                bigquery_project=bigquery_project,
                bigquery_dataset=bigquery_dataset,
            )
        except Exception as e:
            logger.warning(f"Failed to initialize AnalyticsEngine: {e}")
            # Create a mock analytics engine that always returns safe values
            from app.core.mock_analytics_engine import MockAnalyticsEngine

            _analytics_engine = MockAnalyticsEngine()

    return _analytics_engine


def init_services():
    """Initialize all services."""
    logger.info("Initializing Risk Engine services...")

    # Initialize risk calculator
    risk_calc = get_risk_calculator()
    logger.info("Risk calculator initialized")

    # Initialize analytics engine
    analytics = get_analytics_engine()
    logger.info("Analytics engine initialized")

    logger.info("All services initialized successfully")


def cleanup_services():
    """Cleanup all services."""
    global _risk_calculator, _analytics_engine

    logger.info("Cleaning up Risk Engine services...")

    if _risk_calculator:
        _risk_calculator.cleanup()
        _risk_calculator = None

    if _analytics_engine:
        _analytics_engine.cleanup()
        _analytics_engine = None

    logger.info("All services cleaned up successfully")


def get_engine():
    """Get the database engine."""
    return _engine


def get_session_factory():
    """Get the session factory."""
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session."""
    try:
        async with _session_factory() as session:
            yield session
    except Exception as e:
        logger.error(f"Failed to create database session: {e}")
        raise
