"""
Notification models for Alert Notification Service.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NotificationChannel(str, Enum):
    """Notification delivery channels."""

    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    PUSH = "push"  # Future


class NotificationSeverity(str, Enum):
    """Alert severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MarginAlert(BaseModel):
    """Margin alert message from Pub/Sub."""

    event_type: str  # margin_warning, margin_call, liquidation_imminent
    user_id: str
    health_score: float
    previous_health_score: Optional[float] = None
    status: str  # HEALTHY, WARNING, MARGIN_CALL, LIQUIDATION
    severity: str
    message: str
    total_collateral_usd: float
    total_borrow_usd: float
    liquidation_price_drop_percent: Optional[float] = None
    timestamp: str
    published_at: Optional[str] = None


class NotificationRequest(BaseModel):
    """User notification request."""

    user_id: str
    alert_type: str
    severity: str
    message: str
    channels: List[NotificationChannel]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NotificationResponse(BaseModel):
    """Notification delivery response."""

    notification_id: str
    user_id: str
    alert_type: str
    delivered_channels: List[str]
    failed_channels: List[str] = Field(default_factory=list)
    timestamp: str


class NotificationPreferences(BaseModel):
    """User notification preferences."""

    user_id: str
    enabled_channels: List[NotificationChannel] = Field(default_factory=list)
    alert_thresholds: Dict[str, float] = Field(default_factory=dict)
    email: Optional[str] = None
    phone: Optional[str] = None
    webhook_url: Optional[str] = None
    do_not_disturb_hours: Optional[tuple[int, int]] = None  # (start_hour, end_hour)
