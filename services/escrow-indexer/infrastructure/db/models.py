"""
Database models for Escrow Indexer Service.
"""

from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Escrow(Base):
    """Escrow model - stores indexed escrow data."""

    __tablename__ = "escrows"

    # Primary key
    escrow_address = Column(String(42), primary_key=True)

    # Participants
    payer_address = Column(String(42), nullable=False, index=True)
    payee_address = Column(String(42), nullable=False, index=True)
    arbiter_address = Column(String(42), nullable=True, index=True)

    # Escrow details
    amount = Column(Numeric(78, 0), nullable=False)  # Wei amount (up to 78 digits for uint256)
    release_delay = Column(Integer, nullable=False)  # Seconds
    approvals_required = Column(Integer, nullable=False)  # 1-3

    # Status tracking
    status = Column(String(20), nullable=False, default="created", index=True)
    # Status values: created, approved, released, refunded

    # Blockchain metadata
    chain_id = Column(Integer, nullable=False)
    created_block = Column(BigInteger, nullable=False)
    created_tx = Column(String(66), nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    approvals = relationship("Approval", back_populates="escrow", cascade="all, delete-orphan")
    events = relationship("EscrowEvent", back_populates="escrow", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Escrow(address={self.escrow_address}, status={self.status}, payer={self.payer_address}, payee={self.payee_address})>"


class Approval(Base):
    """Approval model - tracks individual approvals for escrows."""

    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True, index=True)
    escrow_address = Column(
        String(42), ForeignKey("escrows.escrow_address"), nullable=False, index=True
    )
    approver_address = Column(String(42), nullable=False, index=True)

    # Blockchain metadata
    block_number = Column(BigInteger, nullable=False)
    tx_hash = Column(String(66), nullable=False, unique=True)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    escrow = relationship("Escrow", back_populates="approvals")

    def __repr__(self):
        return f"<Approval(escrow={self.escrow_address}, approver={self.approver_address})>"


class EscrowEvent(Base):
    """Event log - stores all escrow lifecycle events for audit trail."""

    __tablename__ = "escrow_events"

    id = Column(Integer, primary_key=True, index=True)
    escrow_address = Column(
        String(42), ForeignKey("escrows.escrow_address"), nullable=False, index=True
    )
    event_type = Column(String(50), nullable=False, index=True)
    # Event types: EscrowDeployed, EscrowCreated, Approved, EscrowReleased, EscrowRefunded

    # Event data (JSON-compatible fields)
    event_data = Column(String(2000), nullable=True)  # JSON string

    # Blockchain metadata
    block_number = Column(BigInteger, nullable=False, index=True)
    tx_hash = Column(String(66), nullable=False, index=True)
    chain_id = Column(Integer, nullable=False)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    escrow = relationship("Escrow", back_populates="events")

    def __repr__(self):
        return f"<EscrowEvent(escrow={self.escrow_address}, type={self.event_type}, block={self.block_number})>"


# Indexes for optimal query performance
Index("idx_escrows_payer_status", Escrow.payer_address, Escrow.status)
Index("idx_escrows_payee_status", Escrow.payee_address, Escrow.status)
Index("idx_escrows_arbiter_status", Escrow.arbiter_address, Escrow.status)
Index("idx_approvals_escrow", Approval.escrow_address)
Index("idx_events_escrow_type", EscrowEvent.escrow_address, EscrowEvent.event_type)
