"""preferenze fiscali su investor_profiles (country, dividend_preference)

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("investor_profiles", sa.Column("country", sa.String(), nullable=False, server_default="Italia"))
    op.add_column("investor_profiles", sa.Column("dividend_preference", sa.String(), nullable=False, server_default="accumulazione"))


def downgrade() -> None:
    op.drop_column("investor_profiles", "dividend_preference")
    op.drop_column("investor_profiles", "country")
