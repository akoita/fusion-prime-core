"""Initial migration

Revision ID: c81a6c877761
Revises:
Create Date: 2025-10-25 06:39:40.887590

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c81a6c877761"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create settlement_commands table
    op.create_table(
        "settlement_commands",
        sa.Column("command_id", sa.String(length=128), nullable=False),
        sa.Column("workflow_id", sa.String(length=128), nullable=False),
        sa.Column("account_ref", sa.String(length=128), nullable=False),
        sa.Column("payer", sa.String(length=128), nullable=True),
        sa.Column("payee", sa.String(length=128), nullable=True),
        sa.Column("asset_symbol", sa.String(length=64), nullable=True),
        sa.Column("amount_numeric", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "last_updated",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("command_id"),
    )

    # Create webhook_subscriptions table
    op.create_table(
        "webhook_subscriptions",
        sa.Column("subscription_id", sa.String(length=128), nullable=False),
        sa.Column("url", sa.String(length=512), nullable=False),
        sa.Column("secret", sa.String(length=256), nullable=False),
        sa.Column("event_types", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("subscription_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("webhook_subscriptions")
    op.drop_table("settlement_commands")
