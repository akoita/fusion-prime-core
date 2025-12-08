#!/bin/bash
# Helper script to manage deployment configuration in Secret Manager
#
# Usage:
#   ./manage-secrets.sh create dev
#   ./manage-secrets.sh update staging
#   ./manage-secrets.sh show prod

set -e

COMMAND=$1
ENVIRONMENT=$2

if [ -z "$COMMAND" ] || [ -z "$ENVIRONMENT" ]; then
    echo "Usage: $0 {create|update|show|delete} {dev|staging|prod}"
    exit 1
fi

SECRET_NAME="settlement-service-config-$ENVIRONMENT"
PROJECT_ID="fusion-prime"

case $COMMAND in
    create)
        echo "Creating configuration secret: $SECRET_NAME"
        echo ""
        echo "Enter configuration as JSON (Ctrl+D when done):"
        echo "Example:"
        cat <<'EOF'
{
  "environment": "dev",
  "region": "us-central1",
  "service_name": "settlement-service",
  "service_account": "settlement-service@fusion-prime.iam.gserviceaccount.com",
  "pubsub_topic": "settlement.events.v1",
  "pubsub_subscription": "settlement-events-consumer",
  "db_host": "10.30.0.3",
  "db_port": "5432",
  "db_name": "settlement_db",
  "db_user": "settlement_user",
  "cloudsql_instance": "fusion-prime:us-central1:fusion-prime-db-a504713e",
  "vpc_connector": "fusion-prime-vpc-connector",
  "memory": "512Mi",
  "cpu": "1",
  "min_instances": "0",
  "max_instances": "10",
  "timeout": "300",
  "concurrency": "80"
}
EOF
        echo ""
        echo "Paste JSON config:"

        # Read from stdin
        CONFIG=$(cat)

        # Validate JSON
        echo "$CONFIG" | jq . > /dev/null || {
            echo "❌ Invalid JSON"
            exit 1
        }

        # Create secret
        echo "$CONFIG" | gcloud secrets create $SECRET_NAME \
            --project=$PROJECT_ID \
            --replication-policy="automatic" \
            --data-file=-

        echo "✅ Secret created: $SECRET_NAME"

        # Grant Cloud Build access
        PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
        gcloud secrets add-iam-policy-binding $SECRET_NAME \
            --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
            --role="roles/secretmanager.secretAccessor"

        echo "✅ Granted Cloud Build access to secret"
        ;;

    update)
        echo "Updating configuration secret: $SECRET_NAME"
        echo ""
        echo "Enter new configuration as JSON (Ctrl+D when done):"

        # Read from stdin
        CONFIG=$(cat)

        # Validate JSON
        echo "$CONFIG" | jq . > /dev/null || {
            echo "❌ Invalid JSON"
            exit 1
        }

        # Add new version
        echo "$CONFIG" | gcloud secrets versions add $SECRET_NAME \
            --project=$PROJECT_ID \
            --data-file=-

        echo "✅ Secret updated: $SECRET_NAME"
        ;;

    show)
        echo "Current configuration for: $SECRET_NAME"
        echo ""
        gcloud secrets versions access latest \
            --secret=$SECRET_NAME \
            --project=$PROJECT_ID | jq .
        ;;

    delete)
        echo "⚠️  Deleting secret: $SECRET_NAME"
        read -p "Are you sure? (yes/no): " CONFIRM

        if [ "$CONFIRM" = "yes" ]; then
            gcloud secrets delete $SECRET_NAME \
                --project=$PROJECT_ID \
                --quiet
            echo "✅ Secret deleted: $SECRET_NAME"
        else
            echo "❌ Cancelled"
        fi
        ;;

    *)
        echo "Unknown command: $COMMAND"
        echo "Usage: $0 {create|update|show|delete} {dev|staging|prod}"
        exit 1
        ;;
esac
