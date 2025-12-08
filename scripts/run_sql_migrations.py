#!/usr/bin/env python3
"""
SQL Migration Runner for Fusion Prime

This script runs SQL migrations directly for the Settlement Service.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def run_sql_migrations():
    """Run SQL migrations directly."""
    print("🔄 Running SQL migrations...")

    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

        # Get database connection details from environment
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            print("❌ DATABASE_URL environment variable not set")
            return False

        # Parse the database URL using urllib
        from urllib.parse import parse_qs, urlparse

        parsed_url = urlparse(database_url)

        if parsed_url.scheme != "postgresql":
            print(f"❌ Invalid database scheme: {parsed_url.scheme}")
            return False

        user = parsed_url.username
        password = parsed_url.password
        db_name = parsed_url.path.lstrip("/")

        # Get host from query parameters
        query_params = parse_qs(parsed_url.query)
        host = query_params.get("host", ["localhost"])[0]

        if not user or not password or not db_name:
            print(
                f"❌ Missing required connection details: user={user}, password={'***' if password else None}, db_name={db_name}"
            )
            return False

        # Connect to database
        print(f"📊 Connecting to database: {user}@{host}/{db_name}")

        # For Cloud SQL, we need to use the socket path
        if host.startswith("/cloudsql/"):
            # Use socket connection for Cloud SQL
            conn = psycopg2.connect(user=user, password=password, database=db_name, host=host)
        else:
            # Use regular TCP connection
            conn = psycopg2.connect(
                user=user, password=password, database=db_name, host=host, port=5432
            )

        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Check if tables already exist
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('settlement_commands', 'webhook_subscriptions')
        """
        )
        existing_tables = [row[0] for row in cursor.fetchall()]

        if "settlement_commands" in existing_tables and "webhook_subscriptions" in existing_tables:
            print("✅ Database tables already exist")
            return True

        # Create settlement_commands table
        if "settlement_commands" not in existing_tables:
            print("📋 Creating settlement_commands table...")
            cursor.execute(
                """
                CREATE TABLE settlement_commands (
                    command_id VARCHAR(128) PRIMARY KEY,
                    workflow_id VARCHAR(128) NOT NULL,
                    account_ref VARCHAR(128) NOT NULL,
                    payer VARCHAR(128),
                    payee VARCHAR(128),
                    asset_symbol VARCHAR(64),
                    amount_numeric NUMERIC(38, 18),
                    status VARCHAR(32) NOT NULL,
                    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """
            )
            print("✅ settlement_commands table created")

        # Create webhook_subscriptions table
        if "webhook_subscriptions" not in existing_tables:
            print("📋 Creating webhook_subscriptions table...")
            cursor.execute(
                """
                CREATE TABLE webhook_subscriptions (
                    subscription_id VARCHAR(128) PRIMARY KEY,
                    url VARCHAR(512) NOT NULL,
                    secret VARCHAR(256) NOT NULL,
                    event_types TEXT NOT NULL,
                    enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    description VARCHAR(512),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """
            )
            print("✅ webhook_subscriptions table created")

        cursor.close()
        conn.close()

        print("✅ SQL migrations completed successfully")
        return True

    except ImportError:
        print("❌ psycopg2 not installed. Installing...")
        import subprocess

        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "psycopg2-binary"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("✅ psycopg2 installed successfully")
            # Retry the migration
            return await run_sql_migrations()
        else:
            print(f"❌ Failed to install psycopg2: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error running SQL migrations: {e}")
        return False


async def main():
    """Main function."""
    print("🚀 Fusion Prime SQL Migration Runner")
    print("=" * 50)

    # Check if DATABASE_URL is set
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        print("Please set DATABASE_URL before running migrations")
        sys.exit(1)

    print(f"📊 Database URL: {database_url.split('@')[0]}@***")

    # Run migrations
    success = await run_sql_migrations()

    if success:
        print("\n✅ SQL migrations completed successfully!")
    else:
        print("\n❌ SQL migrations failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
