#!/usr/bin/env python3
"""
Database Setup Script for Fusion Prime

This script creates the necessary database tables for the Settlement Service.
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

from app.dependencies import get_engine
from infrastructure.db.models import Base


async def create_tables():
    """Create database tables."""
    print("🔧 Setting up database tables...")

    try:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables created successfully")
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")
        return False

    return True


async def main():
    """Main function."""
    print("🚀 Fusion Prime Database Setup")
    print("=" * 40)

    # Check if DATABASE_URL is set
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        print("Please set DATABASE_URL before running this script")
        sys.exit(1)

    print(f"📊 Database URL: {database_url.split('@')[0]}@***")

    success = await create_tables()

    if success:
        print("\n✅ Database setup completed successfully!")
    else:
        print("\n❌ Database setup failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
