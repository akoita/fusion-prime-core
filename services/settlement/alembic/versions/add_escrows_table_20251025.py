"""Add escrows table

Revision ID: add_escrows_table
Revises: c81a6c877761
Create Date: 2025-10-25 14:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_escrows_table"
down_revision: Union[str, Sequence[str], None] = "c81a6c877761"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add escrows table."""
    op.create_table(
        "escrows",
        sa.Column("address", sa.String(length=128), nullable=False),
        sa.Column("payer", sa.String(length=128), nullable=False),
        sa.Column("payee", sa.String(length=128), nullable=False),
        sa.Column("amount", sa.String(length=64), nullable=False),
        sa.Column("amount_numeric", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("asset_symbol", sa.String(length=64), server_default="ETH", nullable=True),
        sa.Column("chain_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="created", nullable=False),
        sa.Column("release_delay", sa.Integer(), nullable=True),
        sa.Column("approvals_required", sa.Integer(), nullable=True),
        sa.Column("approvals_count", sa.Integer(), server_default="0", nullable=True),
        sa.Column("arbiter", sa.String(length=128), nullable=True),
        sa.Column("transaction_hash", sa.String(length=128), nullable=True),
        sa.Column("block_number", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("address"),
    )

    # Create index on payer for faster queries
    op.create_index("ix_escrows_payer", "escrows", ["payer"])

    # Create index on payee for faster queries
    op.create_index("ix_escrows_payee", "escrows", ["payee"])

    # Create index on status for filtering
    op.create_index("ix_escrows_status", "escrows", ["status"])

    # Create index on chain_id for multi-chain support
    op.create_index("ix_escrows_chain_id", "escrows", ["chain_id"])


def downgrade() -> None:
    """Downgrade schema - drop escrows table."""
    op.drop_index("ix_escrows_chain_id", table_name="escrows")
    op.drop_index("ix_escrows_status", table_name="escrows")
    op.drop_index("ix_escrows_payee", table_name="escrows")
    op.drop_index("ix_escrows_payer", table_name="escrows")
    op.drop_table("escrows")
