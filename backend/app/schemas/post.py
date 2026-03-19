from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CreatePostRequest(BaseModel):
    entity_id: str | None = Field(default=None, max_length=200)
    title: str = Field(min_length=2, max_length=500)
    summary: str | None = None
    content: dict
    cost: int | None = Field(default=None, ge=0)


class PostPreview(BaseModel):
    id: str
    bar_id: str
    bar_slug: str | None = None
    bar_category: str | None = None
    bar_visibility: str | None = None
    agent_id: str
    entity_id: str | None
    title: str
    summary: str | None
    status: str
    upvotes: int = 0
    downvotes: int = 0
    view_count: int = 0
    cost: int | None = None
    created_at: datetime | None = None


class PostFull(PostPreview):
    content: dict
    cost: int | None = None
    quality_score: float | None = None


class PostList(BaseModel):
    items: list[PostPreview]
    next_cursor: str | None = None


class PostSuggest(BaseModel):
    id: str
    title: str
    bar_id: str
    bar_slug: str | None = None
    bar_category: str | None = None
    bar_visibility: str | None = None
