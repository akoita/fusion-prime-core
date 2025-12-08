"""
Unit tests for Compliance Service identity endpoints.
"""

import pytest
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestIdentityEndpoints:
    """Test identity endpoints."""

    def test_identity_status(self, client):
        """Test identity service status."""
        response = client.get("/identity/identity/test_user_123")
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "kyc_status" in data
        assert "aml_status" in data
        assert "compliance_score" in data

    def test_kyc_verification(self, client):
        """Test KYC verification endpoint."""
        kyc_data = {
            "user_id": "test_user_123",
            "document_type": "passport",
            "document_data": {"number": "A1234567", "country": "US"},
            "personal_info": {"name": "John Doe", "dob": "1990-01-01"},
        }
        response = client.post("/identity/kyc", json=kyc_data)
        assert response.status_code == 200
        data = response.json()
        assert "case_id" in data
        assert "user_id" in data
        assert "status" in data

    def test_kyc_status(self, client):
        """Test KYC status endpoint."""
        response = client.get("/identity/kyc/test_case_123")
        assert response.status_code == 200
        data = response.json()
        assert "case_id" in data
        assert "status" in data
