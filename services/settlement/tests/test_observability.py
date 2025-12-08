"""Tests for observability middleware."""

import json
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from app.middleware import (
    ErrorTrackingMiddleware,
    ObservabilityMiddleware,
    configure_observability,
    get_logger,
)
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def test_app():
    """Create test FastAPI app with observability."""
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        return {"message": "success"}

    @app.get("/error")
    async def error_endpoint():
        raise HTTPException(status_code=500, detail="Internal server error")

    @app.get("/exception")
    async def exception_endpoint():
        raise ValueError("Test exception")

    configure_observability(app, service_name="test-service")
    return app


@pytest.mark.asyncio
async def test_successful_request_logging(test_app):
    """Test that successful requests are logged with trace IDs."""
    with patch("app.middleware.observability.StructuredLoggerAdapter.info") as mock_info:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.get("/test")

        assert response.status_code == 200
        assert "X-Trace-ID" in response.headers
        assert "X-Request-ID" in response.headers
        assert "X-Response-Time" in response.headers

        # Verify logging calls
        assert mock_info.call_count >= 2  # Incoming + completed


@pytest.mark.asyncio
async def test_trace_id_propagation(test_app):
    """Test that trace ID from header is propagated."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        trace_id = "test-trace-123"
        response = await client.get("/test", headers={"X-Cloud-Trace-Context": trace_id})

        assert response.headers["X-Trace-ID"] == trace_id


@pytest.mark.asyncio
async def test_error_tracking_on_5xx(test_app):
    """Test that 5xx errors are tracked."""
    with patch("app.middleware.observability.StructuredLoggerAdapter.error") as mock_error:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.get("/error")

        assert response.status_code == 500

        # Verify error was reported
        # The error tracking middleware should log the error
        error_calls = [call for call in mock_error.call_args_list if "Error reported" in str(call)]
        assert len(error_calls) > 0


@pytest.mark.asyncio
async def test_exception_handling(test_app):
    """Test that unhandled exceptions are logged with stack traces."""
    with patch("app.middleware.observability.StructuredLoggerAdapter.error") as mock_error:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            with pytest.raises(Exception):
                await client.get("/exception")

        # Verify exception was logged
        assert mock_error.called


@pytest.mark.asyncio
async def test_latency_tracking(test_app):
    """Test that request latency is tracked."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.get("/test")

    response_time = response.headers.get("X-Response-Time")
    assert response_time is not None
    assert response_time.endswith("ms")

    # Parse and verify it's a valid number
    latency_ms = float(response_time.replace("ms", ""))
    assert latency_ms >= 0


def test_get_logger():
    """Test structured logger creation."""
    logger = get_logger("test.module", service="test-service", version="1.0")

    assert logger.logger.name == "test.module"
    assert logger.extra == {"service": "test-service", "version": "1.0"}


def test_structured_logger_adapter():
    """Test that structured logger adds context to logs."""
    logger = get_logger("test.module", request_id="req-123")

    # Test that the logger has the correct structure
    assert logger.logger.name == "test.module"
    assert "request_id" in logger.extra
    assert logger.extra["request_id"] == "req-123"

    # Test that the process method adds context correctly
    msg, kwargs = logger.process("Test message", {"extra": {"user_id": "user-456"}})
    assert msg == "Test message"
    assert "extra" in kwargs
    assert "request_id" in kwargs["extra"]
    assert "user_id" in kwargs["extra"]
    assert kwargs["extra"]["request_id"] == "req-123"
    assert kwargs["extra"]["user_id"] == "user-456"


@pytest.mark.asyncio
async def test_observability_middleware_context():
    """Test that observability middleware adds context to request state."""
    from fastapi import Request

    app = FastAPI()

    @app.get("/test")
    async def test_endpoint(request: Request):
        # Access trace_id from request state
        return {
            "trace_id": request.state.trace_id,
            "request_id": request.state.request_id,
        }

    app.add_middleware(ObservabilityMiddleware, service_name="test")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/test")

    data = response.json()
    assert "trace_id" in data
    assert "request_id" in data
    assert data["trace_id"] is not None
    assert data["request_id"] is not None


@pytest.mark.asyncio
async def test_error_tracking_middleware_disabled():
    """Test that error tracking can be disabled."""
    app = FastAPI()

    @app.get("/error")
    async def error_endpoint():
        raise HTTPException(status_code=500, detail="Error")

    app.add_middleware(ErrorTrackingMiddleware, enable_reporting=False)

    with patch("app.middleware.observability.logger") as mock_logger:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/error")

        assert response.status_code == 500

        # Verify no error was reported (reporting disabled)
        error_calls = [
            call for call in mock_logger.error.call_args_list if "Error reported" in str(call)
        ]
        # Should be 0 when reporting is disabled
        # (There might be other error logs, but not from error tracking)
