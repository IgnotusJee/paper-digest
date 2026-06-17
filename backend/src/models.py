from datetime import UTC, datetime, date
from typing import Optional
from sqlalchemy import String, Text, Boolean, Integer, Float, Date, DateTime, JSON, ForeignKey
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


LONG_TEXT = Text().with_variant(mysql.LONGTEXT(), "mysql")


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(128), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(256), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_email: Mapped[bool] = mapped_column(Boolean, default=True)
    daily_total: Mapped[int] = mapped_column(Integer, default=6)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    title_hash: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    authors: Mapped[Optional[list]] = mapped_column(JSON)
    venue: Mapped[Optional[str]] = mapped_column(String(32), index=True)
    venue_hint: Mapped[Optional[str]] = mapped_column(String(32), index=True)
    year: Mapped[Optional[int]] = mapped_column(Integer)
    abstract_en: Mapped[Optional[str]] = mapped_column(LONG_TEXT)
    abstract_cn: Mapped[Optional[str]] = mapped_column(LONG_TEXT)
    summary_cn: Mapped[Optional[dict]] = mapped_column(JSON)
    comments: Mapped[Optional[str]] = mapped_column(Text)
    url: Mapped[Optional[str]] = mapped_column(Text)
    pdf_url: Mapped[Optional[str]] = mapped_column(Text)
    arxiv_id: Mapped[Optional[str]] = mapped_column(String(32), index=True)
    doi: Mapped[Optional[str]] = mapped_column(String(128), index=True)
    citation_count: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(16), nullable=False)  # arxiv/dblp/manual
    keyword_score: Mapped[float] = mapped_column(Float, default=0.0)
    personal_score: Mapped[float] = mapped_column(Float, default=0.5)
    prefilter_score: Mapped[float] = mapped_column(Float, default=0.0)
    llm_score: Mapped[Optional[float]] = mapped_column(Float)
    final_score: Mapped[float] = mapped_column(Float, default=0.0)
    llm_reason: Mapped[Optional[str]] = mapped_column(Text)
    bucket: Mapped[Optional[str]] = mapped_column(String(16))  # venue/arxiv
    pushed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    pushed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    tags: Mapped[list["Tag"]] = relationship("Tag", back_populates="paper", cascade="all, delete-orphan")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    paper_id: Mapped[int] = mapped_column(Integer, ForeignKey("papers.id"), index=True)
    tag_type: Mapped[str] = mapped_column(String(16), nullable=False)  # interested/not_interested/read_later
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    paper: Mapped["Paper"] = relationship("Paper", back_populates="tags")


class Keyword(Base):
    __tablename__ = "keywords"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    keyword: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    category: Mapped[str] = mapped_column(String(32), default="topic")
    aliases: Mapped[Optional[list]] = mapped_column(JSON)
    source: Mapped[str] = mapped_column(String(16), default="manual")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class DigestHistory(Base):
    __tablename__ = "digest_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    digest_date: Mapped[date] = mapped_column(Date, index=True)
    paper_ids: Mapped[Optional[list]] = mapped_column(JSON)
    bucket_breakdown: Mapped[Optional[dict]] = mapped_column(JSON)
    channel: Mapped[str] = mapped_column(String(16), default="email")
    status: Mapped[str] = mapped_column(String(16), default="sent")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class SystemConfig(Base):
    __tablename__ = "system_config"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)
