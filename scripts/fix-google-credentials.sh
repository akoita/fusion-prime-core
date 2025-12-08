#!/bin/bash

# Fix Google Cloud credentials for testing
set -e

echo "🔧 Fixing Google Cloud credentials for testing..."

# Comment out the invalid credentials path
sed -i 's|GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json|# GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json|' .env.test

# Add comment about using Application Default Credentials
echo "" >> .env.test
echo "# Use Application Default Credentials for testing" >> .env.test
echo "# Run: gcloud auth application-default login" >> .env.test

echo "✅ Fixed Google Cloud credentials"
echo "ℹ️  To authenticate, run: gcloud auth application-default login"
