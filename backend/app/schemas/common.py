from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageMeta(BaseModel):
    cursor: str | None = None
    has_more: bool = False
    total: int | None = None


class Meta(BaseModel):
    page: PageMeta | None = None


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "ok"
    data: T | None = None
    meta: Meta | None = None


class ErrorResponse(BaseModel):
    code: int = Field(default=50000)
    message: str = Field(default="Internal server error")
    detail: Any | None = None
