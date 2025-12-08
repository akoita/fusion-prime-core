"""
Base Database utilities for indexers

Provides common database connection and session management patterns.
"""

import logging
import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)


class BaseDatabase:
    """Base database connection manager for indexers."""

    def __init__(self, database_url: str = None, service_name: str = "indexer"):
        """
        Initialize database connection.

        Args:
            database_url: PostgreSQL connection string (or from env)
            service_name: Name of the service (for logging)
        """
        self.service_name = service_name

        # Get database URL from parameter or environment
        self.database_url = database_url or os.getenv("DATABASE_URL")

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

        # Create engine with connection pooling for Cloud SQL
        # Use NullPool for Cloud Run to avoid connection issues
        self.engine = create_engine(
            self.database_url,
            poolclass=NullPool,  # No connection pooling for serverless
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True,  # Verify connections before using
        )

        # Create sessionmaker
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        logger.info(f"✅ {service_name} database initialized")

    def init_db(self, base):
        """
        Initialize database tables.

        Args:
            base: SQLAlchemy declarative base
        """
        logger.info(f"Initializing {self.service_name} database tables...")
        try:
            base.metadata.create_all(bind=self.engine)
            logger.info(f"✅ {self.service_name} database tables created successfully")
        except Exception as e:
            logger.error(f"❌ Failed to create {self.service_name} database tables: {e}")
            raise

    def get_db(self) -> Generator[Session, None, None]:
        """
        Get database session.

        Usage:
            with db.get_db_session() as session:
                # Use session
                pass
        """
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    @contextmanager
    def get_db_session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions with auto-commit.

        Usage:
            with db.get_db_session() as session:
                # Use session
                # Auto-commits on success, rolls back on error
        """
        db = self.SessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def check_connection(self) -> bool:
        """Check if database connection is working."""
        try:
            with self.engine.connect() as conn:
                conn.execute("SELECT 1")
            logger.info(f"✅ {self.service_name} database connection successful")
            return True
        except Exception as e:
            logger.error(f"❌ {self.service_name} database connection failed: {e}")
            return False


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Set SQLite pragmas if using SQLite (for local testing)."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
