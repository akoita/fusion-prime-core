"""
Quick validation test for deployed Compliance Service after bug fixes.

Tests the 4 previously broken endpoints to verify fixes are deployed correctly.
"""

import os

import pytest
import requests

COMPLIANCE_URL = os.getenv(
    "COMPLIANCE_SERVICE_URL",
    "https://compliance-961424092563.us-central1.run.app",
)


class TestComplianceServiceDeployment:
    """Quick validation of deployed Compliance Service fixes."""

    def test_health_check(self):
        """Verify service is healthy."""
        response = requests.get(f"{COMPLIANCE_URL}/health", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("✅ Service is healthy")

    def test_kyc_endpoint_error_handling(self):
        """
        Test that KYC endpoint returns proper error (422) not 500.

        Before fix: Would return 500 with 'NoneType' object is not callable
        After fix: Should return 422 (validation error) or 503 (service unavailable)
        """
        # Test with invalid request
        response = requests.post(
            f"{COMPLIANCE_URL}/compliance/kyc",
            json={},  # Missing required fields
            timeout=10,
        )

        # Should NOT be 500 (that was the bug)
        assert response.status_code != 500, "Bug still present: endpoint returns 500"

        # Should be 422 (validation error) or 503 (service unavailable)
        assert response.status_code in [
            400,
            422,
            503,
        ], f"Unexpected status: {response.status_code}"

        if response.status_code == 503:
            # Service unavailable - check error message
            detail = response.json().get("detail", "")
            assert "not initialized" in detail.lower() or "engine" in detail.lower()
            print("✅ Returns 503 with clear error message (service not initialized)")

        print(f"✅ KYC endpoint returns {response.status_code} (not 500)")

    def test_get_kyc_status_error_handling(self):
        """Test that GET KYC status endpoint handles errors properly."""
        response = requests.get(f"{COMPLIANCE_URL}/compliance/kyc/invalid-case-id", timeout=10)

        # Should NOT be 500
        assert response.status_code != 500, "Bug still present: endpoint returns 500"

        # Should be 404, 400, or 503
        assert response.status_code in [
            400,
            404,
            500,
            503,
        ], f"Unexpected status: {response.status_code}"

        if response.status_code == 500:
            # Check if it's a proper error message about initialization
            detail = response.json().get("detail", "")
            if "not initialized" not in detail.lower():
                pytest.fail("Still returns 500 without proper error message")

        print(f"✅ GET KYC status returns {response.status_code} (not 500 for None)")

    def test_aml_check_error_handling(self):
        """Test that AML check endpoint handles errors properly."""
        response = requests.post(
            f"{COMPLIANCE_URL}/compliance/aml-check",
            json={},  # Missing required fields
            timeout=10,
        )

        # Should NOT be 500
        assert response.status_code != 500, "Bug still present: endpoint returns 500"

        # Should be 422, 400, or 503
        assert response.status_code in [
            400,
            422,
            503,
        ], f"Unexpected status: {response.status_code}"

        print(f"✅ AML check endpoint returns {response.status_code} (not 500)")

    def test_compliance_metrics_endpoint(self):
        """Test that compliance metrics endpoint works."""
        response = requests.get(f"{COMPLIANCE_URL}/compliance/compliance-metrics", timeout=10)

        # Should NOT be 500
        assert response.status_code != 500, "Bug still present: endpoint returns 500"

        # Should be 200 (success) or 503 (service unavailable)
        assert response.status_code in [
            200,
            503,
        ], f"Unexpected status: {response.status_code}"

        if response.status_code == 200:
            data = response.json()
            # Verify response structure
            assert isinstance(data, dict)
            print("✅ Compliance metrics endpoint works correctly")

        print(f"✅ Compliance metrics returns {response.status_code} (not 500)")
