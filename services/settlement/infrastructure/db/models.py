"""SQLAlchemy models for settlement commands and escrows."""

from __future__ import annotations

from sqlalchemy import TIMESTAMP, Boolean, Column, Integer, Numeric, String, Text, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class SettlementCommandRecord(Base):
    __tablename__ = "settlement_commands"

    command_id = Column(String(128), primary_key=True)
    workflow_id = Column(String(128), nullable=False)
    account_ref = Column(String(128), nullable=False)
    payer = Column(String(128))
    payee = Column(String(128))
    asset_symbol = Column(String(64))
    amount_numeric = Column(Numeric(38, 18))
    status = Column(String(32), nullable=False)
    last_updated = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class EscrowRecord(Base):
    """Represents an escrow contract tracked by the settlement service."""

    __tablename__ = "escrows"

    address = Column(String(128), primary_key=True)  # Escrow contract address
    payer = Column(String(128), nullable=False)  # Payer wallet address
    payee = Column(String(128), nullable=False)  # Payee wallet address
    amount = Column(String(64), nullable=False)  # Amount as string
    amount_numeric = Column(Numeric(38, 18))  # Amount as numeric for calculations
    asset_symbol = Column(String(64), default="ETH")  # Asset symbol (ETH, USDC, etc.)
    chain_id = Column(Integer, nullable=False)  # Blockchain chain ID
    status = Column(
        String(32), nullable=False, default="created"
    )  # created, approved, released, refunded
    release_delay = Column(Integer)  # Release delay in seconds
    approvals_required = Column(Integer)  # Number of approvals required
    approvals_count = Column(Integer, default=0)  # Current approval count
    arbiter = Column(String(128))  # Arbiter address if any
    transaction_hash = Column(String(128))  # Creation transaction hash
    block_number = Column(Integer)  # Block number when created
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class WebhookSubscriptionRecord(Base):
    """Represents a webhook subscription in the database."""

    __tablename__ = "webhook_subscriptions"

    subscription_id = Column(String(128), primary_key=True)
    url = Column(String(512), nullable=False)
    secret = Column(String(256), nullable=False)
    event_types = Column(Text, nullable=False)  # JSON array stored as text
    enabled = Column(Boolean, nullable=False, default=True)
    description = Column(String(512), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
