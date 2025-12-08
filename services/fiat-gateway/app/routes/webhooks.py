"""Webhook routes for payment provider callbacks."""

import logging

from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/circle")
async def circle_webhook(request: Request):
    """Handle webhook events from Circle."""
    body = await request.body()
    headers = dict(request.headers)

    logger.info(f"Received Circle webhook: {headers.get('x-circle-signature', 'no-signature')}")

    # TODO: Verify webhook signature
    # TODO: Process webhook event (payment completed, failed, etc.)

    return {"status": "received"}


@router.post("/stripe")
async def stripe_webhook(request: Request):
    """Handle webhook events from Stripe."""
    body = await request.body()
    headers = dict(request.headers)

    logger.info(f"Received Stripe webhook: {headers.get('stripe-signature', 'no-signature')}")

    # TODO: Verify webhook signature
    # TODO: Process webhook event

    return {"status": "received"}
