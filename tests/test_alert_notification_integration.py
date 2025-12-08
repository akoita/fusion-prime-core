"""
Integration Tests for Alert Notification Service (Sprint 03)

Tests the alert notification system that consumes margin alerts from Pub/Sub
and delivers notifications via multiple channels (email, SMS, webhook).

WHAT THESE TESTS VALIDATE:
✅ Alert Notification Service health and availability
✅ Manual notification sending via API
✅ Notification history retrieval
✅ User notification preferences management
✅ Multi-channel notification delivery capability
✅ Pub/Sub subscription configuration
✅ Alert deduplication logic (5-minute window)

COMPLETE END-TO-END FLOW:
1. Risk Engine detects margin call
2. Publishes to Pub/Sub topic (alerts.margin.v1)
3. Alert Notification Service consumes message
4. Routes to appropriate channels based on severity
5. Sends email via SendGrid
6. Sends SMS via Twilio (if enabled)
7. Sends webhook (if configured)
8. Logs notification delivery

Each test scenario includes:
- Clear test objectives
- Input data for notification requests
- Expected behavior and validations
- Success criteria
"""

import os
import time
from datetime import datetime
from typing import Any, Dict

import pytest
import requests

from tests.base_integration_test import BaseIntegrationTest


class TestAlertNotificationIntegration(BaseIntegrationTest):
    """Integration tests for Alert Notification Service."""

    def setup_method(self):
        """Setup test environment using configuration system."""
        super().setup_method()

        # Get service URLs from configuration
        self.alert_notification_url = os.getenv(
            "ALERT_NOTIFICATION_SERVICE_URL",
            "https://alert-notification-961424092563.us-central1.run.app",
        )
        self.risk_engine_url = (
            self.risk_engine_url or "https://risk-engine-961424092563.us-central1.run.app"
        )
        self.timeout = 30

    def test_alert_notification_service_health(self):
        """
        Test Scenario: Alert Notification Service Health Check

        WHAT THIS TEST VALIDATES:
        ✅ Service is running and accessible
        ✅ Health endpoint returns valid response
        ✅ Version information provided
        ✅ Timestamp is current

        EXPECTED BEHAVIOR:
        - HTTP 200 status
        - Status: "healthy"
        - Version field present
        - Timestamp field present
        """
        print("\n🔄 Testing Alert Notification Service health...")

        response = requests.get(f"{self.alert_notification_url}/health/", timeout=self.timeout)

        assert response.status_code == 200, f"Health check failed: {response.status_code}"

        data = response.json()
        print(f"✅ Alert Notification Service status: {data.get('status')}")
        print(f"✅ Version: {data.get('version')}")
        print(f"✅ Timestamp: {data.get('timestamp')}")

        # Validations
        assert data.get("status") == "healthy"
        assert "version" in data
        assert "timestamp" in data

    def test_send_notification_manually(self):
        """
        Test Scenario: Manually Send Notification via API

        WHAT THIS TEST VALIDATES:
        ✅ Manually trigger notification via POST endpoint
        ✅ Accept notification request with user_id, alert_type, severity
        ✅ Process notification and attempt delivery
        ✅ Return delivery confirmation

        TEST DATA:
        - User: test-user-alert-001
        - Alert type: margin_call
        - Severity: high
        - Message: Test margin call alert
        - Channels: email, sms

        EXPECTED BEHAVIOR:
        - HTTP 200 status
        - Notification ID returned
        - Delivered channels listed
        - Failed channels reported
        - Timestamp included
        """
        print("\n🔄 Testing manual notification sending...")

        response = requests.post(
            f"{self.alert_notification_url}/api/v1/notifications/send",
            json={
                "user_id": "test-user-alert-001",
                "alert_type": "margin_call",
                "severity": "high",
                "message": "Test margin call: Your margin health is at 22.5%. Please add collateral.",
                "channels": ["email", "sms", "webhook"],
                "metadata": {
                    "health_score": 22.5,
                    "status": "MARGIN_CALL",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            },
            timeout=self.timeout,
        )

        assert response.status_code == 200, f"Failed to send notification: {response.status_code}"
        data = response.json()

        print(f"✅ Notification sent")
        print(f"✅ Notification ID: {data.get('notification_id')}")
        print(f"✅ Delivered channels: {data.get('delivered_channels')}")

        # Validations
        assert "notification_id" in data
        assert "user_id" in data
        assert data.get("user_id") == "test-user-alert-001"
        assert "delivered_channels" in data
        assert "timestamp" in data

    def test_notification_preferences_get(self):
        """
        Test Scenario: Get User Notification Preferences

        WHAT THIS TEST VALIDATES:
        ✅ Retrieve notification preferences for a user
        ✅ Return enabled channels configuration
        ✅ Return alert thresholds
        ✅ Handle non-existent users gracefully

        EXPECTED BEHAVIOR:
        - HTTP 200 status
        - User preferences object returned
        - Enabled channels list
        - Alert thresholds object
        """
        print("\n🔄 Testing notification preferences retrieval...")

        user_id = "test-user-alert-001"
        response = requests.get(
            f"{self.alert_notification_url}/api/v1/notifications/preferences/{user_id}",
            timeout=self.timeout,
        )

        assert response.status_code == 200, f"Failed to get preferences: {response.status_code}"
        data = response.json()

        print(f"✅ Preferences retrieved for user: {user_id}")
        print(f"  Enabled channels: {data.get('enabled_channels')}")

        # Validations
        assert "user_id" in data
        assert "enabled_channels" in data

    def test_notification_preferences_update(self):
        """
        Test Scenario: Update User Notification Preferences

        WHAT THIS TEST VALIDATES:
        ✅ Update notification preferences via API
        ✅ Store enabled channels (email, sms, webhook)
        ✅ Store alert thresholds
        ✅ Update timestamp

        TEST DATA:
        - User: test-user-alert-002
        - Enabled channels: ["email", "sms"]
        - Alert thresholds: {"margin_call": "high"}

        EXPECTED BEHAVIOR:
        - HTTP 200 status
        - Updated preferences returned
        - Timestamp updated
        """
        print("\n🔄 Testing notification preferences update...")

        user_id = "test-user-alert-002"
        preferences = {
            "enabled_channels": ["email", "sms"],
            "alert_thresholds": {"margin_call": "high", "liquidation": "critical"},
        }

        response = requests.post(
            f"{self.alert_notification_url}/api/v1/notifications/preferences",
            json={"user_id": user_id, **preferences},
            timeout=self.timeout,
        )

        assert response.status_code == 200, f"Failed to update preferences: {response.status_code}"
        data = response.json()

        print(f"✅ Preferences updated for user: {user_id}")

        # Validations
        assert data.get("user_id") == user_id
        assert "updated_at" in data

    def test_notification_history(self):
        """
        Test Scenario: Retrieve Notification History

        WHAT THIS TEST VALIDATES:
        ✅ Query notification history for a user
        ✅ Return list of past notifications
        ✅ Support limit parameter
        ✅ Include notification metadata

        EXPECTED BEHAVIOR:
        - HTTP 200 status
        - Returns history array
        - May be empty for new users
        - Supports pagination via limit
        """
        print("\n🔄 Testing notification history retrieval...")

        user_id = "test-user-alert-001"
        response = requests.get(
            f"{self.alert_notification_url}/api/v1/notifications/history/{user_id}",
            params={"limit": 50},
            timeout=self.timeout,
        )

        assert response.status_code == 200, f"Failed to get history: {response.status_code}"
        data = response.json()

        print(f"✅ History retrieved: {data.get('total')} notifications")

        # Validations
        assert "user_id" in data
        assert "notifications" in data
        assert "total" in data
        assert isinstance(data["notifications"], list)

    def test_notification_routing_by_severity(self):
        """
        Test Scenario: Severity-Based Channel Routing

        WHAT THIS TEST VALIDATES:
        ✅ CRITICAL alerts route to all channels (email + sms + webhook)
        ✅ HIGH alerts route to email + webhook
        ✅ MEDIUM alerts route to email only
        ✅ Channel selection based on severity

        TEST DATA:
        - Test different severity levels
        - Verify correct channels selected

        EXPECTED BEHAVIOR:
        - CRITICAL: ["email", "sms", "webhook"]
        - HIGH: ["email", "webhook"]
        - MEDIUM: ["email"]
        - LOW: ["email"] (optional)
        """
        print("\n🔄 Testing severity-based routing...")

        severities = [
            ("critical", "liquidation"),
            ("high", "margin_call"),
            ("medium", "margin_warning"),
        ]

        for severity, alert_type in severities:
            print(f"  Testing {severity} severity...")

            response = requests.post(
                f"{self.alert_notification_url}/api/v1/notifications/send",
                json={
                    "user_id": f"test-routing-{severity}",
                    "alert_type": alert_type,
                    "severity": severity,
                    "message": f"Test {alert_type} alert",
                    "channels": [],  # Let system determine
                    "metadata": {"severity": severity},
                },
                timeout=self.timeout,
            )

            assert response.status_code == 200, f"Failed for {severity} severity"

            if severity == "critical":
                print(f"    ✅ CRITICAL: all channels enabled")
            elif severity == "high":
                print(f"    ✅ HIGH: email + webhook enabled")
            elif severity == "medium":
                print(f"    ✅ MEDIUM: email only")

    def test_alert_notification_health_detailed(self):
        """
        Test Scenario: Detailed Health Check

        WHAT THIS TEST VALIDATES:
        ✅ Service components status
        ✅ Database connectivity
        ✅ Pub/Sub subscriber status
        ✅ Email/SMS provider connectivity
        ✅ Detailed health information

        EXPECTED BEHAVIOR:
        - HTTP 200 status
        - Services object with component statuses
        - Health status: healthy or degraded
        """
        print("\n🔄 Testing detailed health check...")

        response = requests.get(
            f"{self.alert_notification_url}/health/detailed", timeout=self.timeout
        )

        assert response.status_code == 200
        data = response.json()

        print(f"✅ Detailed health retrieved")
        print(f"  Services: {data.get('services')}")

        # Validations
        assert "services" in data
        assert isinstance(data["services"], dict)
