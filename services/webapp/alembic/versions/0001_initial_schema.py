"""Initial schema — all 5 tables with constraints and indexes.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-03-15
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # users
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.Text, nullable=True),
        sa.Column("google_sub", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("google_sub", name="uq_users_google_sub"),
        sa.CheckConstraint(
            "password_hash IS NOT NULL OR google_sub IS NOT NULL",
            name="chk_users_has_auth",
        ),
    )

    # ------------------------------------------------------------------
    # password_reset_tokens
    # ------------------------------------------------------------------
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_password_reset_tokens_user_id"),
    )

    # ------------------------------------------------------------------
    # tracked_products
    # ------------------------------------------------------------------
    op.create_table(
        "tracked_products",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("product_name", sa.String(500), nullable=False),
        sa.Column("current_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("previous_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_tracked_products_user_id"),
        sa.UniqueConstraint("user_id", "url", name="uq_tracked_products_user_url"),
        sa.CheckConstraint("current_price >= 0", name="chk_tracked_products_current_price"),
        sa.CheckConstraint(
            "previous_price IS NULL OR previous_price >= 0",
            name="chk_tracked_products_previous_price",
        ),
    )

    # ------------------------------------------------------------------
    # notifications
    # ------------------------------------------------------------------
    op.create_table(
        "notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tracked_product_id", UUID(as_uuid=True), nullable=False),
        sa.Column("old_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("new_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_notifications_user_id"),
        sa.ForeignKeyConstraint(
            ["tracked_product_id"],
            ["tracked_products.id"],
            ondelete="CASCADE",
            name="fk_notifications_tracked_product_id",
        ),
        sa.CheckConstraint("new_price < old_price", name="chk_notifications_price_drop"),
        sa.CheckConstraint("old_price > 0", name="chk_notifications_old_price"),
        sa.CheckConstraint("new_price >= 0", name="chk_notifications_new_price"),
    )

    # ------------------------------------------------------------------
    # price_check_log
    # ------------------------------------------------------------------
    op.create_table(
        "price_check_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tracked_product_id", UUID(as_uuid=True), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("result", sa.String(10), nullable=False),
        sa.Column("retry_count", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.ForeignKeyConstraint(
            ["tracked_product_id"],
            ["tracked_products.id"],
            ondelete="CASCADE",
            name="fk_price_check_log_tracked_product_id",
        ),
        sa.CheckConstraint(
            "result IN ('success', 'failure')",
            name="chk_price_check_log_result",
        ),
        sa.CheckConstraint(
            "retry_count >= 0 AND retry_count <= 10",
            name="chk_price_check_log_retry_count",
        ),
        sa.CheckConstraint(
            "(result = 'success' AND error_message IS NULL) OR (result = 'failure' AND error_message IS NOT NULL)",
            name="chk_price_check_log_error_message",
        ),
    )

    # ------------------------------------------------------------------
    # Indexes
    # ------------------------------------------------------------------
    op.create_index("idx_users_google_sub", "users", ["google_sub"], unique=True)

    op.create_index("idx_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"])
    op.create_index("idx_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])

    op.create_index(
        "idx_tracked_products_user_id_created_at",
        "tracked_products",
        ["user_id", sa.text("created_at DESC")],
    )

    # Partial index — must use op.execute() for WHERE clause
    op.execute(
        "CREATE INDEX idx_notifications_user_id_unread_created_at "
        "ON notifications (user_id, created_at DESC) WHERE read_at IS NULL"
    )
    op.create_index("idx_notifications_user_id", "notifications", ["user_id"])
    op.create_index("idx_notifications_tracked_product_id", "notifications", ["tracked_product_id"])

    op.create_index("idx_price_check_log_tracked_product_id", "price_check_log", ["tracked_product_id"])
    op.create_index(
        "idx_price_check_log_result_checked_at",
        "price_check_log",
        ["result", sa.text("checked_at DESC")],
    )


def downgrade() -> None:
    # Drop indexes first
    op.drop_index("idx_price_check_log_result_checked_at", table_name="price_check_log")
    op.drop_index("idx_price_check_log_tracked_product_id", table_name="price_check_log")
    op.drop_index("idx_notifications_tracked_product_id", table_name="notifications")
    op.drop_index("idx_notifications_user_id", table_name="notifications")
    op.execute("DROP INDEX IF EXISTS idx_notifications_user_id_unread_created_at")
    op.drop_index("idx_tracked_products_user_id_created_at", table_name="tracked_products")
    op.drop_index("idx_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_index("idx_password_reset_tokens_token_hash", table_name="password_reset_tokens")
    op.drop_index("idx_users_google_sub", table_name="users")

    # Drop tables in reverse dependency order
    op.drop_table("price_check_log")
    op.drop_table("notifications")
    op.drop_table("tracked_products")
    op.drop_table("password_reset_tokens")
    op.drop_table("users")
