#!/usr/bin/env python3
"""
Database Migration Runner for Fusion Prime

This script runs Alembic migrations for the Settlement Service.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Add the settlement service to the Python path
settlement_service_path = project_root / "services" / "settlement"
sys.path.insert(0, str(settlement_service_path))


async def run_migrations():
    """Run database migrations."""
    print("🔄 Running database migrations...")

    try:
        import subprocess

        # Change to settlement service directory
        os.chdir(settlement_service_path)

        # Run alembic upgrade
        result = subprocess.run(
            ["poetry", "run", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            env=os.environ.copy(),
        )

        if result.returncode == 0:
            print("✅ Database migrations completed successfully")
            print(result.stdout)
        else:
            print(f"❌ Migration failed: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ Error running migrations: {e}")
        return False

    return True


async def check_migration_status():
    """Check the current migration status."""
    print("📊 Checking migration status...")

    try:
        import subprocess

        # Change to settlement service directory
        os.chdir(settlement_service_path)

        # Run alembic current
        result = subprocess.run(
            ["poetry", "run", "alembic", "current"],
            capture_output=True,
            text=True,
            env=os.environ.copy(),
        )

        if result.returncode == 0:
            print("📋 Current migration status:")
            print(result.stdout)
        else:
            print(f"⚠️  Could not check migration status: {result.stderr}")

    except Exception as e:
        print(f"❌ Error checking migration status: {e}")


async def main():
    """Main function."""
    print("🚀 Fusion Prime Database Migration Runner")
    print("=" * 50)

    # Check if DATABASE_URL is set
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        print("Please set DATABASE_URL before running migrations")
        sys.exit(1)

    print(f"📊 Database URL: {database_url.split('@')[0]}@***")

    # Check current status
    await check_migration_status()

    # Run migrations
    success = await run_migrations()

    if success:
        print("\n✅ Database migrations completed successfully!")
    else:
        print("\n❌ Database migrations failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
