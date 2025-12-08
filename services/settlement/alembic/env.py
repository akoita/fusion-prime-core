import os
import sys
from logging.config import fileConfig
from urllib.parse import urlparse

from alembic import context
from sqlalchemy import create_engine, engine_from_config, pool

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import the models
from infrastructure.db.models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_cloud_sql_engine(database_url: str):
    """Create SQLAlchemy engine using Unix socket connection or TCP connection.

    When --set-cloudsql-instances is used, Cloud Run creates a Unix socket proxy
    at /cloudsql/INSTANCE_CONNECTION_NAME. We connect via this socket.

    For local development, falls back to TCP connection.
    """
    import os
    import re
    from urllib.parse import parse_qs, quote, unquote, urlparse

    # Strip whitespace from URL
    database_url = database_url.strip()

    # Map database names to Cloud SQL instance connection names
    db_instance_map = {
        "settlement_db": "fusion-prime:us-central1:fp-settlement-db-590d836a",
        "risk_db": "fusion-prime:us-central1:fp-risk-db-1d929830",
        "compliance_db": "fusion-prime:us-central1:fp-compliance-db-0b9f2040",
    }

    # Parse database URL - use regex to handle special characters in password
    # Format: postgresql://username:password@host:port/database
    # SECURITY: Do not log passwords - extract before validation
    try:
        url_match = re.match(r"^postgresql://([^:@]+):([^@]+)@([^:]+):(\d+)/(.+)$", database_url)

        if url_match:
            # Standard URL format with password
            db_user = url_match.group(1)
            db_pass = url_match.group(2)
            db_host = url_match.group(3)
            db_port = int(url_match.group(4))
            db_name = url_match.group(5)
        else:
            # Try urlparse for other formats
            parsed = urlparse(database_url)
            db_user = parsed.username
            db_pass = parsed.password
            db_host = parsed.hostname
            db_port = parsed.port if parsed.port else 5432
            db_name = parsed.path.lstrip("/")
    except Exception as e:
        # Don't expose the full URL in error messages
        raise ValueError(f"Failed to parse database URL: {str(e)}")

    if not db_user or not db_pass or not db_name or not db_host:
        # Safe URL for error messages - mask the password
        safe_url = database_url.split("@", 1)[0] + "@***"
        raise ValueError(f"Invalid database URL format: {safe_url}")

    # Get the Cloud SQL instance connection name
    instance_connection_name = db_instance_map.get(db_name)
    if not instance_connection_name:
        raise ValueError(f"Unknown database: '{db_name}'")

    # Check if running in Cloud Run environment (has /cloudsql socket)
    unix_socket_path = f"/cloudsql/{instance_connection_name}"
    use_unix_socket = os.path.exists(unix_socket_path)

    # In Cloud Run, ALWAYS use Unix socket if available, regardless of what's in the URL
    # This fixes the issue where Secret Manager URLs have private IPs but we're in Cloud Run
    if use_unix_socket:
        print(f"📊 Cloud Run detected - using Unix socket: {unix_socket_path}")
        use_unix_socket = True

    # URL encode the password to handle special characters
    from urllib.parse import quote_plus

    encoded_password = quote_plus(db_pass)

    if use_unix_socket:
        # Use Unix socket connection for Cloud Run
        socket_url = f"postgresql://{db_user}:{encoded_password}@/{db_name}?host={unix_socket_path}"
        connect_args = {}
        print(f"📊 Using Unix socket connection: {unix_socket_path}")
    else:
        # Use TCP connection with the provided host (could be private IP or localhost with proxy)
        print(f"📊 Using TCP connection to {db_host}:{db_port}")
        socket_url = f"postgresql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"

    # Create SQLAlchemy engine
    # SECURITY: Disable echo/logging to prevent password exposure in logs
    engine = create_engine(
        socket_url,
        poolclass=pool.NullPool,
        echo=False,  # Never log connection strings or queries
    )

    return engine


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # Get database URL from environment variable
    url = os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))
    context.configure(
        url=url,
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
    # Get database URL from environment variable
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        # Use Cloud SQL Python Connector for Cloud Run environment
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
