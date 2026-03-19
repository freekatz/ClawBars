"""C5: Owner bar lifecycle tests."""
import secrets

import pytest
from httpx import AsyncClient


async def test_create_bar_with_content_schema(client: AsyncClient, premium_user_headers: dict):
    """Premium user creates bar with content_schema; schema is stored."""
    slug = f"own-bar-{secrets.token_hex(4)}"
    schema = {
        "type": "object",
        "required": ["title", "body"],
        "properties": {
            "title": {"type": "string"},
            "body": {"type": "string"},
        },
    }
    r = await client.post(
        "/api/v1/owner/bars",
        json={"name": "OwnBar", "slug": slug, "content_schema": schema, "join_mode": "open", "visibility": "private"},
        headers=premium_user_headers,
    )
    assert r.status_code == 201
    bar = r.json()["data"]
    assert bar["content_schema"]["required"] == ["title", "body"]


async def test_schema_enforced_on_post(client: AsyncClient, premium_user_headers: dict, admin_headers: dict):
    """Posts that don't match content_schema are rejected."""
    slug = f"schema-bar-{secrets.token_hex(4)}"
    schema = {
        "type": "object",
        "required": ["analysis"],
        "properties": {"analysis": {"type": "string", "minLength": 10}},
    }
    r = await client.post(
        "/api/v1/owner/bars",
        json={"name": "SchemaBar", "slug": slug, "content_schema": schema, "join_mode": "open", "visibility": "private"},
        headers=premium_user_headers,
    )
    assert r.status_code == 201

    # Register agent under premium user (gets owner_id + auto-joins private bar)
    r_agent = await client.post("/api/v1/agents/register", json={"name": "SchemaAgent"}, headers=premium_user_headers)
    agent_h = {"Authorization": f"Bearer {r_agent.json()['data']['api_key']}"}

    # Missing required field
    r_bad = await client.post(
        f"/api/v1/bars/{slug}/posts",
        json={"title": "Bad", "content": {"other": "stuff"}},
        headers=agent_h,
    )
    assert r_bad.status_code == 400

    # Valid content
    r_good = await client.post(
        f"/api/v1/bars/{slug}/posts",
        json={"title": "Good", "content": {"analysis": "This is a long enough analysis text"}},
        headers=agent_h,
    )
    assert r_good.status_code == 201


async def test_update_bar_fields(client: AsyncClient, premium_user_headers: dict):
    """Owner can update name, description, icon, rules."""
    slug = f"upd-bar-{secrets.token_hex(4)}"
    await client.post(
        "/api/v1/owner/bars",
        json={"name": "Before", "slug": slug, "content_schema": {}, "visibility": "private"},
        headers=premium_user_headers,
    )

    r = await client.put(
        f"/api/v1/owner/bars/{slug}",
        json={"name": "After", "description": "Updated desc", "icon": "🔥"},
        headers=premium_user_headers,
    )
    assert r.status_code == 200
    assert r.json()["data"]["name"] == "After"
    assert r.json()["data"]["description"] == "Updated desc"


async def test_soft_delete_bar(client: AsyncClient, premium_user_headers: dict):
    """Deleted bar not visible in owner's list."""
    slug = f"del-bar-{secrets.token_hex(4)}"
    await client.post(
        "/api/v1/owner/bars",
        json={"name": "ToDelete", "slug": slug, "content_schema": {}, "visibility": "private"},
        headers=premium_user_headers,
    )

    r_del = await client.delete(f"/api/v1/owner/bars/{slug}", headers=premium_user_headers)
    assert r_del.status_code == 200

    r_list = await client.get("/api/v1/owner/bars", headers=premium_user_headers)
    slugs = [b["slug"] for b in r_list.json()["data"]]
    assert slug not in slugs

    # Also not visible in public bars list
    r_public = await client.get("/api/v1/bars")
    public_slugs = [b["slug"] for b in r_public.json()["data"]]
    assert slug not in public_slugs


async def test_ownership_check(
    client: AsyncClient, premium_user_headers: dict, premium_user: dict, db_session,
):
    """User A cannot update User B's bar."""
    slug = f"own-check-{secrets.token_hex(4)}"
    await client.post(
        "/api/v1/owner/bars",
        json={"name": "Owner A Bar", "slug": slug, "content_schema": {}, "visibility": "private"},
        headers=premium_user_headers,
    )

    # Create another premium user
    import bcrypt
    from nanoid import generate
    from app.models.user import User
    from app.middleware.auth import create_access_token

    user_b = User(
        id=generate(size=21),
        email=f"b_{secrets.token_hex(4)}@test.local",
        password_hash=bcrypt.hashpw(b"pass", bcrypt.gensalt()).decode(),
        name="User B",
        role="premium",
        status="active",
    )
    db_session.add(user_b)
    await db_session.commit()
    b_headers = {"Authorization": f"Bearer {create_access_token(user_b.id)}"}

    r = await client.put(
        f"/api/v1/owner/bars/{slug}",
        json={"name": "Hijacked"},
        headers=b_headers,
    )
    assert r.status_code == 404  # Not found for non-owner


async def test_owner_config_update(client: AsyncClient, premium_user_headers: dict, admin_headers: dict):
    """Owner can update their bar's whitelisted configs (coin_enabled, review_enabled)."""
    slug = f"cfgown-{secrets.token_hex(4)}"
    await client.post(
        "/api/v1/owner/bars",
        json={"name": "ConfigOwn", "slug": slug, "content_schema": {}, "join_mode": "open", "visibility": "private"},
        headers=premium_user_headers,
    )

    # Owner can update whitelisted configs
    r = await client.put(
        f"/api/v1/owner/bars/{slug}/configs/coin_enabled",
        json={"value": True},
        headers=premium_user_headers,
    )
    assert r.status_code == 200

    r_cfg = await client.get(f"/api/v1/admin/configs/bars/{slug}", headers=admin_headers)
    assert r_cfg.json()["data"]["coin_enabled"] is True

    # Owner cannot update non-whitelisted configs
    r_blocked = await client.put(
        f"/api/v1/owner/bars/{slug}/configs/post_cost",
        json={"value": 42},
        headers=premium_user_headers,
    )
    assert r_blocked.status_code == 403
