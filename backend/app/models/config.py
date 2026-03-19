"""system_configs: key (PK), value, description, category, updated_by, created_at, updated_at
   bar_configs: id, bar_id, key, value, description, created_at, updated_at"""
from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, NanoIdMixin, TimestampMixin, _JsonType


class SystemConfig(Base, TimestampMixin):
    __tablename__ = "system_configs"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict] = mapped_column(_JsonType, nullable=False, server_default="{}")
    description: Mapped[str | None] = mapped_column(String(500))
    category: Mapped[str | None] = mapped_column(String(50))
    updated_by: Mapped[str | None] = mapped_column(String(21))


class BarConfig(Base, NanoIdMixin, TimestampMixin):
    __tablename__ = "bar_configs"
    __table_args__ = (UniqueConstraint("bar_id", "key", name="uq_bar_config_bar_key"),)

    bar_id: Mapped[str] = mapped_column(String(21), ForeignKey("bars.id"), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[dict] = mapped_column(_JsonType, nullable=False, server_default="{}")
    description: Mapped[str | None] = mapped_column(String(500))
