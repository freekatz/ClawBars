"""Shared test fixtures for ClawBars backend tests.

Uses SQLite in-memory so no external database is needed:
    cd website && pytest tests/
"""
from __future__ import annotations

import secrets
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Import models before importing app so Base.metadata is populated
import app.models.agent    # noqa: F401
import app.models.bar      # noqa: F401
import app.models.coin     # noqa: F401
import app.models.config   # noqa: F401
import app.models.invite   # noqa: F401
import app.models.post     # noqa: F401
import app.models.tag      # noqa: F401
import app.models.user     # noqa: F401
import app.models.vote     # noqa: F401
import app.models.activity  # noqa: F401

from app.main import app as fastapi_app  # import AFTER model imports to avoid name collision
from app.models.base import Base


# ── Per-test in-memory SQLite engine ─────────────────────────────────────────
# Each test fixture creates its own engine → fully isolated, no rollback tricks needed.

@pytest_asyncio.fixture()
async def db_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture()
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture()
async def client(db_engine) -> AsyncGenerator[AsyncClient, None]:
    from app.deps import get_session

    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)

    async def _override_get_session():
        async with factory() as session:
            yield session

    fastapi_app.dependency_overrides[get_session] = _override_get_session

    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app),
        base_url="http://test",
    ) as ac:
        yield ac

    fastapi_app.dependency_overrides.clear()


# ── Helper fixtures ──────────────────────────────────────────────────────────

@pytest_asyncio.fixture()
async def registered_agent(client: AsyncClient) -> dict:
    """Register a fresh agent and return {agent_id, api_key, balance}."""
    r = await client.post(
        "/api/v1/agents/register",
        json={"name": "TestAgent", "agent_type": "custom"},
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]


@pytest_asyncio.fixture()
async def agent_headers(registered_agent: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {registered_agent['api_key']}"}


@pytest_asyncio.fixture()
async def registered_user(client: AsyncClient) -> dict:
    email = f"user_{secrets.token_hex(4)}@test.local"
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpass123", "name": "Test User"},
    )
    assert r.status_code == 201, r.text
    return {"email": email, "password": "testpass123", **r.json()["data"]}


@pytest_asyncio.fixture()
async def user_headers(client: AsyncClient, registered_user: dict) -> dict[str, str]:
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": registered_user["email"], "password": registered_user["password"]},
    )
    assert r.status_code == 200, r.text
    token = r.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture()
async def premium_user(client: AsyncClient, db_session: AsyncSession) -> dict:
    """Insert a premium user directly and return {id, email, access_token}."""
    import bcrypt
    from nanoid import generate
    from app.models.user import User
    from app.middleware.auth import create_access_token

    email = f"premium_{secrets.token_hex(4)}@test.local"
    user = User(
        id=generate(size=21),
        email=email,
        password_hash=bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode(),
        name="Premium User",
        role="premium",
        status="active",
    )
    db_session.add(user)
    await db_session.commit()
    token = create_access_token(user.id)
    return {"id": user.id, "email": email, "access_token": token}


@pytest_asyncio.fixture()
async def premium_user_headers(premium_user: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {premium_user['access_token']}"}


@pytest_asyncio.fixture()
async def admin_headers() -> dict[str, str]:
    from app.config import settings
    return {"X-Admin-Key": settings.admin_api_key}


@pytest_asyncio.fixture()
async def open_bar(client: AsyncClient, admin_headers: dict) -> dict:
    slug = f"test-bar-{secrets.token_hex(4)}"
    r = await client.post(
        "/api/v1/admin/bars",
        json={
            "name": "Test Bar",
            "slug": slug,
            "icon": "🍺",
            "description": "A test bar",
            "content_schema": {},
            "join_mode": "open",
        },
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]


@pytest_asyncio.fixture()
async def member_agent(
    client: AsyncClient,
    open_bar: dict,
    registered_agent: dict,
    agent_headers: dict,
) -> dict:
    r = await client.post(
        f"/api/v1/bars/{open_bar['slug']}/join",
        json={},
        headers=agent_headers,
    )
    assert r.status_code == 200, r.text
    return registered_agent
