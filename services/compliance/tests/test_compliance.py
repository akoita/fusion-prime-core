"""
Unit tests for Compliance Service compliance endpoints.
"""

import pytest
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestComplianceEndpoints:
    """Test compliance endpoints."""

    def test_user_compliance_status(self, client):
        """Test user compliance status endpoint."""
        response = client.get("/compliance/compliance-status/test_user_123")
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data

    def test_kyc_verification(self, client):
        """Test KYC verification endpoint."""
        kyc_data = {
            "user_id": "test_user_123",
            "document_type": "passport",
            "document_data": {"number": "A1234567", "country": "US"},
            "personal_info": {"name": "John Doe", "dob": "1990-01-01"},
        }
        response = client.post("/compliance/kyc", json=kyc_data)
        assert response.status_code == 200
        data = response.json()
        assert "case_id" in data
        assert "user_id" in data
        assert "status" in data

    def test_aml_check(self, client):
        """Test AML check endpoint."""
        aml_data = {
            "user_id": "test_user_123",
            "transaction_amount": 1000.0,
            "transaction_type": "transfer",
            "source_address": "0x1234567890123456789012345678901234567890",
            "destination_address": "0x9876543210987654321098765432109876543210",
        }
        response = client.post("/compliance/aml-check", json=aml_data)
        assert response.status_code == 200
        data = response.json()
        assert "check_id" in data
        assert "user_id" in data
        assert "risk_level" in data

    def test_sanctions_check(self, client):
        """Test sanctions check endpoint."""
        addresses = ["0x1234567890123456789012345678901234567890"]
        response = client.post("/compliance/sanctions-check", json=addresses)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_compliance_cases(self, client):
        """Test compliance cases endpoint."""
        response = client.get("/compliance/compliance-cases")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
