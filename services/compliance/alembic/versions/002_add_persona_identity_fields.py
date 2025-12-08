"""Add Persona and Identity claim fields to KYC cases

Revision ID: 002
Revises: 001
Create Date: 2025-11-04 02:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Persona integration fields and identity claim references to kyc_cases table."""

    # Add Persona integration fields
    op.add_column("kyc_cases", sa.Column("persona_inquiry_id", sa.String(128), nullable=True))
    op.add_column("kyc_cases", sa.Column("persona_session_token", sa.String(256), nullable=True))
    op.add_column("kyc_cases", sa.Column("persona_status", sa.String(32), nullable=True))

    # Add identity claim reference fields for ERC-735 integration
    op.add_column("kyc_cases", sa.Column("kyc_claim_id", sa.String(128), nullable=True))
    op.add_column("kyc_cases", sa.Column("kyc_claim_tx_hash", sa.String(128), nullable=True))

    # Create index on persona_inquiry_id for webhook lookups
    op.create_index(
        "idx_kyc_cases_persona_inquiry_id", "kyc_cases", ["persona_inquiry_id"], unique=False
    )


def downgrade() -> None:
    """Remove Persona and identity claim fields from kyc_cases table."""

    # Drop index
    op.drop_index("idx_kyc_cases_persona_inquiry_id", table_name="kyc_cases")

    # Drop columns
    op.drop_column("kyc_cases", "kyc_claim_tx_hash")
    op.drop_column("kyc_cases", "kyc_claim_id")
    op.drop_column("kyc_cases", "persona_status")
    op.drop_column("kyc_cases", "persona_session_token")
    op.drop_column("kyc_cases", "persona_inquiry_id")
