"""Initial schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "digest_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("digest_date", sa.Date(), nullable=False),
        sa.Column("paper_ids", sa.JSON(), nullable=True),
        sa.Column("bucket_breakdown", sa.JSON(), nullable=True),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index(op.f("ix_digest_history_digest_date"), "digest_history", ["digest_date"], unique=False)

    op.create_table(
        "keywords",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("keyword", sa.String(length=128), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("keyword"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )

    op.create_table(
        "papers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("title_hash", sa.String(length=16), nullable=False),
        sa.Column("authors", sa.JSON(), nullable=True),
        sa.Column("venue", sa.String(length=32), nullable=True),
        sa.Column("venue_hint", sa.String(length=32), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("abstract_en", mysql.LONGTEXT(), nullable=True),
        sa.Column("abstract_cn", mysql.LONGTEXT(), nullable=True),
        sa.Column("summary_cn", sa.JSON(), nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("pdf_url", sa.Text(), nullable=True),
        sa.Column("arxiv_id", sa.String(length=32), nullable=True),
        sa.Column("doi", sa.String(length=128), nullable=True),
        sa.Column("citation_count", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("keyword_score", sa.Float(), nullable=False),
        sa.Column("personal_score", sa.Float(), nullable=False),
        sa.Column("prefilter_score", sa.Float(), nullable=False),
        sa.Column("llm_score", sa.Float(), nullable=True),
        sa.Column("final_score", sa.Float(), nullable=False),
        sa.Column("llm_reason", sa.Text(), nullable=True),
        sa.Column("bucket", sa.String(length=16), nullable=True),
        sa.Column("pushed", sa.Boolean(), nullable=False),
        sa.Column("pushed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index(op.f("ix_papers_arxiv_id"), "papers", ["arxiv_id"], unique=False)
    op.create_index(op.f("ix_papers_doi"), "papers", ["doi"], unique=False)
    op.create_index(op.f("ix_papers_pushed"), "papers", ["pushed"], unique=False)
    op.create_index(op.f("ix_papers_title_hash"), "papers", ["title_hash"], unique=True)
    op.create_index(op.f("ix_papers_venue"), "papers", ["venue"], unique=False)
    op.create_index(op.f("ix_papers_venue_hint"), "papers", ["venue_hint"], unique=False)

    op.create_table(
        "system_config",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=128), nullable=False),
        sa.Column("hashed_password", sa.String(length=256), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("notify_email", sa.Boolean(), nullable=False),
        sa.Column("daily_total", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )

    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("paper_id", sa.Integer(), nullable=False),
        sa.Column("tag_type", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["paper_id"], ["papers.id"]),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index(op.f("ix_tags_paper_id"), "tags", ["paper_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_tags_paper_id"), table_name="tags")
    op.drop_table("tags")
    op.drop_table("users")
    op.drop_table("system_config")
    op.drop_index(op.f("ix_papers_venue_hint"), table_name="papers")
    op.drop_index(op.f("ix_papers_venue"), table_name="papers")
    op.drop_index(op.f("ix_papers_title_hash"), table_name="papers")
    op.drop_index(op.f("ix_papers_pushed"), table_name="papers")
    op.drop_index(op.f("ix_papers_doi"), table_name="papers")
    op.drop_index(op.f("ix_papers_arxiv_id"), table_name="papers")
    op.drop_table("papers")
    op.drop_table("keywords")
    op.drop_index(op.f("ix_digest_history_digest_date"), table_name="digest_history")
    op.drop_table("digest_history")
