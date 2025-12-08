"""
Escrow Indexer Service

Main application that runs:
1. Pub/Sub subscriber (background thread) to process blockchain events
2. REST API (Flask) for querying escrow data
"""

import logging
import os
import sys
import threading

from flask import Flask, jsonify
from flask_cors import CORS

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Import routes
from app.routes.escrows import escrows_bp

# Import subscriber
from app.services.pubsub_subscriber import EscrowEventSubscriber

# Import database
from infrastructure.db import check_db_connection, init_db

# Create Flask app
app = Flask(__name__)

# Enable CORS for frontend
CORS(app, origins=["http://localhost:5173", "http://localhost:3000", "*"])

# Initialize database tables
logger.info("Initializing database tables...")
try:
    init_db()
    logger.info("✅ Database tables initialized")
except Exception as e:
    logger.error(f"❌ Database initialization failed: {e}")
    # Don't exit here - let the app start but log the error

# Register blueprints
app.register_blueprint(escrows_bp)

# Global subscriber instance for status endpoint
subscriber_instance = None

# Start Pub/Sub subscriber in background thread
logger.info("Starting Pub/Sub subscriber thread...")
project_id = os.getenv("PUBSUB_PROJECT_ID") or os.getenv("GCP_PROJECT", "fusion-prime")
subscription_id = os.getenv("PUBSUB_SUBSCRIPTION_ID", "escrow-indexer-sub")
logger.info(f"  Project: {project_id}")
logger.info(f"  Subscription: {subscription_id}")

try:
    subscriber_instance = EscrowEventSubscriber(
        project_id=project_id,
        subscription_id=subscription_id,
    )
    subscriber_thread = threading.Thread(target=subscriber_instance.start, daemon=True)
    subscriber_thread.start()
    logger.info("✅ Pub/Sub subscriber thread started")
except Exception as e:
    logger.error(f"❌ Failed to start subscriber: {e}", exc_info=True)


@app.route("/", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "escrow-indexer"}), 200


@app.route("/health", methods=["GET"])
def health_check():
    """Detailed health check."""
    global subscriber_instance

    db_healthy = check_db_connection()

    status = {
        "status": "healthy" if db_healthy else "unhealthy",
        "service": "escrow-indexer",
        "database": "connected" if db_healthy else "disconnected",
    }

    if subscriber_instance:
        stats = subscriber_instance.get_stats()
        status["subscriber"] = stats

    return jsonify(status), 200 if db_healthy else 503


@app.route("/stats", methods=["GET"])
def stats():
    """Get service statistics."""
    global subscriber_instance

    result = {"service": "escrow-indexer"}

    if subscriber_instance:
        result["subscriber"] = subscriber_instance.get_stats()

    return jsonify(result), 200


def run_subscriber():
    """Run Pub/Sub subscriber in background thread."""
    global subscriber_instance

    project_id = os.getenv("PUBSUB_PROJECT_ID") or os.getenv("GCP_PROJECT", "fusion-prime")
    subscription_id = os.getenv("PUBSUB_SUBSCRIPTION_ID", "escrow-indexer-sub")

    logger.info(f"Starting Pub/Sub subscriber")
    logger.info(f"  Project: {project_id}")
    logger.info(f"  Subscription: {subscription_id}")

    try:
        subscriber_instance = EscrowEventSubscriber(
            project_id=project_id,
            subscription_id=subscription_id,
        )
        subscriber_instance.start()
    except Exception as e:
        logger.error(f"❌ Subscriber error: {e}", exc_info=True)
        sys.exit(1)


def init_app():
    """Initialize application."""
    logger.info("🚀 Initializing Escrow Indexer Service")

    # Initialize database
    logger.info("Initializing database...")
    try:
        init_db()
        if not check_db_connection():
            logger.error("❌ Database connection failed")
            sys.exit(1)
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        sys.exit(1)

    # Start Pub/Sub subscriber in background thread
    logger.info("Starting Pub/Sub subscriber thread...")
    subscriber_thread = threading.Thread(target=run_subscriber, daemon=True)
    subscriber_thread.start()
    logger.info("✅ Subscriber thread started")

    logger.info("✅ Escrow Indexer Service initialized")


if __name__ == "__main__":
    # Initialize app
    init_app()

    # Get port from environment (Cloud Run sets PORT)
    port = int(os.getenv("PORT", "8080"))

    # Start Flask server (blocking)
    logger.info(f"🚀 Starting Flask API server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
