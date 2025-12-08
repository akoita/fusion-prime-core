"""Tests for webhook management endpoints."""

import os

import pytest
import pytest_asyncio
from app.dependencies import get_engine, init_db
from app.main import app
from httpx import ASGITransport, AsyncClient
from infrastructure.db.models import Base

TEST_DB_URL = "sqlite+aiosqlite:///./test_webhooks.db"


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Setup and teardown test database."""
    init_db(TEST_DB_URL)
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    try:
        os.remove("test_webhooks.db")
    except FileNotFoundError:
        pass


@pytest.mark.asyncio
async def test_create_webhook():
    """Test creating a new webhook subscription."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/webhooks",
            json={
                "url": "https://example.com/webhook",
                "event_types": ["settlement.confirmed", "settlement.failed"],
                "description": "Test webhook",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["url"] == "https://example.com/webhook"
    assert data["event_types"] == ["settlement.confirmed", "settlement.failed"]
    assert data["description"] == "Test webhook"
    assert "subscription_id" in data
    assert "secret" in data
    assert data["enabled"] is True


@pytest.mark.asyncio
async def test_get_webhook():
    """Test retrieving a webhook subscription."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_response = await client.post(
            "/webhooks",
            json={
                "url": "https://example.com/webhook",
                "event_types": ["settlement.confirmed"],
            },
        )
        subscription_id = create_response.json()["subscription_id"]

        response = await client.get(f"/webhooks/{subscription_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["subscription_id"] == subscription_id
    assert data["url"] == "https://example.com/webhook"


@pytest.mark.asyncio
async def test_list_webhooks():
    """Test listing all webhook subscriptions."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            "/webhooks",
            json={
                "url": "https://example.com/webhook1",
                "event_types": ["settlement.confirmed"],
            },
        )
        await client.post(
            "/webhooks",
            json={
                "url": "https://example.com/webhook2",
                "event_types": ["settlement.failed"],
            },
        )

        response = await client.get("/webhooks")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_delete_webhook():
    """Test deleting a webhook subscription."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_response = await client.post(
            "/webhooks",
            json={
                "url": "https://example.com/webhook",
                "event_types": ["settlement.confirmed"],
            },
        )
        subscription_id = create_response.json()["subscription_id"]

        delete_response = await client.delete(f"/webhooks/{subscription_id}")
        assert delete_response.status_code == 204

        get_response = await client.get(f"/webhooks/{subscription_id}")
        assert get_response.status_code == 404
