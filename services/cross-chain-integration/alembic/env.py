"""Alembic environment configuration for Cross-Chain Integration database migrations."""

import os
import re
from logging.config import fileConfig
from urllib.parse import quote_plus

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
    """Create SQLAlchemy engine using Unix socket connection or TCP connection.

    When --set-cloudsql-instances is used, Cloud Run creates a Unix socket proxy
    at /cloudsql/INSTANCE_CONNECTION_NAME. We connect via this socket.

    For VPC egress mode, falls back to TCP connection with private IP.
    """
    import os

    # Strip whitespace from URL
    database_url = database_url.strip()

    print(f"📊 Raw DATABASE_URL (first 80 chars): {database_url[:80]}...")

    # Cloud SQL instance connection name for Cross-Chain Integration
    instance_connection_name = "fusion-prime:us-central1:fp-cross-chain-db-0c277aa9"

    # Handle postgresql+asyncpg:// format - convert to postgresql:// for parsing
    normalized_url = database_url
    if database_url.startswith("postgresql+asyncpg://"):
        normalized_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        print("📊 Converted postgresql+asyncpg:// to postgresql:// for parsing")

    # Parse database URL - use regex to handle special characters in password
    # Format: postgresql://username:password@host:port/database
    try:
        url_match = re.match(r"^postgresql://([^:@]+):([^@]+)@([^:]+):(\d+)/(.+)$", normalized_url)

        if url_match:
            # Standard URL format with password
            db_user = url_match.group(1)
            db_pass = url_match.group(2)
            db_host = url_match.group(3)
            db_port = int(url_match.group(4))
            db_name = url_match.group(5).split("?")[0]  # Remove query params if present
        else:
            # Try urlparse for other formats
            from urllib.parse import urlparse

            parsed = urlparse(normalized_url)
            db_user = parsed.username
            db_pass = parsed.password
            db_host = parsed.hostname
            db_port = parsed.port if parsed.port else 5432
            db_name = parsed.path.lstrip("/").split("?")[0]  # Remove query params if present
    except Exception as e:
        raise ValueError(f"Failed to parse database URL: {str(e)}")

    if not db_user or not db_pass or not db_name:
        safe_url = normalized_url.split("@", 1)[0] + "@***"
        raise ValueError(f"Invalid database URL format: {safe_url}")

    # Check if running in Cloud Run environment (has /cloudsql socket)
    unix_socket_path = f"/cloudsql/{instance_connection_name}"
    use_unix_socket = os.path.exists(unix_socket_path)

    # In Cloud Run, ALWAYS use Unix socket if available, regardless of what's in the URL
    # This fixes the issue where Secret Manager URLs have private IPs but we're in Cloud Run
    if use_unix_socket:
        print(f"📊 Cloud Run detected - using Unix socket: {unix_socket_path}")
        use_unix_socket = True

    # URL encode the password to handle special characters
    # Always decode first (in case it's already encoded), then encode
    from urllib.parse import unquote_plus

    decoded_password = unquote_plus(db_pass)  # Decode if already encoded
    encoded_password = quote_plus(decoded_password)  # Encode properly

    if use_unix_socket:
        # Use Unix socket connection for Cloud Run
        socket_url = f"postgresql://{db_user}:{encoded_password}@/{db_name}?host={unix_socket_path}"
        print(f"📊 Using Unix socket connection: {unix_socket_path}")
    else:
        # Use TCP connection with the provided host (could be private IP or localhost with proxy)
        print(f"📊 Using TCP connection to {db_host}:{db_port}")
        socket_url = f"postgresql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}?sslmode=require"

    # Create SQLAlchemy engine
    # SECURITY: Disable echo/logging to prevent password exposure in logs
    try:
        print(f"📊 Creating SQLAlchemy engine...")
        engine = create_engine(
            socket_url,
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
    database_url = os.getenv("DATABASE_URL", "sqlite:///./cross_chain.db")

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
