#!/bin/bash
# Initialize Google Cloud Pub/Sub Emulator with topics and subscriptions
# This script runs against the local emulator to set up required resources

# Track failures
FAILED=0

# Configuration
PROJECT_ID="${GCP_PROJECT:-fusion-prime-local}"
PUBSUB_EMULATOR_HOST="${PUBSUB_EMULATOR_HOST:-localhost:8085}"

echo "===================================="
echo "Initializing Pub/Sub Emulator"
echo "===================================="
echo "Project ID: $PROJECT_ID"
echo "Emulator Host: $PUBSUB_EMULATOR_HOST"
echo ""

# Wait for emulator to be ready
echo "Waiting for Pub/Sub emulator to be ready..."
for i in {1..30}; do
  if curl -s "http://${PUBSUB_EMULATOR_HOST}" > /dev/null 2>&1; then
    echo "✓ Emulator is ready"
    break
  fi
  if [ $i -eq 30 ]; then
    echo "✗ Emulator failed to start within 30 seconds"
    exit 1
  fi
  sleep 1
done

echo ""
echo "Creating topics and subscriptions..."
echo ""

# Topic: settlement.events.v1
echo ">>> Creating topic: settlement.events.v1"
curl -s -X PUT \
  "http://${PUBSUB_EMULATOR_HOST}/v1/projects/${PROJECT_ID}/topics/settlement.events.v1" \
  -H "Content-Type: application/json"

# Subscription: settlement-events-consumer
echo ">>> Creating subscription: settlement-events-consumer"
RESPONSE=$(curl -s -X PUT \
  "http://${PUBSUB_EMULATOR_HOST}/v1/projects/${PROJECT_ID}/subscriptions/settlement-events-consumer" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "projects/'${PROJECT_ID}'/topics/settlement.events.v1",
    "ackDeadlineSeconds": 60,
    "messageRetentionDuration": "604800s",
    "retryPolicy": {
      "minimumBackoff": "10s",
      "maximumBackoff": "600s"
    }
  }')
echo "$RESPONSE"
if echo "$RESPONSE" | grep -q '"error"'; then
  # Ignore "ALREADY_EXISTS" errors (409) - script is idempotent
  if ! echo "$RESPONSE" | grep -q '"ALREADY_EXISTS"'; then
    echo "✗ Failed to create subscription"
    FAILED=1
  fi
fi

# Topic: risk.calculations.v1
echo ">>> Creating topic: risk.calculations.v1"
curl -s -X PUT \
  "http://${PUBSUB_EMULATOR_HOST}/v1/projects/${PROJECT_ID}/topics/risk.calculations.v1" \
  -H "Content-Type: application/json"

# Subscription: risk-analytics-consumer
echo ">>> Creating subscription: risk-analytics-consumer"
RESPONSE=$(curl -s -X PUT \
  "http://${PUBSUB_EMULATOR_HOST}/v1/projects/${PROJECT_ID}/subscriptions/risk-analytics-consumer" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "projects/'${PROJECT_ID}'/topics/risk.calculations.v1",
    "ackDeadlineSeconds": 120,
    "messageRetentionDuration": "604800s"
  }')
echo "$RESPONSE"
if echo "$RESPONSE" | grep -q '"error"'; then
  # Ignore "ALREADY_EXISTS" errors (409) - script is idempotent
  if ! echo "$RESPONSE" | grep -q '"ALREADY_EXISTS"'; then
    echo "✗ Failed to create subscription"
    FAILED=1
  fi
fi

# Topic: compliance.events.v1
echo ">>> Creating topic: compliance.events.v1"
curl -s -X PUT \
  "http://${PUBSUB_EMULATOR_HOST}/v1/projects/${PROJECT_ID}/topics/compliance.events.v1" \
  -H "Content-Type: application/json"

# Subscription: compliance-monitor-consumer
echo ">>> Creating subscription: compliance-monitor-consumer"
RESPONSE=$(curl -s -X PUT \
  "http://${PUBSUB_EMULATOR_HOST}/v1/projects/${PROJECT_ID}/subscriptions/compliance-monitor-consumer" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "projects/'${PROJECT_ID}'/topics/compliance.events.v1",
    "ackDeadlineSeconds": 60,
    "messageRetentionDuration": "604800s"
  }')
echo "$RESPONSE"
if echo "$RESPONSE" | grep -q '"error"'; then
  # Ignore "ALREADY_EXISTS" errors (409) - script is idempotent
  if ! echo "$RESPONSE" | grep -q '"ALREADY_EXISTS"'; then
    echo "✗ Failed to create subscription"
    FAILED=1
  fi
fi

echo ""
if [ $FAILED -eq 1 ]; then
  echo "===================================="
  echo "⚠️  Pub/Sub Initialization Failed"
  echo "===================================="
  echo ""
  echo "Some resources failed to create."
  echo "Check the errors above for details."
  echo ""
  exit 1
else
  echo "===================================="
  echo "✓ Pub/Sub Emulator Initialized"
  echo "===================================="
  echo ""
  echo "Topics created:"
  echo "  - settlement.events.v1"
  echo "  - risk.calculations.v1"
  echo "  - compliance.events.v1"
  echo ""
  echo "Subscriptions created:"
  echo "  - settlement-events-consumer"
  echo "  - risk-analytics-consumer"
  echo "  - compliance-monitor-consumer"
  echo ""
  echo "Ready for local development!"
fi

