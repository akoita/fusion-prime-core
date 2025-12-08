"""
Database models for Risk Engine Service.
These models allow us to query escrow data from the settlement service's database
and persist margin health tracking data.
"""

from sqlalchemy import JSON, TIMESTAMP, Column, Integer, Numeric, String, Text, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class EscrowRecord(Base):
    """Represents an escrow contract from the settlement service database."""

    __tablename__ = "escrows"

    address = Column(String(128), primary_key=True)
    payer = Column(String(128), nullable=False)
    payee = Column(String(128), nullable=False)
    amount = Column(String(64), nullable=False)
    amount_numeric = Column(Numeric(38, 18))
    asset_symbol = Column(String(64), default="ETH")
    chain_id = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False, default="created")
    release_delay = Column(Integer)
    approvals_required = Column(Integer)
    approvals_count = Column(Integer, default=0)
    arbiter = Column(String(128))
    transaction_hash = Column(String(128))
    block_number = Column(Integer)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class MarginHealthSnapshot(Base):
    """Historical margin health snapshots for users."""

    __tablename__ = "margin_health_snapshots"

    snapshot_id = Column(String(128), primary_key=True)
    user_id = Column(String(128), nullable=False, index=True)
    health_score = Column(Numeric(10, 4), nullable=False)
    status = Column(String(32), nullable=False)  # HEALTHY, WARNING, MARGIN_CALL, LIQUIDATION
    total_collateral_usd = Column(Numeric(20, 8))
    total_borrow_usd = Column(Numeric(20, 8))
    collateral_breakdown = Column(JSON)  # Asset-wise collateral
    borrow_breakdown = Column(JSON)  # Asset-wise borrows
    liquidation_price_drop_percent = Column(Numeric(10, 4))
    previous_health_score = Column(Numeric(10, 4))
    calculated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class MarginEvent(Base):
    """Margin events (warnings, margin calls, liquidations)."""

    __tablename__ = "margin_events"

    event_id = Column(String(128), primary_key=True)
    user_id = Column(String(128), nullable=False, index=True)
    event_type = Column(
        String(64), nullable=False
    )  # health_warning, margin_call, liquidation_imminent
    severity = Column(String(32), nullable=False)  # medium, high, critical
    health_score = Column(Numeric(10, 4), nullable=False)
    previous_health_score = Column(Numeric(10, 4))
    threshold_breached = Column(Numeric(10, 4))
    message = Column(Text)
    recommendations = Column(JSON)  # Array of recommended actions
    collateral_usd = Column(Numeric(20, 8))
    borrow_usd = Column(Numeric(20, 8))
    published_to_pubsub = Column(String(16), default="false")  # "true" or "false"
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


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
