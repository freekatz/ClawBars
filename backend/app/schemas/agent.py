from __future__ import annotations

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    agent_type: str = Field(default="custom", max_length=50)
    model_info: str | None = Field(default=None, max_length=200)


class RegisterResponse(BaseModel):
    agent_id: str
    api_key: str
    balance: int


class AgentPublic(BaseModel):
    id: str
    name: str
    owner_id: str | None = None
    owner_name: str | None = None
    agent_type: str
    model_info: str | None = None
    avatar_seed: str | None = None
    reputation: int = 0
    status: str = "active"


class AgentDetail(AgentPublic):
    balance: int = 0
