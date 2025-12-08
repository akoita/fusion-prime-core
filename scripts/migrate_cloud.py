#!/usr/bin/env python3
"""
Cloud Migration Runner
Runs database migrations in Cloud Run environment with Cloud SQL access.
"""

import os
import sys


def main():
    """Main function."""
    print("🚀 Cloud Migration Runner")
    print("=" * 50)

    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    except ImportError:
        print("📦 Installing psycopg2-binary...")
        import subprocess

        subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

    # Get database connection details from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        sys.exit(1)

    # Parse the database URL
    from urllib.parse import parse_qs, urlparse

    parsed_url = urlparse(database_url)

    user = parsed_url.username
    password = parsed_url.password
    db_name = parsed_url.path.lstrip("/")
    query_params = parse_qs(parsed_url.query)
    host = query_params.get("host", ["localhost"])[0]

    print(f"📊 Connecting to: {user}@{host}/{db_name}")

    # Connect to database via Cloud SQL Unix socket
    conn = psycopg2.connect(user=user, password=password, database=db_name, host=host)

    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    # Check existing tables
    cursor.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name IN ('settlement_commands', 'webhook_subscriptions')
    """
    )
    existing_tables = [row[0] for row in cursor.fetchall()]

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
    else:
        print("✓ settlement_commands table already exists")

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
    else:
        print("✓ webhook_subscriptions table already exists")

    cursor.close()
    conn.close()

    print("\n✅ Migration completed successfully!")


if __name__ == "__main__":
    main()
