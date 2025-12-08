"""Database models for Fiat Gateway."""

import enum

from infrastructure.db.session import Base
from sqlalchemy import Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Integer, Numeric, String
from sqlalchemy.sql import func


class TransactionType(str, enum.Enum):
    """Transaction type enumeration."""

    ON_RAMP = "on_ramp"  # Fiat -> Stablecoin
    OFF_RAMP = "off_ramp"  # Stablecoin -> Fiat


class TransactionStatus(str, enum.Enum):
    """Transaction status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PaymentProvider(str, enum.Enum):
    """Payment provider enumeration."""

    CIRCLE = "circle"
    STRIPE = "stripe"


class FiatTransaction(Base):
    """Fiat transaction record."""

    __tablename__ = "fiat_transactions"

    transaction_id = Column(String(128), primary_key=True)
    user_id = Column(String(128), nullable=False, index=True)
    type = Column(SQLEnum(TransactionType), nullable=False)
    amount = Column(Numeric(38, 18), nullable=False)
    currency = Column(String(10), nullable=False, default="USD")
    provider = Column(SQLEnum(PaymentProvider), nullable=False)
    status = Column(SQLEnum(TransactionStatus), nullable=False, default=TransactionStatus.PENDING)

    # On-ramp specific
    destination_address = Column(String(128))  # Wallet address for USDC
    payment_url = Column(String(512))  # Checkout URL

    # Off-ramp specific
    source_address = Column(String(128))  # Wallet sending stablecoin
    destination_account = Column(String(128))  # Bank account or payment method

    # Provider references
    provider_transaction_id = Column(String(128))  # Circle/Stripe transaction ID
    provider_response = Column(String(2048))  # JSON response from provider

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))
