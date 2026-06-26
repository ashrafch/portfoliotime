"""schema iniziale: users, simulation_records, price_cache, investor_profiles

Revision ID: 0001
Revises:
Create Date: 2026-06-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False, server_default=""),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "simulation_records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(), server_default="completed"),
        sa.Column("label", sa.String(), server_default=""),
        sa.Column("input_params", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("narrative", sa.String(), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_simulation_records_user_id", "simulation_records", ["user_id"])

    op.create_table(
        "price_cache",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(length=20), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("close_price", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.UniqueConstraint("ticker", "date", name="uq_price_cache_ticker_date"),
    )
    op.create_index("ix_price_cache_ticker", "price_cache", ["ticker"])

    op.create_table(
        "investor_profiles",
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("eta", sa.Integer(), server_default="40"),
        sa.Column("risk_profile", sa.String(), server_default="bilanciato"),
        sa.Column("base_currency", sa.String(length=3), server_default="EUR"),
        sa.Column("goal", sa.String(), server_default=""),
        sa.Column("default_tasso_fed", sa.Float(), server_default="5.25"),
        sa.Column("default_inflazione", sa.Float(), server_default="3.5"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("investor_profiles")
    op.drop_index("ix_price_cache_ticker", table_name="price_cache")
    op.drop_table("price_cache")
    op.drop_index("ix_simulation_records_user_id", table_name="simulation_records")
    op.drop_table("simulation_records")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
