from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import AppError
from app.deps import get_session
from app.models.agent import Agent
from app.models.user import User

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


def _create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: str) -> str:
    return _create_token(
        subject=user_id,
        token_type=TOKEN_TYPE_ACCESS,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(user_id: str) -> str:
    return _create_token(
        subject=user_id,
        token_type=TOKEN_TYPE_REFRESH,
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except jwt.PyJWTError as exc:
        raise AppError(code=40103, message="Invalid JWT token", http_status=401) from exc


async def get_current_agent(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> Agent | None:
    if not authorization:
        return None
    if not authorization.lower().startswith("bearer "):
        return None

    api_key = authorization[7:].strip()
    if not api_key:
        return None

    key_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
    result = await session.execute(
        select(Agent).where(Agent.api_key_hash == key_hash, Agent.status == "active")
    )
    agent = result.scalar_one_or_none()
    if agent is not None:
        agent.last_active_at = datetime.now(UTC)
    return agent


def require_agent(agent: Agent | None = Depends(get_current_agent)) -> Agent:
    if not agent:
        raise AppError(code=40101, message="API key required", http_status=401)
    return agent


async def get_current_user(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> User | None:
    if not authorization:
        return None
    if not authorization.lower().startswith("bearer "):
        return None  # Not a bearer token, likely something else

    token = authorization[7:].strip()
    try:
        payload = decode_token(token)
    except AppError:
        # Not a valid JWT (might be an agent API key), ignore
        return None

    if payload.get("type") != TOKEN_TYPE_ACCESS:
        return None  # Not an access token

    user_id = payload.get("sub")
    if not user_id:
        return None

    result = await session.execute(
        select(User).where(User.id == user_id, User.status == "active", User.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


def require_user(user: User | None = Depends(get_current_user)) -> User:
    if not user:
        raise AppError(code=40104, message="User authentication required", http_status=401)
    return user


def require_premium(user: User = Depends(require_user)) -> User:
    if user.role not in {"premium", "admin"}:
        raise AppError(code=40303, message="Premium role required", http_status=403)
    return user


async def require_admin(
    x_admin_key: str | None = Header(default=None),
    user: User | None = Depends(get_current_user),
) -> None:
    if x_admin_key and secrets.compare_digest(x_admin_key, settings.admin_api_key):
        return
    if user and user.role == "admin":
        return
    raise AppError(code=40302, message="Invalid admin permission", http_status=403)
