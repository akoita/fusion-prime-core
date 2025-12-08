"""
Dependencies for Compliance Service.
"""

import logging
import os
from functools import lru_cache
from typing import Optional

from app.core.compliance_engine import ComplianceEngine
from app.core.identity_engine import IdentityEngine
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


@lru_cache()
def get_database_url() -> str:
    """Get database URL from environment."""
    database_url = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./compliance.db",  # Use SQLite as fallback
    )
    # Convert postgresql+asyncpg:// to postgresql:// for SQLAlchemy compatibility
    # asyncpg is installed to support async URLs, but we use synchronous sessions
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        logger.info(
            "Converted postgresql+asyncpg:// URL to postgresql:// for SQLAlchemy compatibility"
        )
    return database_url


@lru_cache()
def get_engine():
    """Get database engine."""
    database_url = get_database_url()
    logger.info(f"Connecting to database: {database_url}")

    try:
        engine = create_async_engine(database_url, echo=False)
        return engine
    except Exception as e:
        logger.warning(f"Failed to create database engine: {e}")
        # Return None to indicate database is not available
        return None


@lru_cache()
def get_session_factory():
    """Get database session factory."""
    engine = get_engine()
    if engine is None:
        return None
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session():
    """Get database session."""
    session_factory = get_session_factory()
    if session_factory is None:
        # Return a mock session when database is not available
        yield None
        return

    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


@lru_cache()
def get_compliance_engine():
    """Get compliance engine instance with production implementation."""
    database_url = get_database_url()

    # Use production implementation with database
    engine = ComplianceEngine(database_url=database_url)
    logger.info(f"Compliance engine initialized with database: {database_url}")

    return engine


@lru_cache()
def get_identity_engine():
    """Get identity engine instance."""
    return IdentityEngine()


@lru_cache()
def get_identity_service():
    """Get identity service instance (alias for get_identity_engine)."""
    return get_identity_engine()
