"""activity_log: id (BigInteger auto), event_type, actor_id, target_type, target_id,
   payload, created_at, updated_at"""
from __future__ import annotations

from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, _JsonType


class ActivityLog(Base, TimestampMixin):
    __tablename__ = "activity_log"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    actor_id: Mapped[str | None] = mapped_column(String(21), index=True)
    target_type: Mapped[str | None] = mapped_column(String(30))
    target_id: Mapped[str | None] = mapped_column(String(21))
    payload: Mapped[dict] = mapped_column(_JsonType, nullable=False, server_default="{}")
