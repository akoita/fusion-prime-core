#!/usr/bin/env python3
"""Initialize local Pub/Sub emulator with required topics and subscriptions."""

import os
import sys
import time

from google.api_core import exceptions
from google.cloud import pubsub_v1


def wait_for_emulator(max_attempts=30):
    """Wait for Pub/Sub emulator to be ready."""
    print("⏳ Waiting for Pub/Sub emulator to be ready...")

    for attempt in range(max_attempts):
        try:
            publisher = pubsub_v1.PublisherClient()
            # Try to list topics as a health check
            project_path = f"projects/{os.getenv('GCP_PROJECT', 'fusion-prime-local')}"
            list(publisher.list_topics(request={"project": project_path}))
            print("✅ Pub/Sub emulator is ready")
            return True
        except Exception:
            time.sleep(1)

    print(f"❌ Pub/Sub emulator not ready after {max_attempts}s")
    return False


def create_topic(publisher, project_id, topic_id):
    """Create a Pub/Sub topic."""
    topic_path = publisher.topic_path(project_id, topic_id)

    try:
        publisher.create_topic(request={"name": topic_path})
        print(f"✅ Created topic: {topic_id}")
        return True
    except exceptions.AlreadyExists:
        print(f"   ℹ️  Topic already exists: {topic_id}")
        return True
    except Exception as e:
        print(f"❌ Failed to create topic {topic_id}: {e}")
        return False


def create_subscription(subscriber, project_id, topic_id, subscription_id, ack_deadline=60):
    """Create a Pub/Sub subscription."""
    topic_path = subscriber.topic_path(project_id, topic_id)
    subscription_path = subscriber.subscription_path(project_id, subscription_id)

    try:
        subscriber.create_subscription(
            request={
                "name": subscription_path,
                "topic": topic_path,
                "ack_deadline_seconds": ack_deadline,
            }
        )
        print(f"✅ Created subscription: {subscription_id}")
        return True
    except exceptions.AlreadyExists:
        print(f"   ℹ️  Subscription already exists: {subscription_id}")
        return True
    except Exception as e:
        print(f"❌ Failed to create subscription {subscription_id}: {e}")
        return False


def main():
    """Initialize Pub/Sub for local testing."""
    print("🔧 Initializing Local Pub/Sub Emulator...")
    print()

    # Get configuration from environment
    emulator_host = os.getenv("PUBSUB_EMULATOR_HOST", "localhost:8085")
    project_id = os.getenv("GCP_PROJECT", "fusion-prime-local")

    print(f"   Emulator Host: {emulator_host}")
    print(f"   Project: {project_id}")
    print()

    # Ensure emulator host is set
    os.environ["PUBSUB_EMULATOR_HOST"] = emulator_host

    # Wait for emulator
    if not wait_for_emulator():
        sys.exit(1)

    print()

    # Initialize clients
    publisher = pubsub_v1.PublisherClient()
    subscriber = pubsub_v1.SubscriberClient()

    # Create topic
    print("📤 Creating topics...")
    if not create_topic(publisher, project_id, "settlement.events.v1"):
        sys.exit(1)

    print()

    # Create subscriptions
    print("📥 Creating subscriptions...")

    # Subscription for Settlement service
    if not create_subscription(
        subscriber,
        project_id,
        "settlement.events.v1",
        "settlement-events-consumer",
        ack_deadline=60,
    ):
        sys.exit(1)

    # Subscription for integration tests
    if not create_subscription(
        subscriber, project_id, "settlement.events.v1", "test-events-consumer", ack_deadline=60
    ):
        sys.exit(1)

    print()
    print("=" * 60)
    print("✅ Pub/Sub Initialization Complete!")
    print("=" * 60)
    print()
    print("📊 Summary:")
    print(f"   Topic: settlement.events.v1")
    print(f"   Subscriptions:")
    print(f"     - settlement-events-consumer (for Settlement service)")
    print(f"     - test-events-consumer (for integration tests)")
    print()
    print("🧪 To verify in Python:")
    print("   from google.cloud import pubsub_v1")
    print("   subscriber = pubsub_v1.SubscriberClient()")
    print(f"   sub = subscriber.subscription_path('{project_id}', 'settlement-events-consumer')")
    print("   print(subscriber.get_subscription(request={'subscription': sub}))")


if __name__ == "__main__":
    main()
