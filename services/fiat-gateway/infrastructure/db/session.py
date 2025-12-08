"""Database session management for Fiat Gateway."""

import logging
import os
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

logger = logging.getLogger(__name__)

Base = declarative_base()

# Global engine - created lazily
_engine = None


def get_database_url() -> str:
    """Get database URL from environment."""
    return os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./fiat_gateway.db")


def get_engine():
    """Get or create database engine (lazy initialization)."""
    global _engine

    if _engine is None:
        database_url = get_database_url()

        # Handle Cloud SQL connection via VPC (private IP) vs Unix socket
        # When using VPC egress='private-ranges-only', we should use TCP to private IP
        # Format: postgresql+asyncpg://user:pass@/dbname?host=/cloudsql/... (Unix socket)
        # vs: postgresql+asyncpg://user:pass@PRIVATE_IP:5432/dbname (TCP via VPC)

        if database_url.startswith("postgresql+asyncpg://"):
            from urllib.parse import parse_qs, urlparse

            parsed = urlparse(database_url)
            query_params = parse_qs(parsed.query)

            # Check if using Unix socket (host=/cloudsql/...)
            if "host" in query_params:
                host_path = query_params["host"][0]
                if host_path.startswith("/cloudsql/"):
                    # Unix socket connection - asyncpg doesn't support this well
                    # With VPC egress, we should use TCP instead
                    logger.warning(
                        f"Unix socket connection detected: {host_path}. "
                        "Consider using private IP TCP connection for VPC egress."
                    )
                    # Try to use the connection anyway - may work in some environments
                    logger.info("Attempting Unix socket connection (may fail with asyncpg)")
                else:
                    logger.info("Using TCP connection with specified host")
            elif parsed.hostname:
                # Standard TCP connection (could be private IP via VPC)
                logger.info(f"Using TCP connection to {parsed.hostname}:{parsed.port or 5432}")
            else:
                # Empty hostname - likely Unix socket format
                logger.warning("Empty hostname in connection URL - may need private IP for VPC")
        elif database_url.startswith("postgresql://"):
            logger.info("Using PostgreSQL (standard driver)")
        else:
            logger.info(f"Using database: {database_url.split('://')[0]}")

        try:
            _engine = create_async_engine(
                database_url,
                echo=False,
                future=True,
                pool_pre_ping=True,
                # For asyncpg with VPC, we may need additional connection args
                connect_args={} if not database_url.startswith("postgresql+asyncpg://") else {},
            )
            logger.info("Database engine created successfully")
        except Exception as e:
            logger.error(f"Failed to create database engine: {e}")
            # Don't raise immediately - allow service to start
            logger.warning("Service will continue but database operations may fail")
            raise

    return _engine


def get_session_factory():
    """Get session factory."""
    engine = get_engine()
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session():
    """Get database session."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session
