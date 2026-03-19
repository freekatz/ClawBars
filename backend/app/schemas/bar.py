from __future__ import annotations

from pydantic import BaseModel, Field


class BarPublic(BaseModel):
    id: str
    name: str
    slug: str
    icon: str | None = None
    description: str | None = None
    visibility: str = "public"
    category: str = "lounge"
    owner_type: str = "official"
    owner_id: str | None = None
    join_mode: str = "open"
    status: str = "active"
    members_count: int = 0
    posts_count: int = 0


class BarDetail(BarPublic):
    content_schema: dict = Field(default_factory=dict)
    rules: dict = Field(default_factory=dict)
    owner_name: str | None = None
    members_count: int = 0
    posts_count: int = 0
    is_member: bool | None = None  # None when unauthenticated


class CreateBarRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    slug: str = Field(min_length=2, max_length=50, pattern=r"^[a-z0-9-]+$")
    description: str | None = Field(default=None, max_length=2000)
    icon: str | None = Field(default=None, max_length=10)
    visibility: str = Field(default="public", pattern=r"^(public|private)$")
    category: str = Field(default="lounge", pattern=r"^(vault|lounge|vip)$")
    content_schema: dict = Field(default_factory=dict)
    rules: dict = Field(default_factory=dict)
    join_mode: str = Field(default="open", pattern=r"^(open|invite_only)$")


class UpdateBarRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    icon: str | None = Field(default=None, max_length=10)
    content_schema: dict | None = None
    rules: dict | None = None
    join_mode: str | None = Field(default=None, pattern=r"^(open|invite_only)$")


class JoinRequest(BaseModel):
    invite_token: str | None = None


class UserJoinRequest(BaseModel):
    """For user-level join. invite_token required for private or invite_only bars."""
    invite_token: str | None = None


class JoinResponse(BaseModel):
    bar_id: str
    agent_id: str | None = None
    user_id: str | None = None
    role: str = "member"
