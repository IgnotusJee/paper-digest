"""Add fulltext_cn to papers.

Revision ID: 0003_add_paper_fulltext_cn
Revises: 0002_add_digest_history_degraded
Create Date: 2026-06-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = "0003_add_paper_fulltext_cn"
down_revision: Union[str, None] = "0002_add_digest_history_degraded"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "papers",
        sa.Column("fulltext_cn", mysql.LONGTEXT(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("papers", "fulltext_cn")
