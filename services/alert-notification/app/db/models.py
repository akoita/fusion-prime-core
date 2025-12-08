"""
Database models for Alert Notification Service.

The alert_notifications table lives in the Risk Engine database and tracks
notification delivery history.
"""

from sqlalchemy import JSON, TIMESTAMP, Column, String, Text, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class AlertNotification(Base):
    """Alert notification delivery tracking."""

    __tablename__ = "alert_notifications"

    notification_id = Column(String(128), primary_key=True)
    user_id = Column(String(128), nullable=False, index=True)
    alert_type = Column(String(64), nullable=False)  # margin_call, liquidation, health_warning
    severity = Column(String(32), nullable=False)
    channels = Column(JSON)  # Array of channels used: ["email", "sms", "webhook"]
    status = Column(String(32), nullable=False)  # sent, delivered, failed, pending
    delivery_details = Column(JSON)  # Channel-specific delivery results
    margin_event_id = Column(String(128))  # Link to margin event
    message_body = Column(Text)
    sent_at = Column(TIMESTAMP(timezone=True))
    delivered_at = Column(TIMESTAMP(timezone=True))
    failed_at = Column(TIMESTAMP(timezone=True))
    failure_reason = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
