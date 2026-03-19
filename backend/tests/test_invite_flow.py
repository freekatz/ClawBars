"""C4: Invite system full flow tests."""
import secrets
from datetime import datetime, timezone, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


async def _create_invite_only_bar(
    client: AsyncClient, premium_user_headers: dict, premium_user: dict,
) -> dict:
    slug = f"inv-bar-{secrets.token_hex(4)}"
    r = await client.post(
        "/api/v1/owner/bars",
        json={"name": "Invite Bar", "slug": slug, "content_schema": {}, "join_mode": "invite_only", "visibility": "private"},
        headers=premium_user_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def test_create_invite_and_join(
    client: AsyncClient, premium_user_headers: dict, premium_user: dict,
):
    """Owner creates invite → user joins with token via /join/user."""
    bar = await _create_invite_only_bar(client, premium_user_headers, premium_user)
    slug = bar["slug"]

    r_inv = await client.post(
        f"/api/v1/owner/bars/{slug}/invites",
        json={"label": "Test invite"},
        headers=premium_user_headers,
    )
    assert r_inv.status_code == 201
    token = r_inv.json()["data"]["token"]
    assert token.startswith("clawbars_inv_")

    # Register a user and login
    email = f"invitee_{secrets.token_hex(4)}@test.local"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123", "name": "Invitee"})
    r_login = await client.post("/api/v1/auth/login", json={"email": email, "password": "testpass123"})
    user_h = {"Authorization": f"Bearer {r_login.json()['data']['access_token']}"}

    r_join = await client.post(f"/api/v1/bars/{slug}/join/user", json={"invite_token": token}, headers=user_h)
    assert r_join.status_code == 200


async def test_join_invite_only_without_token(
    client: AsyncClient, premium_user_headers: dict, premium_user: dict,
):
    """Joining invite_only bar without token → 403."""
    bar = await _create_invite_only_bar(client, premium_user_headers, premium_user)

    r_agent = await client.post("/api/v1/agents/register", json={"name": "NoTokenAgent"})
    agent_h = {"Authorization": f"Bearer {r_agent.json()['data']['api_key']}"}

    r = await client.post(f"/api/v1/bars/{bar['slug']}/join", json={}, headers=agent_h)
    assert r.status_code == 403


async def test_max_uses_exhausted(
    client: AsyncClient, premium_user_headers: dict, premium_user: dict,
):
    """Token with max_uses=1 cannot be used twice."""
    bar = await _create_invite_only_bar(client, premium_user_headers, premium_user)
    slug = bar["slug"]

    r_inv = await client.post(
        f"/api/v1/owner/bars/{slug}/invites",
        json={"label": "One-time", "max_uses": 1},
        headers=premium_user_headers,
    )
    token = r_inv.json()["data"]["token"]

    # First user joins OK
    email1 = f"user1_{secrets.token_hex(4)}@test.local"
    await client.post("/api/v1/auth/register", json={"email": email1, "password": "testpass123", "name": "User1"})
    r_login1 = await client.post("/api/v1/auth/login", json={"email": email1, "password": "testpass123"})
    h1 = {"Authorization": f"Bearer {r_login1.json()['data']['access_token']}"}
    r1 = await client.post(f"/api/v1/bars/{slug}/join/user", json={"invite_token": token}, headers=h1)
    assert r1.status_code == 200

    # Second user fails
    email2 = f"user2_{secrets.token_hex(4)}@test.local"
    await client.post("/api/v1/auth/register", json={"email": email2, "password": "testpass123", "name": "User2"})
    r_login2 = await client.post("/api/v1/auth/login", json={"email": email2, "password": "testpass123"})
    h2 = {"Authorization": f"Bearer {r_login2.json()['data']['access_token']}"}
    r2 = await client.post(f"/api/v1/bars/{slug}/join/user", json={"invite_token": token}, headers=h2)
    assert r2.status_code == 400


async def test_expired_token_rejected(
    client: AsyncClient, premium_user_headers: dict, premium_user: dict, db_session: AsyncSession,
):
    """Expired invite token → rejected."""
    bar = await _create_invite_only_bar(client, premium_user_headers, premium_user)
    slug = bar["slug"]

    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    r_inv = await client.post(
        f"/api/v1/owner/bars/{slug}/invites",
        json={"label": "Expired", "expires_at": past},
        headers=premium_user_headers,
    )
    assert r_inv.status_code == 201
    token = r_inv.json()["data"]["token"]

    email = f"late_{secrets.token_hex(4)}@test.local"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123", "name": "LateUser"})
    r_login = await client.post("/api/v1/auth/login", json={"email": email, "password": "testpass123"})
    user_h = {"Authorization": f"Bearer {r_login.json()['data']['access_token']}"}
    r = await client.post(f"/api/v1/bars/{slug}/join/user", json={"invite_token": token}, headers=user_h)
    assert r.status_code == 400


async def test_target_user_restriction(
    client: AsyncClient, premium_user_headers: dict, premium_user: dict,
):
    """Invite for specific user → other user cannot use it (via user join endpoint)."""
    # Create a private bar (not via the helper since we need category=premium)
    import secrets as _secrets
    slug = f"priv-bar-{_secrets.token_hex(4)}"
    r_bar = await client.post(
        "/api/v1/owner/bars",
        json={"name": "Private Bar", "slug": slug, "category": "vip", "visibility": "private"},
        headers=premium_user_headers,
    )
    assert r_bar.status_code == 201
    target_email = f"target_{_secrets.token_hex(4)}@test.local"
    r_target = await client.post(
        "/api/v1/auth/register",
        json={"email": target_email, "password": "testpass123", "name": "TargetUser"},
    )
    assert r_target.status_code == 201
    target_user = r_target.json()["data"]

    r_inv = await client.post(
        f"/api/v1/owner/bars/{slug}/invites",
        json={"label": "Targeted", "target_user_id": target_user["id"]},
        headers=premium_user_headers,
    )
    token = r_inv.json()["data"]["token"]

    # Wrong user tries to use the invite
    wrong_email = f"wrong_{_secrets.token_hex(4)}@test.local"
    r_wrong_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": wrong_email, "password": "testpass123", "name": "WrongUser"},
    )
    r_wrong_login = await client.post(
        "/api/v1/auth/login",
        json={"email": wrong_email, "password": "testpass123"},
    )
    wrong_token = r_wrong_login.json()["data"]["access_token"]
    wrong_h = {"Authorization": f"Bearer {wrong_token}"}

    r = await client.post(
        f"/api/v1/bars/{slug}/join/user",
        json={"invite_token": token},
        headers=wrong_h,
    )
    assert r.status_code == 403

    # Correct user succeeds
    r_target_login = await client.post(
        "/api/v1/auth/login",
        json={"email": target_email, "password": "testpass123"},
    )
    target_token = r_target_login.json()["data"]["access_token"]
    target_h = {"Authorization": f"Bearer {target_token}"}

    r_ok = await client.post(
        f"/api/v1/bars/{slug}/join/user",
        json={"invite_token": token},
        headers=target_h,
    )
    assert r_ok.status_code == 200


async def test_revoked_invite_cannot_be_used(
    client: AsyncClient, premium_user_headers: dict, premium_user: dict,
):
    """Revoked (deleted) invite cannot be used."""
    bar = await _create_invite_only_bar(client, premium_user_headers, premium_user)
    slug = bar["slug"]

    r_inv = await client.post(
        f"/api/v1/owner/bars/{slug}/invites",
        json={"label": "ToRevoke"},
        headers=premium_user_headers,
    )
    invite = r_inv.json()["data"]

    # Revoke
    r_revoke = await client.delete(
        f"/api/v1/owner/bars/{slug}/invites/{invite['id']}",
        headers=premium_user_headers,
    )
    assert r_revoke.status_code == 200

    # Try to use with user-level join
    email = f"post_revoke_{secrets.token_hex(4)}@test.local"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123", "name": "PostRevokeUser"})
    r_login = await client.post("/api/v1/auth/login", json={"email": email, "password": "testpass123"})
    user_h = {"Authorization": f"Bearer {r_login.json()['data']['access_token']}"}
    r = await client.post(f"/api/v1/bars/{slug}/join/user", json={"invite_token": invite["token"]}, headers=user_h)
    assert r.status_code == 404


async def test_token_uniqueness(
    client: AsyncClient, premium_user_headers: dict, premium_user: dict,
):
    """Each invite has a unique token."""
    bar = await _create_invite_only_bar(client, premium_user_headers, premium_user)
    slug = bar["slug"]

    tokens = set()
    for i in range(5):
        r = await client.post(
            f"/api/v1/owner/bars/{slug}/invites",
            json={"label": f"Invite-{i}"},
            headers=premium_user_headers,
        )
        assert r.status_code == 201
        tokens.add(r.json()["data"]["token"])

    assert len(tokens) == 5


async def test_user_join_auto_adds_existing_agents(
    client: AsyncClient, premium_user_headers: dict, premium_user: dict,
):
    """User joins private bar via invite → existing agents are auto-added."""
    import secrets as _secrets
    slug = f"priv-bar-{_secrets.token_hex(4)}"
    r_bar = await client.post(
        "/api/v1/owner/bars",
        json={"name": "Private Bar Agent Test", "slug": slug, "category": "vip", "visibility": "private"},
        headers=premium_user_headers,
    )
    assert r_bar.status_code == 201

    r_inv = await client.post(
        f"/api/v1/owner/bars/{slug}/invites",
        json={"label": "For User"},
        headers=premium_user_headers,
    )
    token = r_inv.json()["data"]["token"]

    # Target user registers
    target_email = f"target_{_secrets.token_hex(4)}@test.local"
    r_target = await client.post(
        "/api/v1/auth/register",
        json={"email": target_email, "password": "testpass123", "name": "TargetUser2"},
    )
    
    r_login = await client.post(
        "/api/v1/auth/login",
        json={"email": target_email, "password": "testpass123"},
    )
    target_token = r_login.json()["data"]["access_token"]
    target_h = {"Authorization": f"Bearer {target_token}"}

    # Target user creates an agent BEFORE joining
    r_agent1 = await client.post("/api/v1/agents/register", json={"name": "PreJoinAgent"}, headers=target_h)
    assert r_agent1.status_code == 201
    agent1_id = r_agent1.json()["data"]["agent_id"]

    # Target user joins the bar
    r_join = await client.post(f"/api/v1/bars/{slug}/join/user", json={"invite_token": token}, headers=target_h)
    assert r_join.status_code == 200

    # Verify agent1 is now a member
    r_members = await client.get(f"/api/v1/bars/{slug}/members")
    assert r_members.status_code == 200
    member_ids = [m["agent_id"] for m in r_members.json()["data"]]
    assert agent1_id in member_ids

    # Target user creates another agent AFTER joining
    r_agent2 = await client.post("/api/v1/agents/register", json={"name": "PostJoinAgent"}, headers=target_h)
    assert r_agent2.status_code == 201
    agent2_id = r_agent2.json()["data"]["agent_id"]

    # Verify agent2 is also a member automatically
    r_members2 = await client.get(f"/api/v1/bars/{slug}/members")
    member_ids2 = [m["agent_id"] for m in r_members2.json()["data"]]
    assert agent2_id in member_ids2
