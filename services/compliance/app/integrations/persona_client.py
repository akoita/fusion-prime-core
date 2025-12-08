"""
Persona API Client for KYC verification.
Integrates with Persona's identity verification platform.
"""

import logging
import os
from typing import Any, Dict, Optional

import httpx
from persona import Client as PersonaClient

logger = logging.getLogger(__name__)


class PersonaKYCClient:
    """Client for Persona KYC verification API."""

    def __init__(self, api_key: Optional[str] = None, environment: str = "sandbox"):
        """
        Initialize Persona client.

        Args:
            api_key: Persona API key (defaults to environment variable)
            environment: 'sandbox' or 'production'
        """
        self.api_key = api_key or os.getenv("PERSONA_API_KEY")
        self.environment = environment

        if not self.api_key:
            logger.warning("Persona API key not configured. KYC verification will fail.")
            self.client = None
        else:
            # Initialize Persona SDK client
            self.client = PersonaClient(api_key=self.api_key, environment=environment)
            logger.info(f"Persona client initialized for {environment} environment")

    async def create_inquiry(
        self,
        user_id: str,
        reference_id: str,
        template_id: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a Persona inquiry for KYC verification.

        Args:
            user_id: Internal user ID
            reference_id: Reference ID for linking (case_id)
            template_id: Persona template ID (optional)
            redirect_uri: Redirect URI after completion (optional)

        Returns:
            Dict with inquiry_id and session_token
        """
        try:
            if not self.client:
                raise ValueError("Persona client not initialized. Check API key configuration.")

            # Create inquiry using Persona SDK
            inquiry = self.client.inquiries.create(
                inquiry_template_id=template_id or os.getenv("PERSONA_TEMPLATE_ID"),
                reference_id=reference_id,
                redirect_uri=redirect_uri,
                fields={
                    "name_first": "",  # User will provide
                    "name_last": "",  # User will provide
                },
            )

            logger.info(f"Created Persona inquiry {inquiry.id} for user {user_id}")

            return {
                "inquiry_id": inquiry.id,
                "session_token": inquiry.attributes.session_token,
                "status": inquiry.attributes.status,
                "reference_id": reference_id,
            }

        except Exception as e:
            logger.error(f"Failed to create Persona inquiry: {e}")
            raise

    async def get_inquiry(self, inquiry_id: str) -> Dict[str, Any]:
        """
        Get inquiry status from Persona.

        Args:
            inquiry_id: Persona inquiry ID

        Returns:
            Dict with inquiry details and status
        """
        try:
            if not self.client:
                raise ValueError("Persona client not initialized")

            inquiry = self.client.inquiries.retrieve(inquiry_id)

            return {
                "inquiry_id": inquiry.id,
                "status": inquiry.attributes.status,
                "reference_id": inquiry.attributes.reference_id,
                "created_at": inquiry.attributes.created_at,
                "completed_at": inquiry.attributes.completed_at,
                "fields": inquiry.attributes.fields,
            }

        except Exception as e:
            logger.error(f"Failed to get Persona inquiry {inquiry_id}: {e}")
            raise

    async def approve_inquiry(self, inquiry_id: str) -> Dict[str, Any]:
        """
        Manually approve an inquiry (for testing/override).

        Args:
            inquiry_id: Persona inquiry ID

        Returns:
            Updated inquiry status
        """
        try:
            if not self.client:
                raise ValueError("Persona client not initialized")

            inquiry = self.client.inquiries.approve(inquiry_id)

            logger.info(f"Approved Persona inquiry {inquiry_id}")

            return {
                "inquiry_id": inquiry.id,
                "status": inquiry.attributes.status,
            }

        except Exception as e:
            logger.error(f"Failed to approve inquiry {inquiry_id}: {e}")
            raise

    async def decline_inquiry(
        self, inquiry_id: str, reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Manually decline an inquiry.

        Args:
            inquiry_id: Persona inquiry ID
            reason: Reason for decline (optional)

        Returns:
            Updated inquiry status
        """
        try:
            if not self.client:
                raise ValueError("Persona client not initialized")

            inquiry = self.client.inquiries.decline(inquiry_id)

            logger.info(f"Declined Persona inquiry {inquiry_id}: {reason}")

            return {
                "inquiry_id": inquiry.id,
                "status": inquiry.attributes.status,
            }

        except Exception as e:
            logger.error(f"Failed to decline inquiry {inquiry_id}: {e}")
            raise

    def verify_webhook_signature(
        self, payload: str, signature: str, webhook_secret: Optional[str] = None
    ) -> bool:
        """
        Verify Persona webhook signature.

        Args:
            payload: Raw webhook payload
            signature: Signature from Persona-Signature header
            webhook_secret: Webhook secret (defaults to env var)

        Returns:
            True if signature is valid
        """
        try:
            secret = webhook_secret or os.getenv("PERSONA_WEBHOOK_SECRET")

            if not secret:
                logger.warning("Persona webhook secret not configured")
                return False

            # Persona uses HMAC SHA256 for webhook signatures
            import hashlib
            import hmac

            expected_signature = hmac.new(
                secret.encode(), payload.encode(), hashlib.sha256
            ).hexdigest()

            is_valid = hmac.compare_digest(signature, expected_signature)

            if not is_valid:
                logger.warning("Invalid Persona webhook signature")

            return is_valid

        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """
        Check Persona API health.

        Returns:
            Health status dict
        """
        try:
            if not self.client:
                return {
                    "status": "unhealthy",
                    "error": "Persona client not initialized",
                }

            # Try to list inquiries as health check
            inquiries = self.client.inquiries.list(page_size=1)

            return {
                "status": "healthy",
                "environment": self.environment,
                "api_accessible": True,
            }

        except Exception as e:
            logger.error(f"Persona health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
            }
