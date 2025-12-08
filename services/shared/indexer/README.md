# Shared Indexer Library

Common utilities and base classes for blockchain event indexers in the Fusion Prime platform.

## Purpose

This library provides reusable components to build consistent, scalable blockchain event indexers. All indexers (escrow, identity, cross-chain, etc.) share the same architectural patterns and can leverage this library.

## Components

### 1. Pub/Sub (`pubsub/`)

**BaseEventSubscriber**: Abstract base class for Pub/Sub subscribers
- Handles message subscription and acknowledgment
- Provides standard callback pattern
- Tracks statistics (messages processed, failed)
- Configurable timeout and error handling

**BaseEventProcessor**: Abstract interface for event processing
- Defines `process_event(event_type, event_data)` contract
- Implement this in your indexer's event processor

### 2. Database (`database/`)

**BaseDatabase**: Database connection and session management
- Automatic engine creation with Cloud Run-friendly settings
- Context managers for sessions with auto-commit/rollback
- Health check utilities
- Support for both DATABASE_URL and individual DB_* env vars

### 3. API (`api/`)

**Standard Responses**: Consistent API response formats
- `success_response()` - Successful responses
- `error_response()` - Error responses
- `list_response()` - List responses with count
- `not_found_response()` - 404 responses
- `validation_error_response()` - 400 validation errors

**Health Checks**: Standard health check endpoints
- `create_health_blueprint()` - Creates Flask blueprint with:
  - `GET /` - Basic health check
  - `GET /health` - Detailed health with DB and subscriber stats
  - `GET /readiness` - Kubernetes readiness probe
  - `GET /liveness` - Kubernetes liveness probe

### 4. Utilities (`utils/`)

**IndexerConfig**: Configuration management
- Loads environment variables with sensible defaults
- Validates required configuration
- Logs configuration (excluding secrets)

**Logging**: Standard logging setup
- Consistent log format across all indexers
- Reduces noise from third-party libraries
- Configurable log level

## Usage

### Creating a New Indexer

1. **Create event processor** (implements `BaseEventProcessor`):

```python
from shared.indexer.pubsub import BaseEventProcessor

class MyEventProcessor(BaseEventProcessor):
    def __init__(self, db):
        self.db = db

    def process_event(self, event_type: str, event_data: dict) -> bool:
        if event_type == "MyEvent":
            return self._process_my_event(event_data)
        return False

    def _process_my_event(self, data: dict) -> bool:
        # Process event and store in database
        with self.db.get_db_session() as session:
            # ... database operations
            pass
        return True
```

2. **Setup main application**:

```python
from flask import Flask
from flask_cors import CORS
from shared.indexer.database import BaseDatabase
from shared.indexer.pubsub import BaseEventSubscriber
from shared.indexer.api import create_health_blueprint
from shared.indexer.utils import IndexerConfig, setup_logging

# Configuration
SERVICE_NAME = "my-indexer"
config = IndexerConfig(SERVICE_NAME)
config.validate()

# Logging
setup_logging(SERVICE_NAME, config.log_level)

# Database
db = BaseDatabase(config.database_url, SERVICE_NAME)
db.init_db(Base)  # Your SQLAlchemy Base

# Flask app
app = Flask(__name__)
CORS(app)

# Health checks
health_bp = create_health_blueprint(
    SERVICE_NAME,
    check_db=db.check_connection,
    get_subscriber_stats=lambda: subscriber.get_stats()
)
app.register_blueprint(health_bp)

# Your API routes
from my_routes import my_bp
app.register_blueprint(my_bp)

# Pub/Sub subscriber (in background thread)
processor = MyEventProcessor(db)
subscriber = BaseEventSubscriber(
    project_id=config.pubsub_project_id,
    subscription_id=config.pubsub_subscription_id,
    event_processor=processor,
    service_name=SERVICE_NAME
)

# Start subscriber in background
import threading
subscriber_thread = threading.Thread(target=subscriber.start, daemon=True)
subscriber_thread.start()

# Run Flask
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.port)
```

3. **API routes** (use standard responses):

```python
from flask import Blueprint
from shared.indexer.api import success_response, error_response, not_found_response

my_bp = Blueprint("my_api", __name__, url_prefix="/api/v1")

@my_bp.route("/items/<item_id>", methods=["GET"])
def get_item(item_id):
    try:
        item = db.query(Item).filter(Item.id == item_id).first()
        if not item:
            return not_found_response("Item", item_id)

        return success_response({"item": item.to_dict()})
    except Exception as e:
        return error_response(str(e))
```

## Dependencies

```txt
flask>=3.0.0
flask-cors>=4.0.0
google-cloud-pubsub>=2.18.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
```

## Architecture Benefits

### Consistency
- All indexers have the same structure
- Predictable patterns for new developers
- Easier to maintain and debug

### Reusability
- Write once, use in all indexers
- Bug fixes benefit all services
- Easy to add new features

### Scalability
- Each indexer scales independently
- Optimized for Cloud Run (NullPool)
- Health checks for load balancers

### Testability
- Mock base classes for unit tests
- Consistent testing patterns
- Easier integration tests

## Example Indexers

- **escrow-indexer**: Indexes escrow events (EscrowDeployed, Approved, Released, Refunded)
- **identity-indexer** (template): Indexes identity events (IdentityCreated, ClaimAdded)
- **cross-chain-indexer** (template): Indexes bridge events (BridgeInitiated, BridgeCompleted)

## File Structure for New Indexer

```
services/my-indexer/
├── app/
│   ├── __init__.py
│   ├── main.py                    # Uses shared library
│   ├── routes/
│   │   ├── __init__.py
│   │   └── my_routes.py           # Uses shared.indexer.api
│   └── services/
│       ├── __init__.py
│       └── event_processor.py     # Implements BaseEventProcessor
├── infrastructure/
│   └── db/
│       ├── __init__.py
│       ├── models.py              # SQLAlchemy models
│       └── database.py            # Uses BaseDatabase
├── Dockerfile
├── cloudbuild.yaml
├── deploy.sh
└── requirements.txt
```

## Development

### Adding New Shared Features

1. Create feature in appropriate module
2. Export in `__init__.py`
3. Update this README
4. Update existing indexers to use new feature
5. Create example in README

### Testing Changes

Test in one indexer first, then roll out to others:

```bash
# Test in escrow-indexer
cd services/escrow-indexer
python app/main.py

# If successful, update other indexers
```

## Versioning

This library uses semantic versioning: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes requiring indexer updates
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes

Current version: **1.0.0**

## License

Apache 2.0
