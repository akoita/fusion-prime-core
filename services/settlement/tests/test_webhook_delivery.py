"""Tests for webhook delivery worker."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from infrastructure.webhooks.delivery import (
    DeliveryStatus,
    WebhookDelivery,
    WebhookDeliveryWorker,
)


@pytest_asyncio.fixture
async def worker():
    """Create webhook delivery worker."""
    async with WebhookDeliveryWorker(timeout=1.0, max_retries=3, base_delay=0.1) as w:
        yield w


@pytest.fixture
def sample_delivery():
    """Create sample webhook delivery."""
    return WebhookDelivery(
        delivery_id="test-delivery-123",
        subscription_id="wh_abc123",
        event_type="settlement.confirmed",
        payload=json.dumps({"command_id": "cmd-123", "status": "confirmed"}),
        target_url="https://example.com/webhook",
        secret="test_secret_key",
        max_attempts=3,
    )


@pytest.mark.asyncio
async def test_compute_signature(worker):
    """Test HMAC signature computation."""
    payload = '{"test": "data"}'
    secret = "my_secret"

    signature = worker._compute_signature(payload, secret)

    assert isinstance(signature, str)
    assert len(signature) == 64  # SHA256 hex digest is 64 characters

    # Verify signature is deterministic
    signature2 = worker._compute_signature(payload, secret)
    assert signature == signature2


@pytest.mark.asyncio
async def test_compute_backoff_delay(worker):
    """Test exponential backoff calculation."""
    assert worker._compute_backoff_delay(0) == 0.1  # base_delay
    assert worker._compute_backoff_delay(1) == 0.2
    assert worker._compute_backoff_delay(2) == 0.4
    assert worker._compute_backoff_delay(3) == 0.8


@pytest.mark.asyncio
async def test_successful_delivery(worker, sample_delivery):
    """Test successful webhook delivery."""
    with patch.object(worker._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = "OK"

        status = await worker.deliver(sample_delivery)

        assert status == DeliveryStatus.SUCCESS
        assert sample_delivery.status == DeliveryStatus.SUCCESS
        assert sample_delivery.attempt == 1
        assert sample_delivery.last_error is None

        # Verify request was made with correct headers
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        assert "X-Fusion-Prime-Signature" in call_kwargs["headers"]
        assert call_kwargs["headers"]["X-Fusion-Prime-Event-Type"] == "settlement.confirmed"
        assert call_kwargs["headers"]["X-Fusion-Prime-Delivery-ID"] == "test-delivery-123"


@pytest.mark.asyncio
async def test_failed_delivery_with_retry(worker, sample_delivery):
    """Test failed delivery with retry scheduling."""
    with patch.object(worker._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 500
        mock_post.return_value.text = "Internal Server Error"

        status = await worker.deliver(sample_delivery)

        assert status == DeliveryStatus.FAILED
        assert sample_delivery.status == DeliveryStatus.FAILED
        assert sample_delivery.attempt == 1
        assert "HTTP 500" in sample_delivery.last_error
        assert sample_delivery.next_retry_at is not None


@pytest.mark.asyncio
async def test_delivery_exhausted_retries(worker, sample_delivery):
    """Test delivery with exhausted retries."""
    sample_delivery.attempt = 2  # Set to max_attempts - 1

    with patch.object(worker._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 503
        mock_post.return_value.text = "Service Unavailable"

        status = await worker.deliver(sample_delivery)

        assert status == DeliveryStatus.EXHAUSTED
        assert sample_delivery.status == DeliveryStatus.EXHAUSTED
        assert sample_delivery.attempt == 3


@pytest.mark.asyncio
async def test_delivery_timeout(worker, sample_delivery):
    """Test delivery with timeout."""
    import httpx

    with patch.object(worker._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Request timeout")

        status = await worker.deliver(sample_delivery)

        assert status == DeliveryStatus.FAILED
        assert "Timeout" in sample_delivery.last_error


@pytest.mark.asyncio
async def test_delivery_request_error(worker, sample_delivery):
    """Test delivery with request error (e.g., connection refused)."""
    import httpx

    with patch.object(worker._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.ConnectError("Connection refused")

        status = await worker.deliver(sample_delivery)

        assert status == DeliveryStatus.FAILED
        assert "Request error" in sample_delivery.last_error


@pytest.mark.asyncio
async def test_deliver_with_retries_success_on_second_attempt(worker, sample_delivery):
    """Test automatic retries with success on second attempt."""
    with patch.object(worker._client, "post", new_callable=AsyncMock) as mock_post:
        # First call fails, second succeeds
        mock_post.side_effect = [
            AsyncMock(status_code=500, text="Error"),
            AsyncMock(status_code=200, text="OK"),
        ]

        status = await worker.deliver_with_retries(sample_delivery)

        assert status == DeliveryStatus.SUCCESS
        assert sample_delivery.attempt == 2
        assert mock_post.call_count == 2


@pytest.mark.asyncio
async def test_deliver_with_retries_all_failed(worker, sample_delivery):
    """Test automatic retries with all attempts failed."""
    with patch.object(worker._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 500
        mock_post.return_value.text = "Error"

        status = await worker.deliver_with_retries(sample_delivery)

        assert status == DeliveryStatus.EXHAUSTED
        assert sample_delivery.attempt == 3
        assert mock_post.call_count == 3


@pytest.mark.asyncio
async def test_signature_verification():
    """Test that signature can be verified by recipient."""
    payload = '{"event": "test"}'
    secret = "webhook_secret"

    async with WebhookDeliveryWorker() as worker:
        signature = worker._compute_signature(payload, secret)

        # Simulate recipient verification
        import hashlib
        import hmac

        expected_signature = hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        assert signature == expected_signature


@pytest.mark.asyncio
async def test_worker_context_manager():
    """Test worker async context manager."""
    worker = WebhookDeliveryWorker()
    assert worker._client is None

    async with worker:
        assert worker._client is not None

    # Client should be closed after exiting context
    # (We can't easily test this without accessing internal state)
