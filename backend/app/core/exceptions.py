from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.schemas.common import ErrorResponse


@dataclass
class AppError(Exception):
    code: int
    message: str
    detail: Any | None = None
    http_status: int = 400


def app_error_to_payload(exc: AppError) -> ErrorResponse:
    return ErrorResponse(code=exc.code, message=exc.message, detail=exc.detail)
