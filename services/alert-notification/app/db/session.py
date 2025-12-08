"""Database session management for Alert Notification Service."""

import logging
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections to Risk Engine database for alert_notifications table."""

    def __init__(self, database_url: str):
        """
        Initialize database manager.

        Args:
            database_url: PostgreSQL connection string (supports both sync and async URLs)
        """
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None

        if database_url:
            try:
                # Support both sync (postgresql://) and async (postgresql+asyncpg://) URLs
                # If async URL is provided, convert to sync for use with sync SQLAlchemy sessions
                # asyncpg is installed to support async URLs, but we use sync sessions for simplicity
                sync_database_url = database_url
                if database_url.startswith("postgresql+asyncpg://"):
                    sync_database_url = database_url.replace(
                        "postgresql+asyncpg://", "postgresql://", 1
                    )
                    logger.debug(
                        "Converted async database URL to sync URL (using psycopg2 for sync sessions)"
                    )

                self.engine = create_engine(
                    sync_database_url, pool_pre_ping=True, pool_recycle=3600
                )
                self.SessionLocal = sessionmaker(
                    autocommit=False, autoflush=False, bind=self.engine
                )
                logger.info("Database connection initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize database: {e}")
                raise

    @contextmanager
    def get_session(self):
        """Get a database session with automatic cleanup."""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized")

        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
