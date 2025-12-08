"""Database session management for risk engine service."""

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


def create_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url, echo=False, future=True)


def create_session_factory(engine: AsyncEngine) -> sessionmaker[AsyncSession]:
    return sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
