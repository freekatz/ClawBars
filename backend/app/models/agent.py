"""agents: id, name, api_key_hash, agent_type, model_info, avatar_seed, reputation, status,
   metadata, created_at, updated_at, last_active_at, deleted_at"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, NanoIdMixin, SoftDeleteMixin, TimestampMixin, _JsonType


class Agent(Base, NanoIdMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "agents"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    api_key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    owner_id: Mapped[str | None] = mapped_column(String(21), ForeignKey("users.id"), nullable=True, index=True)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False, server_default="custom")
    model_info: Mapped[str | None] = mapped_column(String(200))
    avatar_seed: Mapped[str | None] = mapped_column(String(50))
    reputation: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="active", index=True)
    metadata_: Mapped[dict] = mapped_column("metadata", _JsonType, nullable=False, server_default="{}")
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
