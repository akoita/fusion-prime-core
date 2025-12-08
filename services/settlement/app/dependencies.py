import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from infrastructure.db.session import create_engine, create_session_factory
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

DATABASE_URL_ENV = "DATABASE_URL"
DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///./settlement.db"

# Get database URL and log it (without password)
database_url = os.environ.get(DATABASE_URL_ENV, DEFAULT_DATABASE_URL)
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
    raise


def init_db(url: str) -> None:
    global _engine, _session_factory
    _engine = create_engine(url)
    _session_factory = create_session_factory(_engine)


def get_engine():
    return _engine


def get_session_factory():
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    try:
        async with _session_factory() as session:
            yield session
    except Exception as e:
        logger.error(f"Failed to create database session: {e}")
        raise
