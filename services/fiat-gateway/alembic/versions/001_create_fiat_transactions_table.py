"""Create fiat_transactions table

Revision ID: 001_create_fiat_transactions
Revises:
Create Date: 2025-11-02 15:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_create_fiat_transactions"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types (PostgreSQL) using SQLAlchemy ENUM
    # Use try/except to handle existing types gracefully
    connection = op.get_bind()

    def create_enum_if_not_exists(enum_name: str, values: list[str]) -> None:
        """Create ENUM type if it doesn't exist using raw SQL (avoids SQLAlchemy events)."""
        try:
            # Check if type exists first
            result = connection.execute(
                sa.text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = :enum_name)"),
                {"enum_name": enum_name},
            )
            if result.scalar():
                print(f"✓ Enum type '{enum_name}' already exists")
                return

            # Type doesn't exist, create it using raw SQL
            # This avoids SQLAlchemy's event system which can cause duplicate errors
            values_str = ", ".join(f"'{v}'" for v in values)
            op.execute(f"CREATE TYPE {enum_name} AS ENUM ({values_str})")
            print(f"✓ Created enum type: {enum_name}")
        except Exception as e:
            # If it already exists (race condition), that's fine - migration can be re-run
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print(f"✓ Enum type '{enum_name}' already exists (ignoring duplicate)")
            else:
                # Re-raise if it's a different error
                raise

    # Create ENUM types explicitly before using them in tables
    # Use raw SQL to avoid SQLAlchemy event system issues
    create_enum_if_not_exists("transactiontype", ["on_ramp", "off_ramp"])
    create_enum_if_not_exists(
        "transactionstatus", ["pending", "processing", "completed", "failed", "cancelled"]
    )
    create_enum_if_not_exists("paymentprovider", ["circle", "stripe"])

    # Define ENUM objects for use in table columns
    transaction_type_enum = postgresql.ENUM(
        "on_ramp", "off_ramp", name="transactiontype", create_type=False
    )
    transaction_status_enum = postgresql.ENUM(
        "pending",
        "processing",
        "completed",
        "failed",
        "cancelled",
        name="transactionstatus",
        create_type=False,
    )
    payment_provider_enum = postgresql.ENUM(
        "circle", "stripe", name="paymentprovider", create_type=False
    )

    # Create fiat_transactions table
    # Use the pre-created ENUM types (prevents SQLAlchemy from trying to create them again)
    op.create_table(
        "fiat_transactions",
        sa.Column("transaction_id", sa.String(128), primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=False),
        sa.Column("type", transaction_type_enum, nullable=False),
        sa.Column("amount", sa.Numeric(38, 18), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("provider", payment_provider_enum, nullable=False),
        sa.Column("status", transaction_status_enum, nullable=False, server_default="pending"),
        sa.Column("destination_address", sa.String(128), nullable=True),
        sa.Column("payment_url", sa.String(512), nullable=True),
        sa.Column("source_address", sa.String(128), nullable=True),
        sa.Column("destination_account", sa.String(128), nullable=True),
        sa.Column("provider_transaction_id", sa.String(128), nullable=True),
        sa.Column("provider_response", sa.String(2048), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create index on user_id
    op.create_index("ix_fiat_transactions_user_id", "fiat_transactions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_fiat_transactions_user_id", table_name="fiat_transactions")
    op.drop_table("fiat_transactions")
    op.execute("DROP TYPE IF EXISTS transactionstatus")
    op.execute("DROP TYPE IF EXISTS transactiontype")
    op.execute("DROP TYPE IF EXISTS paymentprovider")
