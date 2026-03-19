"""users: id, email, password_hash, name, role, status, avatar_url, metadata, created_at, updated_at, deleted_at"""
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, NanoIdMixin, SoftDeleteMixin, TimestampMixin, _JsonType


class User(Base, NanoIdMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, server_default="free", index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="active", index=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    metadata_: Mapped[dict] = mapped_column("metadata", _JsonType, nullable=False, server_default="{}")
