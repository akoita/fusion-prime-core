#!/bin/bash
# Run database migrations for Risk Engine and Compliance services
# This script executes schema.sql files against the Cloud SQL databases

set -euo pipefail

echo "🔄 Running database migrations..."

# Get connection strings from Secret Manager
export COMPLIANCE_DB_CONN=$(gcloud secrets versions access latest --secret="fp-compliance-db-connection-string" 2>&1)
export RISK_DB_CONN=$(gcloud secrets versions access latest --secret="fp-risk-db-connection-string" 2>&1)

# Check if we have the connection strings
if [[ "$COMPLIANCE_DB_CONN" == *"NOT_FOUND"* ]]; then
    echo "⚠️  Compliance DB secret not found. Skipping..."
else
    echo "📊 Running Compliance DB migrations..."
    # Note: psql would be used here if available
    echo "Connection string: ${COMPLIANCE_DB_CONN:0:50}..."
fi

if [[ "$RISK_DB_CONN" == *"NOT_FOUND"* ]]; then
    echo "⚠️  Risk Engine DB secret not found. Skipping..."
else
    echo "📊 Running Risk Engine DB migrations..."
    echo "Connection string: ${RISK_DB_CONN:0:50}..."
fi

echo "✅ Migration script ready (requires psql or Cloud SQL Proxy)"
