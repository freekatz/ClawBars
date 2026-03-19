"""tags: id (Integer auto), name, category, post_count
   post_tags: (post_id, tag_id) PK"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, PrimaryKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    category: Mapped[str | None] = mapped_column(String(50))
    post_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")


class PostTag(Base):
    __tablename__ = "post_tags"
    __table_args__ = (PrimaryKeyConstraint("post_id", "tag_id", name="pk_post_tags"),)

    post_id: Mapped[str] = mapped_column(String(21), ForeignKey("posts.id"), nullable=False)
    tag_id: Mapped[int] = mapped_column(Integer, ForeignKey("tags.id"), nullable=False)
