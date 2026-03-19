"""bar_invites: id, bar_id, created_by, token, label, max_uses, used_count,
   target_user_id, expires_at, created_at, updated_at"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, NanoIdMixin, TimestampMixin


class BarInvite(Base, NanoIdMixin, TimestampMixin):
    __tablename__ = "bar_invites"

    bar_id: Mapped[str] = mapped_column(String(21), ForeignKey("bars.id"), nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(21), ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    label: Mapped[str | None] = mapped_column(String(100))
    max_uses: Mapped[int | None] = mapped_column(Integer)
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    target_user_id: Mapped[str | None] = mapped_column(String(21), ForeignKey("users.id"))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
