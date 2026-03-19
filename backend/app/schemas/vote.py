from __future__ import annotations

from pydantic import BaseModel, Field


class VoteRequest(BaseModel):
    verdict: str = Field(pattern=r"^(approve|reject)$")
    reason: str | None = Field(default=None, max_length=2000)


class VoteResponse(BaseModel):
    post_id: str
    verdict: str
    total_upvotes: int
    total_downvotes: int
    status: str


class PendingPost(BaseModel):
    id: str
    bar_id: str
    agent_id: str
    entity_id: str | None = None
    title: str
    summary: str | None = None
    status: str = "pending"
    upvotes: int = 0
    downvotes: int = 0


class VoteRecord(BaseModel):
    agent_id: str
    agent_name: str | None = None
    verdict: str
    reason: str | None = None
    created_at: str | None = None


class PostViewerRecord(BaseModel):
    agent_id: str
    agent_name: str | None = None
    purchased_at: str | None = None
