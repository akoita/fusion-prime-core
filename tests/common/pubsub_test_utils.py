"""
Pub/Sub Test Utilities

Provides utilities for testing Pub/Sub message flows in integration tests.
Supports both GCP Pub/Sub and local emulator.
"""

import json
import os
import time
from typing import Any, Dict, List, Optional

from google.api_core import exceptions
from google.cloud import pubsub_v1


def pull_messages(
    project_id: str, subscription_id: str, max_messages: int = 10, timeout: int = 10
) -> List[Dict[str, Any]]:
    """
    Pull messages from a Pub/Sub subscription.

    Args:
        project_id: GCP project ID
        subscription_id: Subscription ID to pull from
        max_messages: Maximum number of messages to pull
        timeout: Timeout in seconds

    Returns:
        List of message dictionaries with 'data', 'attributes', 'message_id'

    Example:
        messages = pull_messages(
            "fusion-prime-local",
            "settlement-events-consumer",
            max_messages=10
        )
        for msg in messages:
            print(f"Message: {msg['data']}")
    """
    # Use emulator if configured
    if os.getenv("PUBSUB_EMULATOR_HOST"):
        os.environ["PUBSUB_EMULATOR_HOST"] = os.getenv("PUBSUB_EMULATOR_HOST")

    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_id)

    messages = []

    try:
        # Pull messages
        response = subscriber.pull(
            request={
                "subscription": subscription_path,
                "max_messages": max_messages,
            },
            timeout=timeout,
        )

        # Extract message data
        for received_message in response.received_messages:
            msg_data = received_message.message.data.decode("utf-8")
            try:
                parsed_data = json.loads(msg_data)
            except json.JSONDecodeError:
                parsed_data = msg_data

            messages.append(
                {
                    "data": parsed_data,
                    "attributes": dict(received_message.message.attributes),
                    "message_id": received_message.message.message_id,
                    "ack_id": received_message.ack_id,
                }
            )

        # Acknowledge messages
        if messages:
            ack_ids = [msg["ack_id"] for msg in messages]
            subscriber.acknowledge(request={"subscription": subscription_path, "ack_ids": ack_ids})

    except exceptions.DeadlineExceeded:
        # No messages available - this is okay
        pass
    except Exception as e:
        print(f"⚠️  Error pulling messages: {e}")

    return messages


def find_message_by_attribute(
    messages: List[Dict[str, Any]], attribute_key: str, attribute_value: str
) -> Optional[Dict[str, Any]]:
    """
    Find a message by attribute value.

    Args:
        messages: List of messages from pull_messages()
        attribute_key: Attribute key to match
        attribute_value: Attribute value to match

    Returns:
        First matching message or None

    Example:
        msg = find_message_by_attribute(
            messages,
            "escrow_address",
            "0x123..."
        )
    """
    for msg in messages:
        if msg.get("attributes", {}).get(attribute_key) == attribute_value:
            return msg
    return None


def find_message_by_content(
    messages: List[Dict[str, Any]], search_key: str, search_value: Any
) -> Optional[Dict[str, Any]]:
    """
    Find a message by content (data field).

    Args:
        messages: List of messages from pull_messages()
        search_key: Key to search in message data
        search_value: Value to match

    Returns:
        First matching message or None

    Example:
        msg = find_message_by_content(
            messages,
            "escrow_address",
            "0x123..."
        )
    """
    for msg in messages:
        if isinstance(msg["data"], dict):
            if msg["data"].get(search_key) == search_value:
                return msg
    return None


def wait_for_message(
    project_id: str,
    subscription_id: str,
    check_fn: callable,
    timeout: int = 180,
    poll_interval: int = 2,
) -> Optional[Dict[str, Any]]:
    """
    Wait for a specific message to appear in subscription.

    Args:
        project_id: GCP project ID
        subscription_id: Subscription ID
        check_fn: Function that takes a message and returns True if it matches
        timeout: Maximum wait time in seconds
        poll_interval: Time between polls in seconds

    Returns:
        Matching message or None if timeout

    Example:
        msg = wait_for_message(
            "fusion-prime-local",
            "settlement-events-consumer",
            lambda msg: msg['data'].get('escrow_address') == expected_address,
            timeout=30
        )
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        messages = pull_messages(project_id, subscription_id, max_messages=10)

        for msg in messages:
            if check_fn(msg):
                return msg

        time.sleep(poll_interval)

    return None


def verify_event_published(
    project_id: str, subscription_id: str, event_type: str, escrow_address: str, timeout: int = 180
) -> bool:
    """
    Verify that a specific event was published for an escrow.

    Args:
        project_id: GCP project ID
        subscription_id: Subscription ID to check
        event_type: Event type to look for (e.g., "EscrowDeployed")
        escrow_address: Escrow address to match
        timeout: Maximum wait time in seconds

    Returns:
        True if event found, False if timeout

    Example:
        found = verify_event_published(
            "fusion-prime-local",
            "settlement-events-consumer",
            "EscrowDeployed",
            "0x123...",
            timeout=30
        )
    """
    print(f"🔍 Waiting for {event_type} event for {escrow_address}...")

    def check_message(msg):
        data = msg.get("data", {})
        if isinstance(data, dict):
            # Check event type
            if data.get("event_type") != event_type and data.get("type") != event_type:
                return False
            # Check escrow address
            return (
                data.get("escrow_address") == escrow_address
                or data.get("escrow") == escrow_address
                or data.get("address") == escrow_address
            )
        return False

    message = wait_for_message(project_id, subscription_id, check_message, timeout=timeout)

    if message:
        print(f"✅ Found {event_type} event in Pub/Sub")
        print(f"   Message ID: {message['message_id']}")
        return True
    else:
        print(f"❌ {event_type} event not found in Pub/Sub (timeout: {timeout}s)")
        return False


def create_test_subscription(project_id: str, topic_id: str, subscription_id: str) -> str:
    """
    Create a temporary subscription for testing.

    Args:
        project_id: GCP project ID
        topic_id: Topic ID to subscribe to
        subscription_id: Subscription ID to create

    Returns:
        Subscription path

    Example:
        sub_path = create_test_subscription(
            "fusion-prime-local",
            "settlement.events.v1",
            "test-sub-123"
        )
    """
    subscriber = pubsub_v1.SubscriberClient()
    publisher = pubsub_v1.PublisherClient()

    topic_path = publisher.topic_path(project_id, topic_id)
    subscription_path = subscriber.subscription_path(project_id, subscription_id)

    try:
        subscriber.create_subscription(
            request={"name": subscription_path, "topic": topic_path, "ack_deadline_seconds": 60}
        )
        print(f"✅ Created test subscription: {subscription_id}")
    except exceptions.AlreadyExists:
        print(f"ℹ️  Subscription already exists: {subscription_id}")

    return subscription_path


def delete_test_subscription(project_id: str, subscription_id: str):
    """
    Delete a test subscription.

    Args:
        project_id: GCP project ID
        subscription_id: Subscription ID to delete
    """
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_id)

    try:
        subscriber.delete_subscription(request={"subscription": subscription_path})
        print(f"✅ Deleted test subscription: {subscription_id}")
    except Exception as e:
        print(f"⚠️  Could not delete subscription: {e}")


def purge_subscription(project_id: str, subscription_id: str):
    """
    Pull and acknowledge all messages from a subscription (clean up).

    Args:
        project_id: GCP project ID
        subscription_id: Subscription ID to purge
    """
    print(f"🧹 Purging subscription: {subscription_id}")

    total_purged = 0
    while True:
        messages = pull_messages(project_id, subscription_id, max_messages=100, timeout=5)
        if not messages:
            break
        total_purged += len(messages)

    if total_purged > 0:
        print(f"✅ Purged {total_purged} messages from {subscription_id}")
    else:
        print(f"ℹ️  No messages to purge from {subscription_id}")
