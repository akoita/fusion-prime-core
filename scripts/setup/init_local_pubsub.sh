#!/bin/bash
# Initialize local Pub/Sub emulator with required topics and subscriptions

set -e

echo "🔧 Initializing Local Pub/Sub Emulator..."

# Set emulator host
export PUBSUB_EMULATOR_HOST="${PUBSUB_EMULATOR_HOST:-localhost:8085}"
export GCP_PROJECT="${GCP_PROJECT:-fusion-prime-local}"

echo "   Emulator Host: $PUBSUB_EMULATOR_HOST"
echo "   Project: $GCP_PROJECT"

# Wait for emulator to be ready
echo "⏳ Waiting for Pub/Sub emulator to be ready..."
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -s "http://${PUBSUB_EMULATOR_HOST//:8085/:8085}/v1/projects/${GCP_PROJECT}" > /dev/null 2>&1; then
        echo "✅ Pub/Sub emulator is ready"
        break
    fi
    attempt=$((attempt + 1))
    sleep 1
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ Pub/Sub emulator not ready after ${max_attempts}s"
    exit 1
fi

# Create settlement events topic
echo "📤 Creating topic: settlement.events.v1"
gcloud pubsub topics create settlement.events.v1 \
    --project="$GCP_PROJECT" \
    2>/dev/null || echo "   ℹ️  Topic already exists"

# Create subscription for Settlement service
echo "📥 Creating subscription: settlement-events-consumer"
gcloud pubsub subscriptions create settlement-events-consumer \
    --topic=settlement.events.v1 \
    --project="$GCP_PROJECT" \
    --ack-deadline=60 \
    2>/dev/null || echo "   ℹ️  Subscription already exists"

# Create subscription for test suite
echo "📥 Creating subscription: test-events-consumer"
gcloud pubsub subscriptions create test-events-consumer \
    --topic=settlement.events.v1 \
    --project="$GCP_PROJECT" \
    --ack-deadline=60 \
    2>/dev/null || echo "   ℹ️  Subscription already exists"

echo ""
echo "✅ Pub/Sub Initialization Complete!"
echo ""
echo "📊 Summary:"
echo "   Topic: settlement.events.v1"
echo "   Subscriptions:"
echo "     - settlement-events-consumer (for Settlement service)"
echo "     - test-events-consumer (for integration tests)"
echo ""
echo "🧪 To verify:"
echo "   gcloud pubsub topics list --project=$GCP_PROJECT"
echo "   gcloud pubsub subscriptions list --project=$GCP_PROJECT"
