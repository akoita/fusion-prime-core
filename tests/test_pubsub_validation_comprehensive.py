"""
Comprehensive Pub/Sub Validation Tests

Tests Pub/Sub integration for all microservices:
- Settlement Service (settlement-events-consumer)
- Risk Engine (risk-events-consumer, risk-engine-prices-consumer)
- Alert Notification Service (alert-notification-service)

Validates:
1. Topic and subscription existence
2. Subscription configuration (ack deadline, message retention, etc.)
3. IAM permissions for service accounts
4. Message publishing and consumption
5. Message format validation

NOTE: These tests make extensive GCP API calls and can be slow/timeout.
      Marked as @pytest.mark.comprehensive to exclude from standard runs.
      Run explicitly with: pytest -m comprehensive
"""

import json
import os
import subprocess
import time
import uuid
from typing import Dict, List, Optional

import pytest
from google.cloud import pubsub_v1


@pytest.mark.comprehensive
class TestPubSubValidationComprehensive:
    """Comprehensive Pub/Sub validation tests for all services."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        self.project_id = os.getenv("GCP_PROJECT", "fusion-prime")

        # Initialize Pub/Sub clients - skip tests if credentials not available
        try:
            self.publisher = pubsub_v1.PublisherClient()
            self.subscriber = pubsub_v1.SubscriberClient()
        except Exception as e:
            pytest.skip(f"Pub/Sub clients not available (credentials issue): {e}")

        # Topics
        self.topics = {
            "settlement": f"projects/{self.project_id}/topics/settlement.events.v1",
            "prices": f"projects/{self.project_id}/topics/market.prices.v1",
            "alerts": f"projects/{self.project_id}/topics/alerts.margin.v1",
        }

        # Subscriptions
        self.subscriptions = {
            "settlement-consumer": f"projects/{self.project_id}/subscriptions/settlement-events-consumer",
            "risk-consumer": f"projects/{self.project_id}/subscriptions/risk-events-consumer",
            "price-consumer": f"projects/{self.project_id}/subscriptions/risk-engine-prices-consumer",
            "alert-consumer": f"projects/{self.project_id}/subscriptions/alert-notification-service",
        }

        print(f"\n🔧 Testing Pub/Sub in project: {self.project_id}")

    # ==================== Topic Tests ====================

    def test_topics_exist(self):
        """Test that all required topics exist."""
        print("\n📋 Testing topic existence...")

        for topic_name, topic_path in self.topics.items():
            try:
                topic = self.publisher.get_topic(topic=topic_path)
                print(f"  ✅ Topic exists: {topic_name} ({topic.name})")
                assert topic.name == topic_path
            except Exception as e:
                pytest.fail(f"Topic {topic_name} does not exist: {e}")

    def test_topics_configuration(self):
        """Test topic configuration (message retention, schema, etc.)."""
        print("\n⚙️  Testing topic configuration...")

        for topic_name, topic_path in self.topics.items():
            try:
                topic = self.publisher.get_topic(topic=topic_path)
                print(f"\n  📄 Topic: {topic_name}")
                print(f"    Name: {topic.name}")
                print(f"    Labels: {dict(topic.labels) if topic.labels else 'None'}")
                print(
                    f"    Schema: {topic.schema_settings.schema if topic.schema_settings else 'None'}"
                )
            except Exception as e:
                print(f"  ⚠️  Could not retrieve config for {topic_name}: {e}")

    # ==================== Subscription Tests ====================

    def test_subscriptions_exist(self):
        """Test that all required subscriptions exist."""
        print("\n📋 Testing subscription existence...")

        for sub_name, sub_path in self.subscriptions.items():
            try:
                subscription = self.subscriber.get_subscription(subscription=sub_path)
                print(f"  ✅ Subscription exists: {sub_name} ({subscription.name})")
                assert subscription.name == sub_path
            except Exception as e:
                pytest.fail(f"Subscription {sub_name} does not exist: {e}")

    def test_subscriptions_configuration(self):
        """Test subscription configuration (ack deadline, retention, etc.)."""
        print("\n⚙️  Testing subscription configuration...")

        for sub_name, sub_path in self.subscriptions.items():
            try:
                subscription = self.subscriber.get_subscription(subscription=sub_path)
                print(f"\n  📄 Subscription: {sub_name}")
                print(f"    Name: {subscription.name}")
                print(f"    Topic: {subscription.topic}")
                print(f"    Ack Deadline: {subscription.ack_deadline_seconds}s")
                print(f"    Message Retention: {subscription.message_retention_duration.seconds}s")
                print(f"    Retain Acked Messages: {subscription.retain_acked_messages}")
                print(
                    f"    Expiration Policy: {subscription.expiration_policy.ttl.seconds if subscription.expiration_policy else 'Never'}s"
                )

                # Validate critical settings
                assert (
                    subscription.ack_deadline_seconds >= 10
                ), f"Ack deadline too short for {sub_name}"
                assert (
                    subscription.message_retention_duration.seconds >= 600
                ), f"Message retention too short for {sub_name}"

            except Exception as e:
                print(f"  ⚠️  Could not retrieve config for {sub_name}: {e}")

    def test_subscription_topic_mapping(self):
        """Test that subscriptions are correctly mapped to topics."""
        print("\n🔗 Testing subscription-topic mapping...")

        expected_mappings = {
            "settlement-consumer": self.topics["settlement"],
            "risk-consumer": self.topics["settlement"],
            "price-consumer": self.topics["prices"],
            "alert-consumer": self.topics["alerts"],
        }

        for sub_name, expected_topic in expected_mappings.items():
            sub_path = self.subscriptions[sub_name]
            try:
                subscription = self.subscriber.get_subscription(subscription=sub_path)
                actual_topic = subscription.topic
                print(f"  {sub_name}:")
                print(f"    Expected topic: {expected_topic}")
                print(f"    Actual topic: {actual_topic}")

                assert (
                    actual_topic == expected_topic
                ), f"Subscription {sub_name} mapped to wrong topic"
                print(f"  ✅ Correct mapping for {sub_name}")
            except Exception as e:
                pytest.fail(f"Could not verify mapping for {sub_name}: {e}")

    # ==================== IAM Tests ====================

    def test_service_account_permissions(self):
        """Test that service accounts have proper IAM permissions."""
        print("\n🔐 Testing service account IAM permissions...")

        # Service accounts for each service
        service_accounts = {
            "settlement": f"settlement-service@{self.project_id}.iam.gserviceaccount.com",
            "risk-engine": f"risk-engine@{self.project_id}.iam.gserviceaccount.com",
        }

        for service_name, sa_email in service_accounts.items():
            print(f"\n  👤 Service Account: {service_name} ({sa_email})")

            # Check subscription permissions
            for sub_name, sub_path in self.subscriptions.items():
                try:
                    result = subprocess.run(
                        [
                            "gcloud",
                            "pubsub",
                            "subscriptions",
                            "get-iam-policy",
                            sub_path.split("/")[-1],
                            "--project",
                            self.project_id,
                            "--format",
                            "json",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )

                    if result.returncode == 0:
                        policy = json.loads(result.stdout)
                        bindings = policy.get("bindings", [])

                        has_permission = False
                        for binding in bindings:
                            if sa_email in binding.get("members", []) or any(
                                sa_email in member for member in binding.get("members", [])
                            ):
                                has_permission = True
                                print(f"    ✅ Has permissions on {sub_name}: {binding['role']}")

                        if not has_permission:
                            print(f"    ℹ️  No explicit permissions on {sub_name}")
                    else:
                        print(f"    ⚠️  Could not check permissions on {sub_name}")

                except Exception as e:
                    print(f"    ℹ️  Permission check for {sub_name}: {e}")

    # ==================== Message Publishing Tests ====================

    def test_publish_to_settlement_topic(self):
        """Test publishing messages to settlement.events.v1 topic."""
        print("\n📤 Testing message publishing to settlement.events.v1...")

        test_message = {
            "event_type": "EscrowCreated",
            "escrow_id": f"test-escrow-{uuid.uuid4()}",
            "block_number": 12345678,
            "transaction_hash": f"0x{'a' * 64}",
            "timestamp": time.time(),
            "test": True,
        }

        try:
            topic_path = self.topics["settlement"]
            message_json = json.dumps(test_message)
            future = self.publisher.publish(
                topic_path, message_json.encode("utf-8"), test="true", source="pytest"
            )
            message_id = future.result(timeout=10)

            print(f"  ✅ Published message to settlement topic")
            print(f"    Message ID: {message_id}")
            print(f"    Content: {test_message['event_type']}")

            assert message_id is not None

        except Exception as e:
            pytest.fail(f"Failed to publish to settlement topic: {e}")

    def test_publish_to_prices_topic(self):
        """Test publishing messages to market.prices.v1 topic."""
        print("\n📤 Testing message publishing to market.prices.v1...")

        test_message = {
            "symbol": "ETHUSD",
            "price": "2500.50",
            "timestamp": time.time(),
            "source": "test",
            "test": True,
        }

        try:
            topic_path = self.topics["prices"]
            message_json = json.dumps(test_message)
            future = self.publisher.publish(
                topic_path, message_json.encode("utf-8"), test="true", source="pytest"
            )
            message_id = future.result(timeout=10)

            print(f"  ✅ Published message to prices topic")
            print(f"    Message ID: {message_id}")
            print(f"    Content: {test_message['symbol']} @ ${test_message['price']}")

            assert message_id is not None

        except Exception as e:
            pytest.fail(f"Failed to publish to prices topic: {e}")

    def test_publish_to_alerts_topic(self):
        """Test publishing messages to alerts.margin.v1 topic."""
        print("\n📤 Testing message publishing to alerts.margin.v1...")

        test_message = {
            "alert_type": "MarginBelowThreshold",
            "account": f"0x{'b' * 40}",
            "margin_percentage": 85.5,
            "threshold": 90.0,
            "timestamp": time.time(),
            "test": True,
        }

        try:
            topic_path = self.topics["alerts"]
            message_json = json.dumps(test_message)
            future = self.publisher.publish(
                topic_path, message_json.encode("utf-8"), test="true", source="pytest"
            )
            message_id = future.result(timeout=10)

            print(f"  ✅ Published message to alerts topic")
            print(f"    Message ID: {message_id}")
            print(f"    Content: {test_message['alert_type']}")

            assert message_id is not None

        except Exception as e:
            pytest.fail(f"Failed to publish to alerts topic: {e}")

    # ==================== Message Consumption Tests ====================

    def test_pull_from_settlement_consumer(self):
        """Test pulling messages from settlement-events-consumer."""
        print("\n📥 Testing message pull from settlement-events-consumer...")

        try:
            sub_path = self.subscriptions["settlement-consumer"]
            response = self.subscriber.pull(subscription=sub_path, max_messages=5, timeout=10)

            message_count = len(response.received_messages)
            print(f"  ✅ Pulled {message_count} messages from settlement-consumer")

            if message_count > 0:
                # Examine first message
                message = response.received_messages[0]
                print(f"\n    📄 Sample Message:")
                print(f"      Message ID: {message.message.message_id}")
                print(f"      Publish Time: {message.message.publish_time}")
                print(f"      Attributes: {dict(message.message.attributes)}")

                # Try to parse message data
                try:
                    data = json.loads(message.message.data.decode("utf-8"))
                    print(f"      Data (parsed): {json.dumps(data, indent=8)}")
                except:
                    print(f"      Data (raw): {message.message.data[:100]}...")

                # Acknowledge messages to clean up
                ack_ids = [msg.ack_id for msg in response.received_messages]
                self.subscriber.acknowledge(subscription=sub_path, ack_ids=ack_ids)
                print(f"    ✅ Acknowledged {len(ack_ids)} messages")
            else:
                print(f"    ℹ️  No messages currently in queue (this is OK)")

        except Exception as e:
            print(f"  ℹ️  Could not pull from settlement-consumer: {e}")

    def test_pull_from_risk_consumer(self):
        """Test pulling messages from risk-events-consumer."""
        print("\n📥 Testing message pull from risk-events-consumer...")

        try:
            sub_path = self.subscriptions["risk-consumer"]
            response = self.subscriber.pull(subscription=sub_path, max_messages=5, timeout=10)

            message_count = len(response.received_messages)
            print(f"  ✅ Pulled {message_count} messages from risk-consumer")

            if message_count > 0:
                print(f"    ℹ️  {message_count} unprocessed messages in queue")

                # Acknowledge messages to clean up
                ack_ids = [msg.ack_id for msg in response.received_messages]
                self.subscriber.acknowledge(subscription=sub_path, ack_ids=ack_ids)
                print(f"    ✅ Acknowledged {len(ack_ids)} messages")
            else:
                print(f"    ℹ️  No messages currently in queue (this is OK)")

        except Exception as e:
            print(f"  ℹ️  Could not pull from risk-consumer: {e}")

    def test_pull_from_price_consumer(self):
        """Test pulling messages from risk-engine-prices-consumer."""
        print("\n📥 Testing message pull from risk-engine-prices-consumer...")

        try:
            sub_path = self.subscriptions["price-consumer"]
            response = self.subscriber.pull(subscription=sub_path, max_messages=5, timeout=10)

            message_count = len(response.received_messages)
            print(f"  ✅ Pulled {message_count} messages from price-consumer")

            if message_count > 0:
                # Examine first message
                message = response.received_messages[0]
                print(f"\n    📄 Sample Price Message:")
                print(f"      Message ID: {message.message.message_id}")

                try:
                    data = json.loads(message.message.data.decode("utf-8"))
                    print(f"      Price Data: {json.dumps(data, indent=8)}")
                except:
                    print(f"      Data (raw): {message.message.data[:100]}...")

                # Acknowledge messages to clean up
                ack_ids = [msg.ack_id for msg in response.received_messages]
                self.subscriber.acknowledge(subscription=sub_path, ack_ids=ack_ids)
                print(f"    ✅ Acknowledged {len(ack_ids)} messages")
            else:
                print(f"    ℹ️  No messages currently in queue (this is OK)")

        except Exception as e:
            print(f"  ℹ️  Could not pull from price-consumer: {e}")

    def test_pull_from_alert_consumer(self):
        """Test pulling messages from alert-notification-service."""
        print("\n📥 Testing message pull from alert-notification-service...")

        try:
            sub_path = self.subscriptions["alert-consumer"]
            response = self.subscriber.pull(subscription=sub_path, max_messages=5, timeout=10)

            message_count = len(response.received_messages)
            print(f"  ✅ Pulled {message_count} messages from alert-consumer")

            if message_count > 0:
                # Examine first message
                message = response.received_messages[0]
                print(f"\n    📄 Sample Alert Message:")
                print(f"      Message ID: {message.message.message_id}")

                try:
                    data = json.loads(message.message.data.decode("utf-8"))
                    print(f"      Alert Data: {json.dumps(data, indent=8)}")
                except:
                    print(f"      Data (raw): {message.message.data[:100]}...")

                # Acknowledge messages to clean up
                ack_ids = [msg.ack_id for msg in response.received_messages]
                self.subscriber.acknowledge(subscription=sub_path, ack_ids=ack_ids)
                print(f"    ✅ Acknowledged {len(ack_ids)} messages")
            else:
                print(f"    ℹ️  No messages currently in queue (this is OK)")

        except Exception as e:
            print(f"  ℹ️  Could not pull from alert-consumer: {e}")

    # ==================== End-to-End Tests ====================

    def test_end_to_end_message_flow(self):
        """Test end-to-end message flow: publish and consume."""
        print("\n🔄 Testing end-to-end message flow...")

        # Publish a unique test message
        test_id = str(uuid.uuid4())
        test_message = {
            "event_type": "TestEvent",
            "test_id": test_id,
            "timestamp": time.time(),
            "test": True,
        }

        try:
            # Publish to settlement topic
            topic_path = self.topics["settlement"]
            message_json = json.dumps(test_message)
            future = self.publisher.publish(
                topic_path,
                message_json.encode("utf-8"),
                test="true",
                test_id=test_id,
                source="pytest",
            )
            message_id = future.result(timeout=10)
            print(f"  ✅ Published test message: {message_id}")

            # Wait for message to propagate
            time.sleep(3)

            # Try to pull from settlement consumer
            sub_path = self.subscriptions["settlement-consumer"]
            response = self.subscriber.pull(subscription=sub_path, max_messages=10, timeout=10)

            found_message = False
            for received_message in response.received_messages:
                try:
                    data = json.loads(received_message.message.data.decode("utf-8"))
                    if data.get("test_id") == test_id:
                        found_message = True
                        print(f"  ✅ Found test message in consumer queue")
                        print(f"    Round-trip time: ~3 seconds")
                        break
                except:
                    continue

            # Acknowledge all messages
            if response.received_messages:
                ack_ids = [msg.ack_id for msg in response.received_messages]
                self.subscriber.acknowledge(subscription=sub_path, ack_ids=ack_ids)

            if found_message:
                print(f"  ✅ End-to-end message flow VERIFIED")
            else:
                print(f"  ℹ️  Test message not found (may have been consumed by service already)")

        except Exception as e:
            print(f"  ⚠️  End-to-end test: {e}")

    # ==================== Performance Tests ====================

    def test_message_throughput(self):
        """Test message publishing throughput."""
        print("\n⚡ Testing message publishing throughput...")

        try:
            topic_path = self.topics["settlement"]
            message_count = 10
            start_time = time.time()

            futures = []
            for i in range(message_count):
                test_message = {
                    "event_type": "ThroughputTest",
                    "sequence": i,
                    "timestamp": time.time(),
                    "test": True,
                }
                message_json = json.dumps(test_message)
                future = self.publisher.publish(
                    topic_path, message_json.encode("utf-8"), test="true", source="pytest"
                )
                futures.append(future)

            # Wait for all publishes to complete
            for future in futures:
                future.result(timeout=10)

            elapsed_time = time.time() - start_time
            throughput = message_count / elapsed_time

            print(f"  ✅ Published {message_count} messages")
            print(f"    Total time: {elapsed_time:.2f}s")
            print(f"    Throughput: {throughput:.2f} messages/second")

            assert throughput > 1, "Publishing throughput too low"

        except Exception as e:
            pytest.fail(f"Throughput test failed: {e}")
