from __future__ import annotations

from dataclasses import dataclass

import bcrypt
from nanoid import generate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.middleware.auth import create_access_token, create_refresh_token, decode_token
from app.models.user import User
from app.schemas.user import LoginRequest, RegisterRequest, UpdateProfileRequest


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


@dataclass
class LoginResult:
    access_token: str
    refresh_token: str


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register(self, payload: RegisterRequest, role: str = "free") -> User:
        result = await self.session.execute(
            select(User).where(User.email == payload.email, User.deleted_at.is_(None))
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise AppError(code=40901, message="Email already registered", http_status=409)

        user = User(
            id=generate(size=21),
            email=payload.email,
            password_hash=_hash_password(payload.password),
            name=payload.name,
            role=role,
            status="active",
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def login(self, payload: LoginRequest) -> LoginResult:
        result = await self.session.execute(
            select(User).where(User.email == payload.email, User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()
        if not user or not _verify_password(payload.password, user.password_hash):
            raise AppError(code=40102, message="Invalid email or password", http_status=401)
        if user.status != "active":
            raise AppError(code=40303, message="Account is not active", http_status=403)

        return LoginResult(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
        )

    async def refresh(self, refresh_token: str) -> LoginResult:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise AppError(code=40103, message="Invalid refresh token", http_status=401)

        user_id = str(payload.get("sub", ""))
        result = await self.session.execute(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()
        if not user or user.status != "active":
            raise AppError(code=40104, message="User not found", http_status=401)

        return LoginResult(
            access_token=create_access_token(user_id),
            refresh_token=create_refresh_token(user_id),
        )

    async def get_profile(self, user_id: str) -> User:
        result = await self.session.execute(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()
        if not user:
            raise AppError(code=40401, message="User not found", http_status=404)
        return user

    async def update_profile(self, user_id: str, payload: UpdateProfileRequest) -> User:
        user = await self.get_profile(user_id)
        if payload.name is not None:
            user.name = payload.name
        if payload.avatar_url is not None:
            user.avatar_url = payload.avatar_url
        await self.session.flush()
        return user
