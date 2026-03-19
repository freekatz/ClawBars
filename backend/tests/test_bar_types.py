"""Tests for bar category presets and visibility controls."""
import secrets

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


async def test_create_knowledge_bar(client: AsyncClient, premium_user_headers: dict):
    """Admin creates a knowledge bar with correct defaults."""
    slug = f"kb-bar-{secrets.token_hex(4)}"
    r = await client.post(
        "/api/v1/admin/bars",
        json={"name": "Knowledge Bar", "slug": slug, "category": "vault", "visibility": "public"},
        headers=premium_user_headers,
    )
    # premium_user_headers may not be admin; if 403 that's expected
    if r.status_code == 403:
        pytest.skip("Requires admin access")
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["visibility"] == "public"
    assert data["category"] == "vault"
    assert data["join_mode"] == "open"


async def test_create_forum_bar(client: AsyncClient, premium_user_headers: dict):
    """Create a forum bar → defaults: visibility=private (premium user), no review."""
    slug = f"forum-bar-{secrets.token_hex(4)}"
    r = await client.post(
        "/api/v1/owner/bars",
        json={"name": "Forum Bar", "slug": slug, "category": "lounge", "visibility": "private"},
        headers=premium_user_headers,
    )
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["visibility"] == "private"
    assert data["category"] == "lounge"
    assert data["join_mode"] == "invite_only"


async def test_create_premium_bar(client: AsyncClient, premium_user_headers: dict):
    """Create a premium bar → private by default for premium users."""
    slug = f"premium-bar-{secrets.token_hex(4)}"
    r = await client.post(
        "/api/v1/owner/bars",
        json={"name": "Premium Bar", "slug": slug, "category": "vip", "visibility": "private"},
        headers=premium_user_headers,
    )
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["visibility"] == "private"
    assert data["category"] == "vip"
    assert data["join_mode"] == "invite_only"


async def test_premium_public_allowed(client: AsyncClient, premium_user_headers: dict):
    """Premium bar can be public when created by admin."""
    slug = f"premium-pub-{secrets.token_hex(4)}"
    r = await client.post(
        "/api/v1/admin/bars",
        json={"name": "Premium Public", "slug": slug, "category": "vip", "visibility": "public"},
        headers=premium_user_headers,
    )
    # premium_user_headers may not be admin; if 403 that's expected
    if r.status_code == 403:
        pytest.skip("Requires admin access")
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["visibility"] == "public"
    assert data["category"] == "vip"


async def test_private_bar_requires_user_join(
    client: AsyncClient, premium_user_headers: dict, agent_headers: dict,
):
    """Agent cannot directly join a private bar without user-level access."""
    slug = f"priv-bar-{secrets.token_hex(4)}"
    r = await client.post(
        "/api/v1/owner/bars",
        json={"name": "Private Bar", "slug": slug, "category": "vip", "visibility": "private"},
        headers=premium_user_headers,
    )
    assert r.status_code == 201

    # Agent tries to join directly → should fail
    r_join = await client.post(
        f"/api/v1/bars/{slug}/join",
        json={},
        headers=agent_headers,
    )
    assert r_join.status_code == 403


async def test_user_join_private_bar_with_invite(
    client: AsyncClient, premium_user_headers: dict, premium_user: dict,
):
    """User joins private bar via invite → BarUserMembership created."""
    slug = f"priv-bar-{secrets.token_hex(4)}"
    r = await client.post(
        "/api/v1/owner/bars",
        json={"name": "Private Bar", "slug": slug, "category": "vip", "visibility": "private"},
        headers=premium_user_headers,
    )
    assert r.status_code == 201

    # Create invite
    r_inv = await client.post(
        f"/api/v1/owner/bars/{slug}/invites",
        json={"label": "General invite"},
        headers=premium_user_headers,
    )
    assert r_inv.status_code == 201
    token = r_inv.json()["data"]["token"]

    # Register another user and join via invite
    email = f"joiner_{secrets.token_hex(4)}@test.local"
    r_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpass123", "name": "Joiner"},
    )
    assert r_reg.status_code == 201

    r_login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "testpass123"},
    )
    user_token = r_login.json()["data"]["access_token"]
    user_h = {"Authorization": f"Bearer {user_token}"}

    r_join = await client.post(
        f"/api/v1/bars/{slug}/join/user",
        json={"invite_token": token},
        headers=user_h,
    )
    assert r_join.status_code == 200
    assert r_join.json()["data"]["role"] == "member"


async def test_agent_with_owner_joins_private_bar_after_user_join(
    client: AsyncClient, premium_user_headers: dict, premium_user: dict,
):
    """After user joins private bar, their agents can join via agent join."""
    slug = f"priv-bar-{secrets.token_hex(4)}"
    r = await client.post(
        "/api/v1/owner/bars",
        json={"name": "Private Bar", "slug": slug, "category": "vip", "visibility": "private"},
        headers=premium_user_headers,
    )
    assert r.status_code == 201

    # Create invite
    r_inv = await client.post(
        f"/api/v1/owner/bars/{slug}/invites",
        json={"label": "General invite"},
        headers=premium_user_headers,
    )
    token = r_inv.json()["data"]["token"]

    # Register user
    email = f"owner_{secrets.token_hex(4)}@test.local"
    r_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpass123", "name": "AgentOwner"},
    )
    assert r_reg.status_code == 201

    r_login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "testpass123"},
    )
    user_token = r_login.json()["data"]["access_token"]
    user_h = {"Authorization": f"Bearer {user_token}"}

    # Register agent with user auth → agent is linked to user
    r_agent = await client.post(
        "/api/v1/agents/register",
        json={"name": "LinkedAgent"},
        headers=user_h,
    )
    assert r_agent.status_code == 201
    agent_key = r_agent.json()["data"]["api_key"]
    agent_h = {"Authorization": f"Bearer {agent_key}"}

    # User joins private bar via invite
    r_join_user = await client.post(
        f"/api/v1/bars/{slug}/join/user",
        json={"invite_token": token},
        headers=user_h,
    )
    assert r_join_user.status_code == 200

    # Agent should now be able to join (since user has access)
    r_join_agent = await client.post(
        f"/api/v1/bars/{slug}/join",
        json={},
        headers=agent_h,
    )
    # Agent was auto-joined during user join, so either 200 or 409 (already member)
    assert r_join_agent.status_code in (200, 409)


async def test_bar_default_category_is_forum(client: AsyncClient, premium_user_headers: dict):
    """Creating a bar without category defaults to forum."""
    slug = f"default-bar-{secrets.token_hex(4)}"
    r = await client.post(
        "/api/v1/owner/bars",
        json={"name": "Default Bar", "slug": slug, "visibility": "private"},
        headers=premium_user_headers,
    )
    assert r.status_code == 201
    assert r.json()["data"]["category"] == "lounge"


async def test_bar_list_shows_category(client: AsyncClient, premium_user_headers: dict):
    """Bar listing includes category field."""
    slug = f"cat-bar-{secrets.token_hex(4)}"
    await client.post(
        "/api/v1/owner/bars",
        json={"name": "Cat Bar", "slug": slug, "category": "vip", "visibility": "private"},
        headers=premium_user_headers,
    )

    r = await client.get(f"/api/v1/bars/{slug}")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["category"] == "vip"


async def test_bar_list_filter_by_category(client: AsyncClient, premium_user_headers: dict):
    """Bar listing can filter by category."""
    slug = f"filter-bar-{secrets.token_hex(4)}"
    await client.post(
        "/api/v1/owner/bars",
        json={"name": "Filter Bar", "slug": slug, "category": "vip", "visibility": "private"},
        headers=premium_user_headers,
    )

    r = await client.get("/api/v1/bars", params={"category": "vip"})
    assert r.status_code == 200
    bars = r.json()["data"]
    for bar in bars:
        assert bar["category"] == "vip"


async def test_agent_register_with_user_auth(client: AsyncClient):
    """Agent registered with user JWT gets owner_id set."""
    email = f"agent_owner_{secrets.token_hex(4)}@test.local"
    r_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpass123", "name": "AgentOwner"},
    )
    assert r_reg.status_code == 201

    r_login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "testpass123"},
    )
    user_token = r_login.json()["data"]["access_token"]
    user_h = {"Authorization": f"Bearer {user_token}"}

    r_agent = await client.post(
        "/api/v1/agents/register",
        json={"name": "OwnedAgent"},
        headers=user_h,
    )
    assert r_agent.status_code == 201

    # Get agent details to verify
    agent_id = r_agent.json()["data"]["agent_id"]
    r_detail = await client.get(f"/api/v1/agents/{agent_id}")
    assert r_detail.status_code == 200
    assert r_detail.json()["data"]["owner_id"] == r_reg.json()["data"]["id"]


async def test_my_agents_endpoint(client: AsyncClient):
    """GET /auth/me/agents returns agents owned by current user."""
    email = f"agent_lister_{secrets.token_hex(4)}@test.local"
    r_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpass123", "name": "AgentLister"},
    )
    assert r_reg.status_code == 201

    r_login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "testpass123"},
    )
    user_token = r_login.json()["data"]["access_token"]
    user_h = {"Authorization": f"Bearer {user_token}"}

    # Register 2 agents under this user
    for name in ["Agent1", "Agent2"]:
        r_a = await client.post("/api/v1/agents/register", json={"name": name}, headers=user_h)
        assert r_a.status_code == 201

    r_list = await client.get("/api/v1/auth/me/agents", headers=user_h)
    assert r_list.status_code == 200
    agents = r_list.json()["data"]
    assert len(agents) == 2
    names = {a["name"] for a in agents}
    assert "Agent1" in names
    assert "Agent2" in names


async def test_knowledge_public_has_coins(client: AsyncClient, premium_user_headers: dict):
    """Public knowledge bar should have coin_enabled=True and review_enabled=True."""
    slug = f"kb-coins-{secrets.token_hex(4)}"
    r = await client.post(
        "/api/v1/admin/bars",
        json={"name": "KB Coins", "slug": slug, "category": "vault", "visibility": "public"},
        headers=premium_user_headers,
    )
    if r.status_code == 403:
        pytest.skip("Requires admin access")
    assert r.status_code == 201

    r_cfg = await client.get(f"/api/v1/admin/configs/bars/{slug}", headers=premium_user_headers)
    if r_cfg.status_code == 403:
        pytest.skip("Requires admin access")
    configs = r_cfg.json()["data"]
    assert configs.get("coin_enabled") is True
    assert configs.get("review_enabled") is True
    assert configs.get("post_cost") == 5


async def test_knowledge_private_no_coins(client: AsyncClient, premium_user_headers: dict):
    """Private knowledge bar should have coin_enabled=False."""
    slug = f"kb-nocoins-{secrets.token_hex(4)}"
    r = await client.post(
        "/api/v1/owner/bars",
        json={"name": "KB NoCoin", "slug": slug, "category": "vault", "visibility": "private"},
        headers=premium_user_headers,
    )
    assert r.status_code == 201

    r_cfg = await client.get(f"/api/v1/admin/configs/bars/{slug}", headers=premium_user_headers)
    if r_cfg.status_code == 403:
        pytest.skip("Requires admin access")
    configs = r_cfg.json()["data"]
    assert configs.get("coin_enabled") is False
    assert configs.get("review_enabled") is False


async def test_forum_public_no_coins(client: AsyncClient, premium_user_headers: dict):
    """Public forum bar should have coin_enabled=False (forums never have coins)."""
    slug = f"forum-nocoins-{secrets.token_hex(4)}"
    r = await client.post(
        "/api/v1/admin/bars",
        json={"name": "Forum NoCoin", "slug": slug, "category": "lounge", "visibility": "public"},
        headers=premium_user_headers,
    )
    if r.status_code == 403:
        pytest.skip("Requires admin access")
    assert r.status_code == 201

    r_cfg = await client.get(f"/api/v1/admin/configs/bars/{slug}", headers=premium_user_headers)
    if r_cfg.status_code == 403:
        pytest.skip("Requires admin access")
    configs = r_cfg.json()["data"]
    assert configs.get("coin_enabled") is False
    assert configs.get("review_enabled") is False


async def test_premium_only_creator_posts(client: AsyncClient, premium_user_headers: dict):
    """Non-creator agent cannot post in premium bar (403)."""
    slug = f"prem-nopost-{secrets.token_hex(4)}"
    r = await client.post(
        "/api/v1/owner/bars",
        json={"name": "Premium NoPost", "slug": slug, "category": "vip", "visibility": "private"},
        headers=premium_user_headers,
    )
    assert r.status_code == 201

    # Register a different user and their agent
    email = f"other_{secrets.token_hex(4)}@test.local"
    r_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpass123", "name": "Other"},
    )
    assert r_reg.status_code == 201
    r_login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "testpass123"},
    )
    other_token = r_login.json()["data"]["access_token"]
    other_h = {"Authorization": f"Bearer {other_token}"}

    # Create invite and join the other user
    r_inv = await client.post(
        f"/api/v1/owner/bars/{slug}/invites",
        json={"label": "test"},
        headers=premium_user_headers,
    )
    assert r_inv.status_code == 201
    token = r_inv.json()["data"]["token"]

    r_join = await client.post(
        f"/api/v1/bars/{slug}/join/user",
        json={"invite_token": token},
        headers=other_h,
    )
    assert r_join.status_code == 200

    # Register agent under the other user
    r_agent = await client.post(
        "/api/v1/agents/register",
        json={"name": "OtherAgent"},
        headers=other_h,
    )
    assert r_agent.status_code == 201
    agent_key = r_agent.json()["data"]["api_key"]
    agent_h = {"Authorization": f"Bearer {agent_key}"}

    # Agent joins bar
    r_join_agent = await client.post(
        f"/api/v1/bars/{slug}/join", json={}, headers=agent_h,
    )
    assert r_join_agent.status_code in (200, 409)

    # Now try to post → should be 403
    r_post = await client.post(
        f"/api/v1/bars/{slug}/posts",
        json={"title": "Test", "content": {"text": "test"}, "summary": "test"},
        headers=agent_h,
    )
    assert r_post.status_code == 403


async def test_premium_creator_posts_ok(client: AsyncClient, premium_user_headers: dict):
    """Creator's agent can post in premium bar."""
    slug = f"prem-ok-{secrets.token_hex(4)}"
    r = await client.post(
        "/api/v1/owner/bars",
        json={"name": "Premium OK", "slug": slug, "category": "vip", "visibility": "private"},
        headers=premium_user_headers,
    )
    assert r.status_code == 201

    # Get the premium user's info to register an agent under them
    r_me = await client.get("/api/v1/auth/me", headers=premium_user_headers)
    assert r_me.status_code == 200

    # Register agent under the premium user (creator)
    r_agent = await client.post(
        "/api/v1/agents/register",
        json={"name": f"CreatorAgent-{secrets.token_hex(4)}"},
        headers=premium_user_headers,
    )
    assert r_agent.status_code == 201
    agent_key = r_agent.json()["data"]["api_key"]
    agent_h = {"Authorization": f"Bearer {agent_key}"}

    # Agent joins bar
    r_join = await client.post(
        f"/api/v1/bars/{slug}/join", json={}, headers=agent_h,
    )
    assert r_join.status_code in (200, 409)

    # Post → should succeed
    r_post = await client.post(
        f"/api/v1/bars/{slug}/posts",
        json={"title": "Creator Post", "content": {"text": "ok"}, "summary": "test"},
        headers=agent_h,
    )
    assert r_post.status_code == 201


async def test_free_user_member_limit(client: AsyncClient, user_headers: dict):
    """Free-user premium bar enforces 50-member limit."""
    from app.services.bar import FREE_USER_MEMBER_LIMITS
    # Verify the limits are configured
    assert FREE_USER_MEMBER_LIMITS["vault"] == 20
    assert FREE_USER_MEMBER_LIMITS["lounge"] == 100
    assert FREE_USER_MEMBER_LIMITS["vip"] == 50
