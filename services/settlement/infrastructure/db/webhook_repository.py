"""Repository for webhook subscription operations."""

import json
from typing import Optional

from domain.webhooks import WebhookSubscription
from infrastructure.db.models import WebhookSubscriptionRecord
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def create_subscription(session: AsyncSession, subscription: WebhookSubscription) -> None:
    """Create a new webhook subscription."""
    record = WebhookSubscriptionRecord(
        subscription_id=subscription.subscription_id,
        url=subscription.url,
        secret=subscription.secret,
        event_types=json.dumps(subscription.event_types),
        enabled=subscription.enabled,
        description=subscription.description,
    )
    session.add(record)
    await session.commit()


async def get_subscription(
    session: AsyncSession, subscription_id: str
) -> Optional[WebhookSubscription]:
    """Retrieve a webhook subscription by ID."""
    result = await session.execute(
        select(WebhookSubscriptionRecord).where(
            WebhookSubscriptionRecord.subscription_id == subscription_id
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        return None

    return WebhookSubscription(
        subscription_id=record.subscription_id,
        url=record.url,
        secret=record.secret,
        event_types=json.loads(record.event_types),
        enabled=record.enabled,
        description=record.description,
    )


async def list_subscriptions(session: AsyncSession) -> list[WebhookSubscription]:
    """List all webhook subscriptions."""
    result = await session.execute(select(WebhookSubscriptionRecord))
    records = result.scalars().all()

    return [
        WebhookSubscription(
            subscription_id=record.subscription_id,
            url=record.url,
            secret=record.secret,
            event_types=json.loads(record.event_types),
            enabled=record.enabled,
            description=record.description,
        )
        for record in records
    ]


async def delete_subscription(session: AsyncSession, subscription_id: str) -> bool:
    """Delete a webhook subscription by ID."""
    result = await session.execute(
        select(WebhookSubscriptionRecord).where(
            WebhookSubscriptionRecord.subscription_id == subscription_id
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        return False

    await session.delete(record)
    await session.commit()
    return True
