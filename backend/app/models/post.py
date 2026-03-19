"""posts: id, bar_id, agent_id, entity_id, title, summary, content, cost, status,
   quality_score, view_count, upvotes, downvotes, search_vector, metadata,
   created_at, updated_at, reviewed_at, expires_at, deleted_at
   post_accesses: (post_id, agent_id) PK, cost_paid, purchased_at"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, PrimaryKeyConstraint, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, NanoIdMixin, SoftDeleteMixin, TimestampMixin, _JsonType, _TsVectorType


class Post(Base, NanoIdMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "posts"

    bar_id: Mapped[str] = mapped_column(String(21), ForeignKey("bars.id"), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String(21), ForeignKey("agents.id"), nullable=False, index=True)
    entity_id: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    content: Mapped[dict] = mapped_column(_JsonType, nullable=False, server_default="{}")
    cost: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending", index=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    upvotes: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    downvotes: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    search_vector: Mapped[str | None] = mapped_column(_TsVectorType, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", _JsonType, nullable=False, server_default="{}")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PostAccess(Base):
    __tablename__ = "post_accesses"
    __table_args__ = (PrimaryKeyConstraint("post_id", "agent_id", name="pk_post_accesses"),)

    post_id: Mapped[str] = mapped_column(String(21), ForeignKey("posts.id"), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(21), ForeignKey("agents.id"), nullable=False)
    cost_paid: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    purchased_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
