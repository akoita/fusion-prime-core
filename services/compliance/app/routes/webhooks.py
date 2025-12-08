"""
Webhook endpoints for external service callbacks.
Handles Persona KYC verification webhooks.
"""

import logging
from typing import Any, Dict

from app.integrations.persona_client import PersonaKYCClient
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class PersonaWebhookEvent(BaseModel):
    """Persona webhook event payload."""

    type: str
    data: Dict[str, Any]


@router.post("/persona/inquiry")
async def persona_inquiry_webhook(
    request: Request,
    event: PersonaWebhookEvent,
    persona_signature: str = Header(None, alias="Persona-Signature"),
):
    """
    Handle Persona inquiry webhook events.

    Persona sends webhooks when inquiry status changes:
    - inquiry.created
    - inquiry.started
    - inquiry.completed
    - inquiry.failed
    - inquiry.needs-review
    - inquiry.approved
    - inquiry.declined
    """
    try:
        # Get compliance engine from app state
        compliance_engine = getattr(request.app.state, "compliance_engine", None)
        if not compliance_engine:
            raise HTTPException(status_code=503, detail="Compliance engine not initialized")

        # Verify webhook signature
        raw_body = await request.body()
        persona_client = PersonaKYCClient()

        if persona_signature:
            is_valid = persona_client.verify_webhook_signature(
                payload=raw_body.decode("utf-8"), signature=persona_signature
            )

            if not is_valid:
                logger.warning("Invalid Persona webhook signature")
                raise HTTPException(status_code=401, detail="Invalid webhook signature")

        logger.info(f"Received Persona webhook: {event.type}")

        # Process inquiry status updates
        if event.type.startswith("inquiry."):
            inquiry_data = event.data.get("attributes", {})
            inquiry_id = event.data.get("id")

            if not inquiry_id:
                raise HTTPException(status_code=400, detail="Missing inquiry ID")

            # Extract inquiry status
            inquiry_status = inquiry_data.get("status")

            if not inquiry_status:
                logger.warning(f"Webhook {event.type} has no status, skipping")
                return {"status": "ignored", "reason": "no_status_change"}

            # Process the webhook in compliance engine
            result = await compliance_engine.process_persona_webhook(
                inquiry_id=inquiry_id, status=inquiry_status, inquiry_data=inquiry_data
            )

            logger.info(
                f"Processed Persona webhook for inquiry {inquiry_id}: "
                f"case_id={result['case_id']}, status={result['status']}"
            )

            return {
                "status": "processed",
                "case_id": result["case_id"],
                "kyc_status": result["status"],
            }

        else:
            # Other event types (verification, document, etc.)
            logger.info(f"Received non-inquiry Persona webhook: {event.type}")
            return {"status": "acknowledged"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Persona webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")


@router.get("/persona/health")
async def persona_webhook_health():
    """Health check endpoint for Persona webhook configuration."""
    return {
        "status": "healthy",
        "webhook": "persona_inquiry",
        "accepted_events": [
            "inquiry.created",
            "inquiry.started",
            "inquiry.completed",
            "inquiry.failed",
            "inquiry.needs-review",
            "inquiry.approved",
            "inquiry.declined",
        ],
    }
