#!/bin/bash
# Update Cloud SQL connection strings to use private IP for VPC egress mode
# This enables asyncpg to work properly with VPC egress='private-ranges-only'

set -e

PROJECT_ID=${1:-${GCP_PROJECT:-"fusion-prime"}}

echo "🔄 Updating Cloud SQL Connection Strings for VPC Mode"
echo "   Project: $PROJECT_ID"
echo ""

# List of databases to update
INSTANCES=(
    "fp-fiat-gateway-db-a0cd6952:fiat_gateway_user:fiat_gateway:fp-fiat-gateway-db-connection-string"
    "fp-cross-chain-db-0c277aa9:cross_chain_user:cross_chain:fp-cross-chain-db-connection-string"
)

for INSTANCE_INFO in "${INSTANCES[@]}"; do
    IFS=':' read -r INSTANCE_NAME DB_USER DB_NAME SECRET_NAME <<< "$INSTANCE_INFO"

    echo "📋 Processing: $INSTANCE_NAME"

    # Get private IP address
    PRIVATE_IP=$(gcloud sql instances describe "$INSTANCE_NAME" \
        --project="$PROJECT_ID" \
        --format="value(ipAddresses[?type=='PRIVATE'].ipAddress)" 2>/dev/null || echo "")

    if [ -z "$PRIVATE_IP" ]; then
        echo "  ⚠️  No private IP found. Checking all IPs..."
        ALL_IPS=$(gcloud sql instances describe "$INSTANCE_NAME" \
            --project="$PROJECT_ID" \
            --format="value(ipAddresses[].ipAddress)" 2>/dev/null)
        PRIVATE_IP=$(echo "$ALL_IPS" | head -1)
    fi

    if [ -z "$PRIVATE_IP" ]; then
        echo "  ❌ Could not determine IP address for $INSTANCE_NAME"
        continue
    fi

    echo "  ✅ Private IP: $PRIVATE_IP"

    # Get database password from existing secret
    # Try multiple secret name patterns
    PASSWORD=$(gcloud secrets versions access latest \
        --secret="${INSTANCE_NAME%-*}-db-password" \
        --project="$PROJECT_ID" 2>/dev/null || echo "")

    if [ -z "$PASSWORD" ]; then
        # Try alternative secret name with underscores replaced
        PASSWORD=$(gcloud secrets versions access latest \
            --secret="fp-${DB_NAME//_/-}-db-db-password" \
            --project="$PROJECT_ID" 2>/dev/null || echo "")
    fi

    if [ -z "$PASSWORD" ]; then
        # Try direct pattern: fp-INSTANCE_BASE-db-db-password
        INSTANCE_BASE="${INSTANCE_NAME%-*}"  # Remove suffix (e.g., -0c277aa9)
        PASSWORD=$(gcloud secrets versions access latest \
            --secret="${INSTANCE_BASE}-db-db-password" \
            --project="$PROJECT_ID" 2>/dev/null || echo "")
    fi

    if [ -z "$PASSWORD" ]; then
        echo "  ⚠️  Could not retrieve password. Trying to list available secrets..."
        gcloud secrets list --project="$PROJECT_ID" --filter="name:${INSTANCE_NAME%-*}" --format="table(name)" 2>&1 | head -5
        echo "  ❌ Could not retrieve password. Skipping..."
        continue
    fi

    # Create new connection string with private IP
    # Format: postgresql+asyncpg://user:pass@PRIVATE_IP:5432/dbname?sslmode=require
    # URL-encode the password to handle special characters
    # Add SSL requirement for Cloud SQL private IP connections
    ENCODED_PASSWORD=$(python3 -c "from urllib.parse import quote_plus; print(quote_plus('${PASSWORD}'))" 2>/dev/null || echo "${PASSWORD}")
    NEW_CONNECTION_STRING="postgresql+asyncpg://${DB_USER}:${ENCODED_PASSWORD}@${PRIVATE_IP}:5432/${DB_NAME}?sslmode=require"

    echo "  📝 Updating secret: $SECRET_NAME"

    # Update secret
    echo -n "$NEW_CONNECTION_STRING" | gcloud secrets versions add "$SECRET_NAME" \
        --project="$PROJECT_ID" \
        --data-file=- 2>/dev/null && {
        echo "  ✅ Connection string updated successfully"
    } || {
        echo "  ⚠️  Failed to update secret (may need manual update)"
        echo "  Connection string: postgresql+asyncpg://${DB_USER}:***@${PRIVATE_IP}:5432/${DB_NAME}"
    }

    echo ""
done

echo "✅ Connection string update complete!"
echo ""
echo "📋 Next Steps:"
echo "  1. Redeploy services to use new connection strings"
echo "  2. Verify database connectivity"
echo "  3. Run migrations if needed"
