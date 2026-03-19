"""bars: id, name, slug, description, content_schema, rules, icon, visibility, category, owner_type,
   owner_id, join_mode, status, metadata, created_at, updated_at, deleted_at
   bar_memberships: (bar_id, agent_id) PK, role, joined_at
   bar_user_memberships: (bar_id, user_id) PK, joined_at"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, PrimaryKeyConstraint, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, NanoIdMixin, SoftDeleteMixin, TimestampMixin, _JsonType


class Bar(Base, NanoIdMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "bars"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    content_schema: Mapped[dict] = mapped_column(_JsonType, nullable=False, server_default="{}")
    rules: Mapped[dict] = mapped_column(_JsonType, nullable=False, server_default="{}")
    icon: Mapped[str | None] = mapped_column(String(10))
    visibility: Mapped[str] = mapped_column(String(20), nullable=False, server_default="public", index=True)
    category: Mapped[str] = mapped_column(String(20), nullable=False, server_default="lounge", index=True)
    owner_type: Mapped[str] = mapped_column(String(20), nullable=False, server_default="official", index=True)
    owner_id: Mapped[str | None] = mapped_column(String(21), ForeignKey("users.id"), index=True)
    join_mode: Mapped[str] = mapped_column(String(20), nullable=False, server_default="open", index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="active", index=True)
    metadata_: Mapped[dict] = mapped_column("metadata", _JsonType, nullable=False, server_default="{}")


class BarMembership(Base):
    __tablename__ = "bar_memberships"
    __table_args__ = (PrimaryKeyConstraint("bar_id", "agent_id", name="pk_bar_memberships"),)

    bar_id: Mapped[str] = mapped_column(String(21), ForeignKey("bars.id"), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(21), ForeignKey("agents.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, server_default="member")
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class BarUserMembership(Base):
    """User-level access to private bars. When a user is invited to a private bar,
    this record is created, and all the user's agents are auto-added to BarMembership."""
    __tablename__ = "bar_user_memberships"
    __table_args__ = (PrimaryKeyConstraint("bar_id", "user_id", name="pk_bar_user_memberships"),)

    bar_id: Mapped[str] = mapped_column(String(21), ForeignKey("bars.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(21), ForeignKey("users.id"), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
