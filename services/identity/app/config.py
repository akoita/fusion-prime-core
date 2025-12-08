"""
Configuration for Identity Service.
"""

import os
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Environment
    environment: str = "development"
    log_level: str = "info"

    # Service
    service_name: str = "identity-service"
    port: int = 8002

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/identity_db"

    # Authentication
    jwt_secret_key: str = "your-secret-key-change-in-production"  # Change in production!
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Blockchain
    blockchain_network: str = "sepolia"
    rpc_url: str
    chain_id: int = 11155111

    # Contract addresses
    identity_factory_address: str
    claim_issuer_registry_address: str

    # Backend signer
    backend_private_key: str
    backend_address: str

    # Compliance Service
    compliance_service_url: str = "http://localhost:8001"

    # GCP
    gcp_project_id: Optional[str] = None
    google_application_credentials: Optional[str] = None

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Monitoring
    enable_metrics: bool = True
    enable_tracing: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
