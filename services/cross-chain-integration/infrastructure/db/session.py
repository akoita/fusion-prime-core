"""Database session management for Cross-Chain Integration Service."""

import logging
import os
from functools import lru_cache
from urllib.parse import parse_qs, urlparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

logger = logging.getLogger(__name__)

Base = declarative_base()

# Global engine - created lazily
_engine = None


def get_database_url() -> str:
    """Get database URL from environment."""
    return os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./cross_chain_integration.db")


def get_engine():
    """Get or create database engine (lazy initialization)."""
    global _engine

    if _engine is None:
        database_url = get_database_url()

        # Handle Cloud SQL connection via VPC (private IP) vs Unix socket
        # When using VPC egress='private-ranges-only', we should use TCP to private IP
        # Format: postgresql+asyncpg://user:pass@PRIVATE_IP:5432/dbname (TCP via VPC)

        connect_args = {}
        processed_url = database_url

        if database_url.startswith("postgresql+asyncpg://"):
            parsed = urlparse(database_url)
            query_params = parse_qs(parsed.query)

            # asyncpg doesn't support sslmode in URL - need to handle it separately
            sslmode = None
            if "sslmode" in query_params:
                sslmode = query_params["sslmode"][0].lower()
                # Remove sslmode from query params to rebuild URL
                new_query_params = {k: v for k, v in query_params.items() if k != "sslmode"}
                # Rebuild URL without sslmode
                new_query = "&".join(f"{k}={v[0]}" for k, v in new_query_params.items() if v)
                processed_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}" + (
                    f"?{new_query}" if new_query else ""
                )

            # Configure SSL for asyncpg based on sslmode
            # asyncpg uses ssl=True/False or an ssl context, not sslmode string values
            # For Cloud SQL, we need to disable certificate verification
            # (Cloud SQL uses self-signed certificates)
            if sslmode:
                if sslmode in ["require", "prefer", "allow"]:
                    # For Cloud SQL private IP connections, SSL is required
                    # but certificate verification should be disabled for Cloud SQL
                    # as it uses self-signed certificates
                    import ssl as ssl_module

                    ssl_context = ssl_module.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl_module.CERT_NONE
                    connect_args["ssl"] = ssl_context
                    logger.info(
                        f"Configured SSL connection with certificate verification disabled (sslmode={sslmode})"
                    )
                elif sslmode == "disable":
                    connect_args["ssl"] = False
                    logger.info("SSL disabled")
                # For other modes, asyncpg will use default behavior (SSL enabled)

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
                processed_url,
                echo=False,
                future=True,
                pool_pre_ping=True,
                connect_args=connect_args,
            )
            logger.info("Database engine created successfully")
        except Exception as e:
            logger.error(f"Failed to create database engine: {e}")
            # Don't raise immediately - allow service to start
            logger.warning(
                "Service will continue - database operations may fail until connection is established"
            )
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
