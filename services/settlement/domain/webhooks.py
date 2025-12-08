"""Domain models for webhook management."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class WebhookSubscription:
    """Represents a webhook subscription."""

    subscription_id: str
    url: str
    secret: str
    event_types: list[str]
    enabled: bool = True
    description: Optional[str] = None
