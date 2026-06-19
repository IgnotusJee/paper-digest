"""Add degraded flag to digest history.

Revision ID: 0002_add_digest_history_degraded
Revises: 0001_initial_schema
Create Date: 2026-06-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_add_digest_history_degraded"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "digest_history",
        sa.Column("degraded", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("digest_history", "degraded", server_default=None)


def downgrade() -> None:
    op.drop_column("digest_history", "degraded")
