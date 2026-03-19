from __future__ import annotations

from datetime import datetime, timezone

from nanoid import generate
from sqlalchemy import DateTime, JSON, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

try:
    from sqlalchemy.dialects.postgresql import JSONB
    _JsonType = JSON().with_variant(JSONB(), "postgresql")
except ImportError:
    _JsonType = JSON()

try:
    from sqlalchemy.dialects.postgresql import TSVECTOR
    _TsVectorType = Text().with_variant(TSVECTOR(), "postgresql")
except ImportError:
    _TsVectorType = Text()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class NanoIdMixin:
    id: Mapped[str] = mapped_column(String(21), primary_key=True, default=lambda: generate(size=21))


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
