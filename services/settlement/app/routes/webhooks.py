"""Webhook subscription management endpoints."""

import secrets
from typing import Annotated

from app.dependencies import get_session
from domain.webhooks import WebhookSubscription
from fastapi import APIRouter, Depends, HTTPException, status
from infrastructure.db import webhook_repository
from pydantic import BaseModel, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class CreateWebhookRequest(BaseModel):
    """Request model for creating a webhook subscription."""

    url: HttpUrl
    event_types: list[str]
    description: str | None = None


class WebhookResponse(BaseModel):
    """Response model for webhook subscription."""

    subscription_id: str
    url: str
    secret: str
    event_types: list[str]
    enabled: bool
    description: str | None = None


@router.post("", status_code=status.HTTP_201_CREATED, response_model=WebhookResponse)
async def create_webhook(
    request: CreateWebhookRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> WebhookResponse:
    """Create a new webhook subscription."""
    subscription_id = f"wh_{secrets.token_urlsafe(16)}"
    secret = secrets.token_urlsafe(32)

    subscription = WebhookSubscription(
        subscription_id=subscription_id,
        url=str(request.url),
        secret=secret,
        event_types=request.event_types,
        description=request.description,
    )

    await webhook_repository.create_subscription(session, subscription)

    return WebhookResponse(
        subscription_id=subscription.subscription_id,
        url=subscription.url,
        secret=subscription.secret,
        event_types=subscription.event_types,
        enabled=subscription.enabled,
        description=subscription.description,
    )


@router.get("/{subscription_id}", response_model=WebhookResponse)
async def get_webhook(
    subscription_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> WebhookResponse:
    """Retrieve a webhook subscription by ID."""
    subscription = await webhook_repository.get_subscription(session, subscription_id)
    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook subscription {subscription_id} not found",
        )

    return WebhookResponse(
        subscription_id=subscription.subscription_id,
        url=subscription.url,
        secret=subscription.secret,
        event_types=subscription.event_types,
        enabled=subscription.enabled,
        description=subscription.description,
    )


@router.get("", response_model=list[WebhookResponse])
async def list_webhooks(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[WebhookResponse]:
    """List all webhook subscriptions."""
    subscriptions = await webhook_repository.list_subscriptions(session)

    return [
        WebhookResponse(
            subscription_id=sub.subscription_id,
            url=sub.url,
            secret=sub.secret,
            event_types=sub.event_types,
            enabled=sub.enabled,
            description=sub.description,
        )
        for sub in subscriptions
    ]


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    subscription_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """Delete a webhook subscription."""
    deleted = await webhook_repository.delete_subscription(session, subscription_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook subscription {subscription_id} not found",
        )
