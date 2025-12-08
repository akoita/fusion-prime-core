"""
Standard health check utilities for indexers

Provides consistent health check endpoints across all indexer APIs.
"""

import logging
from typing import Any, Callable, Dict

from flask import Blueprint, jsonify

logger = logging.getLogger(__name__)


def create_health_blueprint(
    service_name: str,
    check_db: Callable[[], bool],
    get_subscriber_stats: Callable[[], Dict[str, Any]] = None,
) -> Blueprint:
    """
    Create a standard health check blueprint.

    Args:
        service_name: Name of the service
        check_db: Function to check database connection
        get_subscriber_stats: Optional function to get subscriber statistics

    Returns:
        Flask blueprint with health check endpoints
    """
    health_bp = Blueprint("health", __name__)

    @health_bp.route("/", methods=["GET"])
    def root():
        """Root health check."""
        return jsonify({"status": "healthy", "service": service_name}), 200

    @health_bp.route("/health", methods=["GET"])
    def health():
        """Detailed health check."""
        db_healthy = check_db()

        status = {
            "status": "healthy" if db_healthy else "unhealthy",
            "service": service_name,
            "database": "connected" if db_healthy else "disconnected",
        }

        if get_subscriber_stats:
            try:
                stats = get_subscriber_stats()
                status["subscriber"] = stats
            except Exception as e:
                logger.error(f"Failed to get subscriber stats: {e}")
                status["subscriber"] = {"error": str(e)}

        return jsonify(status), 200 if db_healthy else 503

    @health_bp.route("/readiness", methods=["GET"])
    def readiness():
        """Kubernetes readiness probe."""
        db_healthy = check_db()
        return jsonify({"ready": db_healthy}), 200 if db_healthy else 503

    @health_bp.route("/liveness", methods=["GET"])
    def liveness():
        """Kubernetes liveness probe."""
        return jsonify({"alive": True}), 200

    return health_bp
