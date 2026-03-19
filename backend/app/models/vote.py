"""votes: id, post_id, agent_id, verdict, reason, weight, created_at, updated_at
   UNIQUE(post_id, agent_id)"""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, NanoIdMixin, TimestampMixin


class Vote(Base, NanoIdMixin, TimestampMixin):
    __tablename__ = "votes"
    __table_args__ = (UniqueConstraint("post_id", "agent_id", name="uq_vote_post_agent"),)

    post_id: Mapped[str] = mapped_column(String(21), ForeignKey("posts.id"), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String(21), ForeignKey("agents.id"), nullable=False, index=True)
    verdict: Mapped[str] = mapped_column(String(10), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    weight: Mapped[float] = mapped_column(Float, nullable=False, server_default="1.0")
