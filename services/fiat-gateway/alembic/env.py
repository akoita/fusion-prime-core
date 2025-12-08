"""Alembic environment configuration for Fiat Gateway database migrations."""

import os
from logging.config import fileConfig
from urllib.parse import parse_qs, quote_plus, urlparse

from alembic import context

# Import Base and models
from infrastructure.db.models import Base
from sqlalchemy import create_engine, engine_from_config, pool

# This is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


def get_cloud_sql_engine(database_url: str):
    """Create SQLAlchemy engine using VPC TCP connection.

    When using VPC egress='private-ranges-only', we connect via TCP to private IP.
    Format: postgresql+asyncpg://user:pass@PRIVATE_IP:5432/dbname

    Follows the same pattern as settlement/risk-engine services:
    - Uses regex parsing first to handle special characters in passwords
    - Falls back to urlparse for other formats
    - URL encodes password for SQLAlchemy
    """
    import re
    from urllib.parse import quote_plus

    # Strip whitespace from URL
    database_url = database_url.strip()

    print(f"📊 Raw DATABASE_URL (first 80 chars): {database_url[:80]}...")

    # Handle postgresql+asyncpg:// format - convert to postgresql:// for parsing
    # The URL structure is the same, just the driver prefix differs
    normalized_url = database_url
    if database_url.startswith("postgresql+asyncpg://"):
        normalized_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        print("📊 Converted postgresql+asyncpg:// to postgresql:// for parsing")

    # Parse database URL - use regex FIRST (same pattern as working services)
    # This handles special characters in passwords better than urlparse
    # Format: postgresql://username:password@host:port/database
    try:
        url_match = re.match(r"^postgresql://([^:@]+):([^@]+)@([^:]+):(\d+)/(.+)$", normalized_url)

        if url_match:
            # Standard URL format with password - regex parsing (handles special chars)
            db_user = url_match.group(1)
            db_pass = url_match.group(2)
            db_host = url_match.group(3)
            db_port = int(url_match.group(4))
            db_name = url_match.group(5)
            print("📊 Parsed URL using regex (handles special characters in password)")
        else:
            # Fall back to urlparse for other formats (e.g., Unix socket)
            parsed = urlparse(normalized_url)
            db_user = parsed.username
            db_pass = parsed.password
            db_host = parsed.hostname
            db_port = parsed.port if parsed.port else 5432
            db_name = parsed.path.lstrip("/")
            print("📊 Parsed URL using urlparse (fallback for non-standard formats)")

    except Exception as e:
        # Don't expose the full URL in error messages
        raise ValueError(f"Failed to parse database URL: {str(e)}")

    # Validate required components
    if not db_user or not db_pass or not db_name or not db_host:
        # Safe URL for error messages - mask the password
        safe_url = normalized_url.split("@", 1)[0] + "@***"
        raise ValueError(f"Invalid database URL format: {safe_url}")

    # URL encode the password to handle special characters (same as working services)
    encoded_password = quote_plus(db_pass)

    # Build connection URL for psycopg2 (postgresql:// format)
    # For VPC TCP connections, use the host:port directly
    connection_url = f"postgresql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"

    print(f"📊 Migration connection: {db_host}:{db_port}")
    print(f"📊 Database: {db_name}")
    print(f"📊 User: {db_user}")

    # Create SQLAlchemy engine for migrations
    # Use psycopg2 driver (via standard postgresql:// URL)
    try:
        print(f"📊 Creating SQLAlchemy engine...")
        engine = create_engine(
            connection_url,
            poolclass=pool.NullPool,
            echo=False,  # Never log connection strings or queries
        )
        print(f"✅ Engine created successfully")
        return engine
    except Exception as e:
        print(f"❌ Failed to create SQLAlchemy engine: {e}")
        raise


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.
    """
    database_url = os.getenv("DATABASE_URL", "sqlite:///./fiat_gateway.db")

    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        # Use Cloud SQL connection handler for VPC/TCP connections
        connectable = get_cloud_sql_engine(database_url)
    else:
        # Fallback to standard connection from alembic.ini
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
