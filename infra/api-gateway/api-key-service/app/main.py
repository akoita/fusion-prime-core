"""API Key Management Service for API Gateway."""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


class APIKey(BaseModel):
    """API Key model."""

    key_id: str
    key_name: str
    tier: str  # free, pro, enterprise
    created_at: str
    last_used: Optional[str] = None
    requests_today: int = 0
    requests_limit: int


class CreateAPIKeyRequest(BaseModel):
    """Request to create API key."""

    key_name: str
    tier: str = "free"  # free, pro, enterprise
    user_id: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("🚀 API Key Management Service starting up")
    yield
    logger.info("🛑 API Key Management Service shutting down")


app = FastAPI(
    title="API Key Management Service",
    description="Manages API keys for Fusion Prime API Gateway",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# In-memory storage (replace with database in production)
api_keys_db = {}


def generate_api_key() -> str:
    """Generate a new API key."""
    import secrets

    return f"fp_{secrets.token_urlsafe(32)}"


@app.post("/api/v1/keys", response_model=APIKey)
async def create_api_key(request: CreateAPIKeyRequest):
    """Create a new API key."""
    import uuid

    key_id = str(uuid.uuid4())
    api_key = generate_api_key()

    # Determine rate limits based on tier
    tier_limits = {
        "free": 100,  # requests per minute
        "pro": 1000,
        "enterprise": 10000,
    }

    requests_limit = tier_limits.get(request.tier.lower(), 100)

    key_record = {
        "key_id": key_id,
        "api_key": api_key,
        "key_name": request.key_name,
        "tier": request.tier.lower(),
        "user_id": request.user_id,
        "created_at": datetime.utcnow().isoformat(),
        "requests_today": 0,
        "requests_limit": requests_limit,
    }

    api_keys_db[api_key] = key_record

    logger.info(f"Created API key: {key_id} (tier: {request.tier})")

    return APIKey(
        key_id=key_id,
        key_name=request.key_name,
        tier=request.tier,
        created_at=key_record["created_at"],
        requests_limit=requests_limit,
    )


@app.get("/api/v1/keys/{key_id}", response_model=APIKey)
async def get_api_key(key_id: str):
    """Get API key details."""
    # Find key by key_id
    key_record = None
    for api_key, record in api_keys_db.items():
        if record["key_id"] == key_id:
            key_record = record
            break

    if not key_record:
        raise HTTPException(status_code=404, detail="API key not found")

    return APIKey(
        key_id=key_record["key_id"],
        key_name=key_record["key_name"],
        tier=key_record["tier"],
        created_at=key_record["created_at"],
        last_used=key_record.get("last_used"),
        requests_today=key_record["requests_today"],
        requests_limit=key_record["requests_limit"],
    )


@app.delete("/api/v1/keys/{key_id}")
async def revoke_api_key(key_id: str):
    """Revoke an API key."""
    # Find and remove key
    api_key_to_remove = None
    for api_key, record in api_keys_db.items():
        if record["key_id"] == key_id:
            api_key_to_remove = api_key
            break

    if api_key_to_remove:
        del api_keys_db[api_key_to_remove]
        logger.info(f"Revoked API key: {key_id}")
        return {"status": "revoked"}
    else:
        raise HTTPException(status_code=404, detail="API key not found")


@app.get("/api/v1/keys")
async def list_api_keys(user_id: Optional[str] = None):
    """List API keys (optionally filtered by user_id)."""
    keys = []
    for api_key, record in api_keys_db.items():
        if user_id is None or record.get("user_id") == user_id:
            keys.append(
                APIKey(
                    key_id=record["key_id"],
                    key_name=record["key_name"],
                    tier=record["tier"],
                    created_at=record["created_at"],
                    last_used=record.get("last_used"),
                    requests_today=record["requests_today"],
                    requests_limit=record["requests_limit"],
                )
            )
    return {"keys": keys, "total": len(keys)}


@app.post("/api/v1/keys/{key_id}/rotate")
async def rotate_api_key(key_id: str):
    """Rotate an API key (generate new key, keep same key_id)."""
    # Find key
    api_key_to_rotate = None
    for api_key, record in api_keys_db.items():
        if record["key_id"] == key_id:
            api_key_to_rotate = api_key
            break

    if not api_key_to_rotate:
        raise HTTPException(status_code=404, detail="API key not found")

    # Generate new key
    new_api_key = generate_api_key()
    old_record = api_keys_db[api_key_to_rotate].copy()

    # Create new record with same key_id
    del api_keys_db[api_key_to_rotate]
    api_keys_db[new_api_key] = old_record
    old_record["api_key"] = new_api_key

    logger.info(f"Rotated API key: {key_id}")

    return {"key_id": key_id, "new_api_key": new_api_key}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "api-key-service"}


# Validation endpoint (used by API Gateway)
@app.post("/api/v1/validate")
async def validate_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """Validate an API key and return tier/rate limit info."""
    if x_api_key not in api_keys_db:
        raise HTTPException(status_code=401, detail="Invalid API key")

    record = api_keys_db[x_api_key]

    # Update last used
    record["last_used"] = datetime.utcnow().isoformat()

    return {
        "valid": True,
        "tier": record["tier"],
        "requests_limit": record["requests_limit"],
        "key_id": record["key_id"],
    }
