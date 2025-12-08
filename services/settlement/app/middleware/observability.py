"""Observability middleware for structured logging, tracing, and error tracking."""

from __future__ import annotations

import json
import logging
import time
import traceback
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


# Configure structured logging
class CustomFormatter(logging.Formatter):
    def format(self, record):
        # Create a copy of the record to avoid modifying the original
        record_copy = logging.makeLogRecord(record.__dict__)

        # Get the extra data from the record safely
        extra_data = getattr(record_copy, "extra", {})
        if not extra_data or not isinstance(extra_data, dict):
            extra_data = {}

        # Format the basic log message
        basic_format = '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "message": "%(message)s"'

        # Add extra data if present and valid
        if extra_data:
            try:
                import json

                extra_json = json.dumps(extra_data)
                basic_format += f', "extra": {extra_json}'
            except (TypeError, ValueError):
                # If extra data can't be serialized, skip it
                pass

        basic_format += "}"

        # Set the format and format the record
        self._style._fmt = basic_format
        return super().format(record_copy)


# Set up logging with custom formatter
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(CustomFormatter(datefmt="%Y-%m-%dT%H:%M:%S%z"))
logger.addHandler(handler)

logger = logging.getLogger(__name__)


class StructuredLoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that adds structured context to log messages.

    This ensures all logs include trace_id, request_id, and other contextual information
    for easy correlation in Cloud Logging.
    """

    def process(self, msg, kwargs):
        """Add extra context to log messages."""
        extra = kwargs.get("extra", {})
        if self.extra:
            extra.update(self.extra)
        # Keep extra as dict, don't convert to JSON string
        kwargs["extra"] = extra if extra else {}
        return msg, kwargs


def get_logger(name: str, **context) -> StructuredLoggerAdapter:
    """
    Get a structured logger with optional context.

    Args:
        name: Logger name (typically __name__)
        **context: Additional context to include in all logs

    Returns:
        Structured logger adapter

    Example:
        >>> logger = get_logger(__name__, service="settlement", version="1.0")
        >>> logger.info("Processing command", extra={"command_id": "cmd-123"})
    """
    base_logger = logging.getLogger(name)
    return StructuredLoggerAdapter(base_logger, context)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request/response logging, tracing, and performance monitoring.

    Features:
    - Automatic trace_id generation for distributed tracing
    - Request/response logging with timing
    - Error tracking with stack traces
    - Performance metrics (latency, status codes)
    """

    def __init__(self, app: ASGIApp, service_name: str = "settlement-service"):
        """
        Initialize observability middleware.

        Args:
            app: FastAPI application
            service_name: Service name for logging context
        """
        super().__init__(app)
        self.service_name = service_name
        self.logger = get_logger(__name__, service=service_name)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with observability instrumentation.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response
        """
        # Generate trace and request IDs
        trace_id = request.headers.get("X-Cloud-Trace-Context", str(uuid.uuid4()))
        request_id = str(uuid.uuid4())

        # Add to request state for downstream use
        request.state.trace_id = trace_id
        request.state.request_id = request_id

        # Start timing
        start_time = time.time()

        # Log incoming request
        self.logger.info(
            "Incoming request",
            extra={
                "trace_id": trace_id,
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_host": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            },
        )

        response = None
        error = None

        try:
            # Process request
            response = await call_next(request)

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            # Log successful response
            self.logger.info(
                "Request completed",
                extra={
                    "trace_id": trace_id,
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "latency_ms": round(latency_ms, 2),
                },
            )

            # Add trace headers to response
            response.headers["X-Trace-ID"] = trace_id
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{latency_ms:.2f}ms"

            return response

        except Exception as e:
            error = e
            latency_ms = (time.time() - start_time) * 1000

            # Log error with stack trace
            self.logger.error(
                "Request failed with exception",
                extra={
                    "trace_id": trace_id,
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "stack_trace": traceback.format_exc(),
                    "latency_ms": round(latency_ms, 2),
                },
                exc_info=True,
            )

            # Re-raise to let FastAPI handle it
            raise


class ErrorTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for capturing and reporting errors to error tracking services.

    In production, this would integrate with services like:
    - Google Cloud Error Reporting
    - Sentry
    - Rollbar
    """

    def __init__(self, app: ASGIApp, enable_reporting: bool = True):
        """
        Initialize error tracking middleware.

        Args:
            app: FastAPI application
            enable_reporting: Whether to enable error reporting (disable in tests)
        """
        super().__init__(app)
        self.enable_reporting = enable_reporting
        self.logger = get_logger(__name__)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with error tracking.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response
        """
        try:
            response = await call_next(request)

            # Track 5xx errors even if no exception was raised
            if 500 <= response.status_code < 600 and self.enable_reporting:
                self._report_error(
                    request=request,
                    error_type="HTTPError",
                    error_message=f"HTTP {response.status_code}",
                    status_code=response.status_code,
                )

            return response

        except Exception as e:
            if self.enable_reporting:
                self._report_error(
                    request=request,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    exception=e,
                )
            raise

    def _report_error(
        self,
        request: Request,
        error_type: str,
        error_message: str,
        status_code: int = 500,
        exception: Exception | None = None,
    ) -> None:
        """
        Report error to tracking service.

        Args:
            request: HTTP request
            error_type: Type of error
            error_message: Error message
            status_code: HTTP status code
            exception: Original exception (if available)
        """
        trace_id = getattr(request.state, "trace_id", "unknown")
        request_id = getattr(request.state, "request_id", "unknown")

        error_context = {
            "trace_id": trace_id,
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "error_type": error_type,
            "error_message": error_message,
            "status_code": status_code,
        }

        if exception:
            error_context["stack_trace"] = traceback.format_exception(
                type(exception), exception, exception.__traceback__
            )

        self.logger.error(
            "Error reported to tracking service",
            extra=error_context,
        )

        # In production, send to Cloud Error Reporting:
        # from google.cloud import error_reporting
        # client = error_reporting.Client()
        # client.report_exception(...)


def configure_observability(app, service_name: str = "settlement-service"):
    """
    Configure observability for FastAPI application.

    Args:
        app: FastAPI application
        service_name: Service name for logging context

    Example:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> configure_observability(app, "settlement-service")
    """
    # Add middleware (order matters: first added = outermost layer)
    app.add_middleware(ErrorTrackingMiddleware, enable_reporting=True)
    app.add_middleware(ObservabilityMiddleware, service_name=service_name)

    logger = get_logger(__name__, service=service_name)
    logger.info(
        "Observability configured",
        extra={
            "service": service_name,
            "middlewares": ["ErrorTracking", "Observability"],
        },
    )
