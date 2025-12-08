"""Create cross_chain_messages and related tables

Revision ID: 001_create_cross_chain_tables
Revises:
Create Date: 2025-11-02 22:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_create_cross_chain_tables"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types (PostgreSQL) using raw SQL (avoids SQLAlchemy events)
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
    create_enum_if_not_exists(
        "messagestatus", ["pending", "sent", "confirmed", "delivered", "failed", "retrying"]
    )
    create_enum_if_not_exists("bridgeprotocol", ["axelar", "ccip"])

    # Define ENUM objects for use in table columns (create_type=False since we created manually)
    message_status_enum = postgresql.ENUM(
        "pending",
        "sent",
        "confirmed",
        "delivered",
        "failed",
        "retrying",
        name="messagestatus",
        create_type=False,
    )
    bridge_protocol_enum = postgresql.ENUM(
        "axelar", "ccip", name="bridgeprotocol", create_type=False
    )

    # Create cross_chain_messages table
    op.create_table(
        "cross_chain_messages",
        sa.Column("message_id", sa.String(128), primary_key=True),
        sa.Column("source_chain", sa.String(32), nullable=False),
        sa.Column("destination_chain", sa.String(32), nullable=False),
        sa.Column("source_address", sa.String(128), nullable=False),
        sa.Column("destination_address", sa.String(128), nullable=False),
        sa.Column("payload", postgresql.JSON, nullable=False),
        sa.Column("status", message_status_enum, nullable=False, server_default="pending"),
        sa.Column("protocol", bridge_protocol_enum, nullable=False),
        # Transaction details
        sa.Column("transaction_hash", sa.String(128)),
        sa.Column("block_number", sa.Integer),
        sa.Column("gas_used", sa.Integer),
        # Message details
        sa.Column("nonce", sa.Integer),
        sa.Column("retry_count", sa.Integer, server_default="0"),
        sa.Column("max_retries", sa.Integer, server_default="3"),
        # Finality tracking
        sa.Column("source_chain_confirmed", sa.DateTime(timezone=True)),
        sa.Column("destination_chain_confirmed", sa.DateTime(timezone=True)),
        sa.Column("delivery_estimated_at", sa.DateTime(timezone=True)),
        # Metadata
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )

    # Create collateral_snapshots table
    op.create_table(
        "collateral_snapshots",
        sa.Column("snapshot_id", sa.String(128), primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=False, index=True),
        sa.Column("total_collateral_usd", sa.Numeric(38, 18), nullable=False),
        sa.Column("chains_data", postgresql.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # Create settlement_records table
    op.create_table(
        "settlement_records",
        sa.Column("settlement_id", sa.String(128), primary_key=True),
        sa.Column("source_chain", sa.String(32), nullable=False),
        sa.Column("destination_chain", sa.String(32), nullable=False),
        sa.Column("amount", sa.Numeric(38, 18), nullable=False),
        sa.Column("asset", sa.String(16), nullable=False),
        sa.Column("source_address", sa.String(128), nullable=False),
        sa.Column("destination_address", sa.String(128), nullable=False),
        sa.Column("protocol", bridge_protocol_enum, nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("message_id", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )

    # Create indexes (with IF NOT EXISTS check)
    connection = op.get_bind()

    def create_index_if_not_exists(index_name: str, table_name: str, columns: list[str]) -> None:
        """Create index if it doesn't exist."""
        try:
            result = connection.execute(
                sa.text("SELECT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = :index_name)"),
                {"index_name": index_name},
            )
            if result.scalar():
                print(f"✓ Index '{index_name}' already exists")
                return

            # Index doesn't exist, create it
            columns_str = ", ".join(columns)
            op.execute(f"CREATE INDEX {index_name} ON {table_name} ({columns_str})")
            print(f"✓ Created index: {index_name}")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print(f"✓ Index '{index_name}' already exists (ignoring duplicate)")
            else:
                raise

    # Note: collateral_snapshots.user_id already has index=True in column definition
    # So we only create the explicit index if the table exists but index doesn't
    create_index_if_not_exists("ix_cross_chain_messages_status", "cross_chain_messages", ["status"])
    # Check if table exists before creating index (since user_id column has index=True)
    result = connection.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'collateral_snapshots')"
        )
    )
    if result.scalar():
        # Table exists, check if index exists
        create_index_if_not_exists(
            "ix_collateral_snapshots_user_id", "collateral_snapshots", ["user_id"]
        )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_collateral_snapshots_user_id", table_name="collateral_snapshots")
    op.drop_index("ix_cross_chain_messages_status", table_name="cross_chain_messages")

    # Drop tables
    op.drop_table("settlement_records")
    op.drop_table("collateral_snapshots")
    op.drop_table("cross_chain_messages")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS bridgeprotocol")
    op.execute("DROP TYPE IF EXISTS messagestatus")
