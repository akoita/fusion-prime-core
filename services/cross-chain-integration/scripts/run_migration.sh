#!/bin/bash
# Run Alembic migrations for Cross-Chain Integration Service
# This script follows the pattern from run_alembic_migrations.sh

set -e

echo "========================================="
echo "Starting Alembic Migrations for Cross-Chain Integration"
echo "========================================="

# Change to service directory (alembic.ini is at /app/alembic.ini in Docker)
cd /app

# DATABASE_URL should already be set from Cloud Run Job environment
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERROR: DATABASE_URL environment variable is not set"
    exit 1
fi

echo "✓ Using DATABASE_URL from environment"
echo ""

# Check if migrations exist
if [ ! -d "alembic/versions" ] || [ -z "$(ls -A alembic/versions/*.py 2>/dev/null)" ]; then
    echo "⚠️  No migration files found"
    echo "→ This should not happen - migrations should be in the repository"
    exit 1
else
    echo "✓ Found migration files in alembic/versions/"
fi

# Run migrations
echo ""
echo "→ Running migrations..."
echo ""

if alembic upgrade head; then
    echo ""
    echo "✅ Migrations completed successfully!"
    exit 0
else
    echo ""
    echo "❌ Migration failed!"
    exit 1
fi
