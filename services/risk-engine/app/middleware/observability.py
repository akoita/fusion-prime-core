"""
Observability middleware for Risk Engine Service.
"""

import json
import logging
import time
from typing import Optional

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
                extra_json = json.dumps(extra_data)
                basic_format += f', "extra": {extra_json}'
            except (TypeError, ValueError):
                # If extra data can't be serialized, skip it
                pass

        basic_format += "}"

        # Set the format and format the record
        self._style._fmt = basic_format
        return super().format(record_copy)


def configure_observability(app, service_name: str = "risk-engine"):
    """Configure observability for the Risk Engine Service."""

    # Configure logging
    logger = logging.getLogger(service_name)
    logger.setLevel(logging.INFO)

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create console handler with custom formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(CustomFormatter())
    logger.addHandler(console_handler)

    # Add middleware for request logging
    app.add_middleware(LoggingMiddleware, service_name=service_name)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses."""

    def __init__(self, app: ASGIApp, service_name: str = "risk-engine"):
        super().__init__(app)
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)

    async def dispatch(self, request: Request, call_next):
        # Log request
        start_time = time.time()

        self.logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "service": self.service_name,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": request.client.host if request.client else None,
            },
        )

        # Process request
        response = await call_next(request)

        # Log response
        process_time = time.time() - start_time

        self.logger.info(
            f"Request completed: {response.status_code}",
            extra={
                "service": self.service_name,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "process_time": process_time,
            },
        )

        return response


def get_logger(name: str, service: str = "risk-engine") -> logging.Logger:
    """Get a logger with service context."""
    logger = logging.getLogger(name)

    # Add service context to all log records
    class ServiceFilter(logging.Filter):
        def __init__(self, service_name):
            super().__init__()
            self.service_name = service_name

        def filter(self, record):
            record.service = self.service_name
            return True

    # Add service filter if not already present
    if not any(isinstance(f, ServiceFilter) for f in logger.filters):
        logger.addFilter(ServiceFilter(service))

    return logger
