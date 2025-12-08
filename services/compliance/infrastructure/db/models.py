"""
Database models for Compliance Service.
Stores compliance cases, KYC data, AML checks, and sanctions screening results.
"""

from sqlalchemy import JSON, TIMESTAMP, Boolean, Column, Integer, Numeric, String, Text, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class KYCCase(Base):
    """KYC (Know Your Customer) verification case."""

    __tablename__ = "kyc_cases"

    case_id = Column(String(128), primary_key=True)
    user_id = Column(String(128), nullable=False)
    document_type = Column(String(64), nullable=False)
    document_data = Column(JSON)
    personal_info = Column(JSON)
    status = Column(
        String(32), nullable=False, default="pending"
    )  # pending, verified, rejected, review
    verification_score = Column(Numeric(5, 2))
    required_actions = Column(JSON)  # Array of action strings

    # Persona integration fields
    persona_inquiry_id = Column(String(128))  # Persona inquiry ID
    persona_session_token = Column(String(256))  # Session token for embedded flow
    persona_status = Column(String(32))  # Persona inquiry status

    # Identity claim references (for ERC-735 integration)
    kyc_claim_id = Column(String(128))  # On-chain claim ID
    kyc_claim_tx_hash = Column(String(128))  # Blockchain transaction hash

    reviewer_id = Column(String(128))  # Compliance officer who reviewed
    reviewed_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class AMLAlert(Base):
    """AML (Anti-Money Laundering) alert."""

    __tablename__ = "aml_alerts"

    alert_id = Column(String(128), primary_key=True)
    user_id = Column(String(128), nullable=False)
    transaction_id = Column(String(128))
    transaction_amount = Column(Numeric(18, 8))
    transaction_type = Column(String(64))
    source_address = Column(String(128))
    destination_address = Column(String(128))
    risk_score = Column(Numeric(5, 4))
    risk_level = Column(String(32))  # low, medium, high, critical
    flags = Column(JSON)  # Array of flag strings
    recommendations = Column(JSON)  # Array of recommendation strings
    status = Column(
        String(32), nullable=False, default="open"
    )  # open, investigating, resolved, false_positive
    assigned_to = Column(String(128))  # Compliance officer assigned
    investigated_at = Column(TIMESTAMP(timezone=True))
    resolved_at = Column(TIMESTAMP(timezone=True))
    resolution_notes = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class SanctionsCheck(Base):
    """Sanctions list screening check."""

    __tablename__ = "sanctions_checks"

    check_id = Column(String(128), primary_key=True)
    user_id = Column(String(128))
    address = Column(String(128), nullable=False)
    network = Column(String(32))  # ethereum, polygon, etc.
    matches = Column(JSON)  # Array of sanctions list matches
    risk_level = Column(String(32))  # none, low, medium, high
    checked_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class ComplianceCase(Base):
    """General compliance case for case management."""

    __tablename__ = "compliance_cases"

    case_id = Column(String(128), primary_key=True)
    user_id = Column(String(128), nullable=False)
    case_type = Column(String(64), nullable=False)  # kyc, aml, sanctions, general
    status = Column(
        String(32), nullable=False, default="open"
    )  # open, investigating, resolved, closed
    priority = Column(String(32), default="normal")  # low, normal, high, urgent
    title = Column(String(256))
    description = Column(Text)
    case_metadata = Column(JSON)  # Additional case-specific data
    assigned_to = Column(String(128))
    created_by = Column(String(128))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    resolved_at = Column(TIMESTAMP(timezone=True))
    resolution = Column(Text)


class ComplianceCheck(Base):
    """Specific compliance check (linked to escrow/transaction)."""

    __tablename__ = "compliance_checks"

    check_id = Column(String(128), primary_key=True)
    check_type = Column(String(64), nullable=False)  # kyc, aml, sanctions, kyb
    escrow_address = Column(String(128))
    user_id = Column(String(128))
    transaction_hash = Column(String(128))
    status = Column(String(32), nullable=False)  # passed, pending, flagged, failed
    score = Column(Numeric(5, 4))
    risk_score = Column(Numeric(5, 4))
    flags = Column(JSON)
    notes = Column(Text)
    check_metadata = Column(JSON)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    checked_at = Column(TIMESTAMP(timezone=True))
