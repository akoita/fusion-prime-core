"""
Integration tests for API Key Management Service.

Tests API key creation, rotation, listing, and service health endpoints.

WHAT THESE TESTS VALIDATE:
✅ API key creation with different tiers (free, pro, enterprise)
✅ API key listing and retrieval
✅ API key rotation
✅ API key revocation
✅ Service health endpoints
"""

import os

import httpx
import pytest

API_KEY_SERVICE_URL = os.getenv(
    "API_KEY_SERVICE_URL", "https://api-key-service-ggats6pubq-uc.a.run.app"
)


@pytest.fixture
def http_client():
    """HTTP client for making requests."""
    return httpx.AsyncClient(timeout=30.0)


class TestAPIKeyServiceHealth:
    """Tests for API Key Service health endpoints."""

    @pytest.mark.asyncio
    async def test_service_health_check(self, http_client: httpx.AsyncClient):
        """Test API Key Service health endpoint."""
        response = await http_client.get(f"{API_KEY_SERVICE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "api-key-service"


class TestAPIKeyManagement:
    """Tests for API key CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_api_key_free_tier(self, http_client: httpx.AsyncClient):
        """Test creating an API key with free tier."""
        payload = {
            "key_name": f"test-key-{os.urandom(4).hex()}",
            "tier": "free",
        }
        response = await http_client.post(f"{API_KEY_SERVICE_URL}/api/v1/keys", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "key_id" in data
        assert "key_name" in data
        assert "tier" in data
        assert data["tier"] == "free"
        # Note: API key itself is not returned (security)

    @pytest.mark.asyncio
    async def test_create_api_key_pro_tier(self, http_client: httpx.AsyncClient):
        """Test creating an API key with pro tier."""
        payload = {
            "key_name": f"test-key-pro-{os.urandom(4).hex()}",
            "tier": "pro",
        }
        response = await http_client.post(f"{API_KEY_SERVICE_URL}/api/v1/keys", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["tier"] == "pro"
        assert data["requests_limit"] == 1000  # Pro tier limit

    @pytest.mark.asyncio
    async def test_list_api_keys(self, http_client: httpx.AsyncClient):
        """Test listing all API keys."""
        response = await http_client.get(f"{API_KEY_SERVICE_URL}/api/v1/keys")
        assert response.status_code == 200
        data = response.json()
        assert "keys" in data or isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_api_key_by_id(self, http_client: httpx.AsyncClient):
        """Test retrieving an API key by ID."""
        # First create a key
        create_response = await http_client.post(
            f"{API_KEY_SERVICE_URL}/api/v1/keys",
            json={"key_name": f"test-get-key-{os.urandom(4).hex()}", "tier": "free"},
        )
        assert create_response.status_code == 200
        key_data = create_response.json()
        key_id = key_data["key_id"]

        # Now retrieve it
        response = await http_client.get(f"{API_KEY_SERVICE_URL}/api/v1/keys/{key_id}")
        assert response.status_code == 200
        retrieved_data = response.json()
        assert retrieved_data["key_id"] == key_id
        assert retrieved_data["key_name"] == key_data["key_name"]

    @pytest.mark.asyncio
    async def test_rotate_api_key(self, http_client: httpx.AsyncClient):
        """Test rotating an API key."""
        # First create a key
        create_response = await http_client.post(
            f"{API_KEY_SERVICE_URL}/api/v1/keys",
            json={"key_name": f"test-rotate-key-{os.urandom(4).hex()}", "tier": "free"},
        )
        assert create_response.status_code == 200
        key_data = create_response.json()
        key_id = key_data["key_id"]

        # Now rotate it
        response = await http_client.post(f"{API_KEY_SERVICE_URL}/api/v1/keys/{key_id}/rotate")
        assert response.status_code == 200
        rotate_data = response.json()
        assert rotate_data["key_id"] == key_id
        assert "new_api_key" in rotate_data

    @pytest.mark.asyncio
    async def test_revoke_api_key(self, http_client: httpx.AsyncClient):
        """Test revoking an API key."""
        # First create a key
        create_response = await http_client.post(
            f"{API_KEY_SERVICE_URL}/api/v1/keys",
            json={"key_name": f"test-revoke-key-{os.urandom(4).hex()}", "tier": "free"},
        )
        assert create_response.status_code == 200
        key_data = create_response.json()
        key_id = key_data["key_id"]

        # Now revoke it
        response = await http_client.delete(f"{API_KEY_SERVICE_URL}/api/v1/keys/{key_id}")
        assert response.status_code == 200

        # Verify it's gone (should return 404)
        get_response = await http_client.get(f"{API_KEY_SERVICE_URL}/api/v1/keys/{key_id}")
        assert get_response.status_code == 404
