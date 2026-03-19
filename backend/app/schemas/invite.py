from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CreateInviteRequest(BaseModel):
    label: str | None = Field(default=None, max_length=100)
    max_uses: int | None = Field(default=None, ge=1)
    target_user_id: str | None = None
    expires_at: datetime | None = None


class InviteResponse(BaseModel):
    id: str
    bar_id: str
    token: str
    label: str | None = None
    max_uses: int | None = None
    used_count: int = 0
    target_user_id: str | None = None
    expires_at: datetime | None = None
    created_at: datetime | None = None


class AddMemberRequest(BaseModel):
    agent_id: str = Field(min_length=1)
