"""
Integration Tests: Webhook Subscription Feature

Tests the complete webhook subscription workflow including:
1. Creating webhook subscriptions via Settlement Service API
2. Verifying database persistence by retrieving subscriptions
3. Managing subscriptions (list, delete)

WHAT THIS TEST VALIDATES:
✅ Webhook subscription API works end-to-end
✅ webhook_subscriptions table gets populated
✅ Subscriptions can be retrieved and managed
✅ Database persistence is working correctly

These tests exercise the REAL webhook feature, not just data insertion.
"""

import os
import secrets
from typing import Dict

import pytest
import requests


class TestWebhookSubscriptionIntegration:
    """Integration tests for webhook subscription management."""

    def setup_method(self):
        """Setup test environment."""
        # Get Settlement Service URL from env or use default
        self.settlement_url = os.getenv(
            "SETTLEMENT_SERVICE_URL", "https://settlement-service-ggats6pubq-uc.a.run.app"
        )
        self.timeout = 30
        self.created_webhook_ids = []  # Track for cleanup

        print(f"\n🔧 Test Configuration:")
        print(f"  Settlement Service: {self.settlement_url}")

    def teardown_method(self):
        """Cleanup created webhooks."""
        for webhook_id in self.created_webhook_ids:
            try:
                requests.delete(
                    f"{self.settlement_url}/webhooks/{webhook_id}", timeout=self.timeout
                )
            except Exception:
                pass  # Best effort cleanup

    def test_create_webhook_subscription(self):
        """
        Test Scenario: Create Webhook Subscription

        WHAT THIS TEST VALIDATES:
        ✅ POST /webhooks endpoint works
        ✅ Webhook record created in webhook_subscriptions table
        ✅ Returns subscription_id and secret
        ✅ Subscription is enabled by default

        TEST DATA:
        - URL: https://test-webhook-{random}.example.com
        - Event types: ["escrow.created", "escrow.released"]
        - Description: "Integration test webhook"

        EXPECTED BEHAVIOR:
        - HTTP 201 status
        - Valid subscription_id returned
        - Secret generated automatically
        - Subscription enabled=true
        """
        print("\n🔄 Testing webhook subscription creation...")

        # Create unique webhook URL
        webhook_url = f"https://test-webhook-{secrets.token_hex(8)}.example.com"

        response = requests.post(
            f"{self.settlement_url}/webhooks",
            json={
                "url": webhook_url,
                "event_types": ["escrow.created", "escrow.released"],
                "description": "Integration test webhook",
            },
            timeout=self.timeout,
        )

        print(f"  Response status: {response.status_code}")
        assert (
            response.status_code == 201
        ), f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()
        print(f"  ✅ Webhook created: {data.get('subscription_id')}")

        # Validate response structure
        assert "subscription_id" in data, "subscription_id missing from response"
        assert "secret" in data, "secret missing from response"
        # URL may have trailing slash normalized by Pydantic HttpUrl
        assert data["url"].rstrip("/") == webhook_url.rstrip("/"), "URL doesn't match"
        assert data["event_types"] == [
            "escrow.created",
            "escrow.released",
        ], "Event types don't match"
        assert data["enabled"] is True, "Webhook should be enabled by default"
        assert data["description"] == "Integration test webhook", "Description doesn't match"

        # Track for cleanup
        self.created_webhook_ids.append(data["subscription_id"])

        print("  ✅ Webhook subscription created and validated")

    def test_retrieve_webhook_subscription(self):
        """
        Test Scenario: Retrieve Webhook Subscription

        WHAT THIS TEST VALIDATES:
        ✅ GET /webhooks/{id} endpoint works
        ✅ Webhook persisted in database
        ✅ Data retrieved matches what was created

        STEPS:
        1. Create webhook subscription
        2. Retrieve subscription by ID
        3. Verify all fields match

        EXPECTED BEHAVIOR:
        - HTTP 200 status
        - All fields match created subscription
        - Proves database persistence working
        """
        print("\n🔄 Testing webhook subscription retrieval...")

        # Step 1: Create webhook
        webhook_url = f"https://test-webhook-{secrets.token_hex(8)}.example.com"
        create_response = requests.post(
            f"{self.settlement_url}/webhooks",
            json={
                "url": webhook_url,
                "event_types": ["escrow.approved"],
                "description": "Test retrieval webhook",
            },
            timeout=self.timeout,
        )
        assert create_response.status_code == 201
        created_data = create_response.json()
        subscription_id = created_data["subscription_id"]
        self.created_webhook_ids.append(subscription_id)

        print(f"  Created webhook: {subscription_id}")

        # Step 2: Retrieve webhook
        get_response = requests.get(
            f"{self.settlement_url}/webhooks/{subscription_id}", timeout=self.timeout
        )

        print(f"  Response status: {get_response.status_code}")
        assert get_response.status_code == 200, f"Expected 200, got {get_response.status_code}"

        retrieved_data = get_response.json()

        # Step 3: Verify data matches
        assert retrieved_data["subscription_id"] == subscription_id, "Subscription ID doesn't match"
        assert retrieved_data["url"].rstrip("/") == webhook_url.rstrip("/"), "URL doesn't match"
        assert retrieved_data["event_types"] == ["escrow.approved"], "Event types don't match"
        assert (
            retrieved_data["description"] == "Test retrieval webhook"
        ), "Description doesn't match"
        assert retrieved_data["enabled"] is True, "Webhook should be enabled"

        print("  ✅ Webhook retrieved successfully from database")

    def test_list_webhook_subscriptions(self):
        """
        Test Scenario: List All Webhook Subscriptions

        WHAT THIS TEST VALIDATES:
        ✅ GET /webhooks endpoint works
        ✅ Returns list of all subscriptions
        ✅ Multiple webhooks can be stored

        STEPS:
        1. Create 3 webhook subscriptions
        2. List all subscriptions
        3. Verify all created webhooks are in the list

        EXPECTED BEHAVIOR:
        - HTTP 200 status
        - List contains at least our created webhooks
        - Proves multiple webhook persistence
        """
        print("\n🔄 Testing webhook subscription listing...")

        # Step 1: Create 3 webhooks
        created_ids = []
        for i in range(3):
            webhook_url = f"https://test-webhook-{i}-{secrets.token_hex(6)}.example.com"
            response = requests.post(
                f"{self.settlement_url}/webhooks",
                json={
                    "url": webhook_url,
                    "event_types": ["escrow.created"],
                    "description": f"Test webhook {i}",
                },
                timeout=self.timeout,
            )
            assert response.status_code == 201
            webhook_id = response.json()["subscription_id"]
            created_ids.append(webhook_id)
            self.created_webhook_ids.append(webhook_id)

        print(f"  Created {len(created_ids)} webhooks")

        # Step 2: List all webhooks
        list_response = requests.get(f"{self.settlement_url}/webhooks", timeout=self.timeout)

        print(f"  Response status: {list_response.status_code}")
        assert list_response.status_code == 200, f"Expected 200, got {list_response.status_code}"

        webhooks = list_response.json()
        assert isinstance(webhooks, list), "Response should be a list"

        # Step 3: Verify our webhooks are in the list
        webhook_ids_in_list = [w["subscription_id"] for w in webhooks]
        for created_id in created_ids:
            assert created_id in webhook_ids_in_list, f"Webhook {created_id} not found in list"

        print(f"  ✅ Found all {len(created_ids)} webhooks in list")
        print(f"  Total webhooks in system: {len(webhooks)}")

    def test_delete_webhook_subscription(self):
        """
        Test Scenario: Delete Webhook Subscription

        WHAT THIS TEST VALIDATES:
        ✅ DELETE /webhooks/{id} endpoint works
        ✅ Webhook removed from database
        ✅ Subsequent GET returns 404

        STEPS:
        1. Create webhook subscription
        2. Delete the subscription
        3. Try to retrieve (should return 404)

        EXPECTED BEHAVIOR:
        - DELETE returns 204
        - Subsequent GET returns 404
        - Proves deletion from database
        """
        print("\n🔄 Testing webhook subscription deletion...")

        # Step 1: Create webhook
        webhook_url = f"https://test-webhook-{secrets.token_hex(8)}.example.com"
        create_response = requests.post(
            f"{self.settlement_url}/webhooks",
            json={
                "url": webhook_url,
                "event_types": ["escrow.refunded"],
            },
            timeout=self.timeout,
        )
        assert create_response.status_code == 201
        subscription_id = create_response.json()["subscription_id"]

        print(f"  Created webhook: {subscription_id}")

        # Step 2: Delete webhook
        delete_response = requests.delete(
            f"{self.settlement_url}/webhooks/{subscription_id}", timeout=self.timeout
        )

        print(f"  Delete response status: {delete_response.status_code}")
        assert (
            delete_response.status_code == 204
        ), f"Expected 204, got {delete_response.status_code}"

        # Step 3: Try to retrieve (should fail)
        get_response = requests.get(
            f"{self.settlement_url}/webhooks/{subscription_id}", timeout=self.timeout
        )

        print(f"  Get after delete status: {get_response.status_code}")
        assert get_response.status_code == 404, f"Expected 404, got {get_response.status_code}"

        print("  ✅ Webhook deleted successfully from database")

    def test_webhook_subscription_persistence_across_requests(self):
        """
        Test Scenario: Webhook Persistence Across Multiple Requests

        WHAT THIS TEST VALIDATES:
        ✅ Webhook survives multiple API calls
        ✅ Database transactions are committed
        ✅ Data consistency maintained

        STEPS:
        1. Create webhook
        2. Retrieve it 3 times
        3. Verify data is consistent each time

        EXPECTED BEHAVIOR:
        - All retrievals return same data
        - Proves proper database commit
        """
        print("\n🔄 Testing webhook persistence across requests...")

        # Step 1: Create webhook
        webhook_url = f"https://test-webhook-{secrets.token_hex(8)}.example.com"
        create_response = requests.post(
            f"{self.settlement_url}/webhooks",
            json={
                "url": webhook_url,
                "event_types": ["escrow.created", "escrow.released", "escrow.refunded"],
                "description": "Persistence test webhook",
            },
            timeout=self.timeout,
        )
        assert create_response.status_code == 201
        subscription_id = create_response.json()["subscription_id"]
        self.created_webhook_ids.append(subscription_id)

        print(f"  Created webhook: {subscription_id}")

        # Step 2: Retrieve 3 times
        for i in range(3):
            response = requests.get(
                f"{self.settlement_url}/webhooks/{subscription_id}",
                timeout=self.timeout,
            )
            assert response.status_code == 200
            data = response.json()

            # Verify data is consistent
            assert data["subscription_id"] == subscription_id
            assert data["url"].rstrip("/") == webhook_url.rstrip("/")
            assert len(data["event_types"]) == 3
            assert data["description"] == "Persistence test webhook"

            print(f"  Retrieval {i+1}/3: ✅ Data consistent")

        print("  ✅ Webhook data persisted correctly across multiple requests")

    def test_create_webhook_with_multiple_event_types(self):
        """
        Test Scenario: Webhook with Multiple Event Types

        WHAT THIS TEST VALIDATES:
        ✅ JSON array storage in event_types column
        ✅ Multiple event types persisted correctly
        ✅ Event types retrieved in correct order

        TEST DATA:
        - Event types: 5 different escrow events

        EXPECTED BEHAVIOR:
        - All event types stored
        - Retrieved in same order
        - JSON serialization working
        """
        print("\n🔄 Testing webhook with multiple event types...")

        event_types = [
            "escrow.created",
            "escrow.approved",
            "escrow.released",
            "escrow.refunded",
            "escrow.disputed",
        ]

        # Create webhook with multiple events
        webhook_url = f"https://test-webhook-{secrets.token_hex(8)}.example.com"
        create_response = requests.post(
            f"{self.settlement_url}/webhooks",
            json={
                "url": webhook_url,
                "event_types": event_types,
                "description": "Multi-event webhook",
            },
            timeout=self.timeout,
        )
        assert create_response.status_code == 201
        subscription_id = create_response.json()["subscription_id"]
        self.created_webhook_ids.append(subscription_id)

        # Retrieve and verify
        get_response = requests.get(
            f"{self.settlement_url}/webhooks/{subscription_id}", timeout=self.timeout
        )
        assert get_response.status_code == 200
        data = get_response.json()

        assert data["event_types"] == event_types, "Event types don't match"
        print(f"  ✅ All {len(event_types)} event types persisted correctly")
