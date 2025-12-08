"""Add margin health persistence tables

Revision ID: 001
Revises:
Create Date: 2025-10-29

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create margin_health_snapshots table
    op.create_table(
        "margin_health_snapshots",
        sa.Column("snapshot_id", sa.String(128), primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=False, index=True),
        sa.Column("health_score", sa.Numeric(10, 4), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("total_collateral_usd", sa.Numeric(20, 8)),
        sa.Column("total_borrow_usd", sa.Numeric(20, 8)),
        sa.Column("collateral_breakdown", JSON),
        sa.Column("borrow_breakdown", JSON),
        sa.Column("liquidation_price_drop_percent", sa.Numeric(10, 4)),
        sa.Column("previous_health_score", sa.Numeric(10, 4)),
        sa.Column("calculated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )

    # Create margin_events table
    op.create_table(
        "margin_events",
        sa.Column("event_id", sa.String(128), primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=False, index=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("health_score", sa.Numeric(10, 4), nullable=False),
        sa.Column("previous_health_score", sa.Numeric(10, 4)),
        sa.Column("threshold_breached", sa.Numeric(10, 4)),
        sa.Column("message", sa.Text),
        sa.Column("recommendations", JSON),
        sa.Column("collateral_usd", sa.Numeric(20, 8)),
        sa.Column("borrow_usd", sa.Numeric(20, 8)),
        sa.Column("published_to_pubsub", sa.String(16), server_default="false"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )

    # Create alert_notifications table
    op.create_table(
        "alert_notifications",
        sa.Column("notification_id", sa.String(128), primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=False, index=True),
        sa.Column("alert_type", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("channels", JSON),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("delivery_details", JSON),
        sa.Column("margin_event_id", sa.String(128)),
        sa.Column("message_body", sa.Text),
        sa.Column("sent_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("delivered_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("failed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("failure_reason", sa.Text),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )

    # Create indexes for performance
    op.create_index(
        "idx_margin_snapshots_user_created", "margin_health_snapshots", ["user_id", "created_at"]
    )
    op.create_index("idx_margin_events_user_created", "margin_events", ["user_id", "created_at"])
    op.create_index(
        "idx_alert_notifications_user_created", "alert_notifications", ["user_id", "created_at"]
    )
    op.create_index("idx_margin_events_type_severity", "margin_events", ["event_type", "severity"])
    op.create_index("idx_alert_notifications_status", "alert_notifications", ["status"])


def downgrade():
    # Drop indexes
    op.drop_index("idx_alert_notifications_status")
    op.drop_index("idx_margin_events_type_severity")
    op.drop_index("idx_alert_notifications_user_created")
    op.drop_index("idx_margin_events_user_created")
    op.drop_index("idx_margin_snapshots_user_created")

    # Drop tables
    op.drop_table("alert_notifications")
    op.drop_table("margin_events")
    op.drop_table("margin_health_snapshots")
