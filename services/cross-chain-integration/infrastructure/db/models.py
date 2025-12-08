"""Database models for Cross-Chain Integration Service."""

import enum

from infrastructure.db.session import Base
from sqlalchemy import JSON, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Integer, Numeric, String
from sqlalchemy.sql import func


class MessageStatus(str, enum.Enum):
    """Message status enumeration."""

    PENDING = "pending"
    SENT = "sent"
    CONFIRMED = "confirmed"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


class BridgeProtocol(str, enum.Enum):
    """Bridge protocol enumeration."""

    AXELAR = "axelar"
    CCIP = "ccip"


class CrossChainMessage(Base):
    """Cross-chain message record."""

    __tablename__ = "cross_chain_messages"

    message_id = Column(String(128), primary_key=True)
    source_chain = Column(String(32), nullable=False)
    destination_chain = Column(String(32), nullable=False)
    source_address = Column(String(128), nullable=False)
    destination_address = Column(String(128), nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(SQLEnum(MessageStatus), nullable=False, default=MessageStatus.PENDING)
    protocol = Column(SQLEnum(BridgeProtocol, native_enum=False), nullable=False)

    # Transaction details
    transaction_hash = Column(String(128))
    block_number = Column(Integer)
    gas_used = Column(Integer)

    # Message details
    nonce = Column(Integer)  # Replay protection
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # Finality tracking
    source_chain_confirmed = Column(DateTime(timezone=True))
    destination_chain_confirmed = Column(DateTime(timezone=True))
    delivery_estimated_at = Column(DateTime(timezone=True))

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))


class CollateralSnapshot(Base):
    """Aggregated collateral snapshot across chains."""

    __tablename__ = "collateral_snapshots"

    snapshot_id = Column(String(128), primary_key=True)
    user_id = Column(String(128), nullable=False, index=True)
    total_collateral_usd = Column(Numeric(38, 18), nullable=False)
    chains_data = Column(JSON, nullable=False)  # {chain: {asset: amount, ...}}

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SettlementRecord(Base):
    """Cross-chain settlement record."""

    __tablename__ = "settlement_records"

    settlement_id = Column(String(128), primary_key=True)
    source_chain = Column(String(32), nullable=False)
    destination_chain = Column(String(32), nullable=False)
    amount = Column(Numeric(38, 18), nullable=False)
    asset = Column(String(16), nullable=False)
    source_address = Column(String(128), nullable=False)
    destination_address = Column(String(128), nullable=False)
    protocol = Column(SQLEnum(BridgeProtocol, native_enum=False), nullable=False)

    status = Column(String(32), nullable=False, default="pending")
    message_id = Column(String(128))  # Reference to cross_chain_messages

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))
