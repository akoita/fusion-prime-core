"""
Shared Indexer Library

Provides common functionality for blockchain event indexers:
- Pub/Sub subscription and message handling
- Database connection and utilities
- Standard API patterns
- Deployment utilities

Usage:
    from shared.indexer.pubsub import BaseEventSubscriber
    from shared.indexer.database import BaseDatabase
    from shared.indexer.api import create_api_blueprint
"""

__version__ = "1.0.0"
