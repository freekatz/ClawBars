"""Tests for bar ownership and management."""
import secrets

import pytest
from httpx import AsyncClient


async def test_free_user_can_create_private_bar(client: AsyncClient, user_headers: dict):
    """Free users can create private bars."""
    slug = f"free-bar-{secrets.token_hex(4)}"
    r = await client.post(
        "/api/v1/owner/bars",
        json={"name": "Free Bar", "slug": slug, "category": "lounge", "visibility": "private"},
        headers=user_headers,
    )
    assert r.status_code == 201
    assert r.json()["data"]["visibility"] == "private"


async def test_free_user_cannot_create_public_knowledge(client: AsyncClient, user_headers: dict):
    """Free users cannot create public knowledge bars (admin only)."""
    r = await client.post(
        "/api/v1/owner/bars",
        json={"name": "KB", "slug": f"kb-{secrets.token_hex(4)}", "category": "vault", "visibility": "public"},
        headers=user_headers,
    )
    assert r.status_code == 403


async def test_free_user_cannot_create_public_forum(client: AsyncClient, user_headers: dict):
    """Free users cannot create public forum bars (admin only)."""
    r = await client.post(
        "/api/v1/owner/bars",
        json={"name": "Forum", "slug": f"forum-{secrets.token_hex(4)}", "category": "lounge", "visibility": "public"},
        headers=user_headers,
    )
    assert r.status_code == 403


async def test_create_bar_as_premium(client: AsyncClient, premium_user_headers: dict):
    slug = f"premium-bar-{secrets.token_hex(4)}"
    r = await client.post(
        "/api/v1/owner/bars",
        json={
            "name": "My Premium Bar",
            "slug": slug,
            "description": "A test bar",
            "icon": "🍻",
            "join_mode": "open",
            "visibility": "private",
        },
        headers=premium_user_headers,
    )
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["slug"] == slug
    assert data["owner_type"] == "user"
    assert data["join_mode"] == "invite_only"  # private bars always force invite_only


async def test_create_bar_duplicate_slug(client: AsyncClient, premium_user_headers: dict):
    slug = f"dup-bar-{secrets.token_hex(4)}"
    await client.post(
        "/api/v1/owner/bars",
        json={"name": "Bar One", "slug": slug, "visibility": "private"},
        headers=premium_user_headers,
    )
    r = await client.post(
        "/api/v1/owner/bars",
        json={"name": "Bar Two", "slug": slug, "visibility": "private"},
        headers=premium_user_headers,
    )
    assert r.status_code == 409


async def test_list_my_bars(client: AsyncClient, premium_user_headers: dict):
    slug = f"mylist-bar-{secrets.token_hex(4)}"
    await client.post(
        "/api/v1/owner/bars",
        json={"name": "Listed Bar", "slug": slug, "visibility": "private"},
        headers=premium_user_headers,
    )
    r = await client.get("/api/v1/owner/bars", headers=premium_user_headers)
    assert r.status_code == 200
    bars = r.json()["data"]
    slugs = [b["slug"] for b in bars]
    assert slug in slugs


async def test_update_bar(client: AsyncClient, premium_user_headers: dict):
    slug = f"upd-bar-{secrets.token_hex(4)}"
    await client.post(
        "/api/v1/owner/bars",
        json={"name": "Original Name", "slug": slug, "visibility": "private"},
        headers=premium_user_headers,
    )
    r = await client.put(
        f"/api/v1/owner/bars/{slug}",
        json={"name": "Updated Name", "description": "New desc"},
        headers=premium_user_headers,
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["name"] == "Updated Name"
    assert data["description"] == "New desc"


async def test_update_bar_not_owned(client: AsyncClient, premium_user_headers: dict, admin_headers: dict):
    slug = f"admin-bar-{secrets.token_hex(4)}"
    await client.post(
        "/api/v1/admin/bars",
        json={"name": "Admin Bar", "slug": slug},
        headers=admin_headers,
    )
    r = await client.put(
        f"/api/v1/owner/bars/{slug}",
        json={"name": "Hijacked"},
        headers=premium_user_headers,
    )
    assert r.status_code == 404


async def test_add_and_remove_member(
    client: AsyncClient, premium_user_headers: dict, registered_agent: dict
):
    slug = f"member-bar-{secrets.token_hex(4)}"
    await client.post(
        "/api/v1/owner/bars",
        json={"name": "Member Bar", "slug": slug, "visibility": "private"},
        headers=premium_user_headers,
    )
    agent_id = registered_agent["agent_id"]

    # Add member
    r = await client.post(
        f"/api/v1/owner/bars/{slug}/members",
        json={"agent_id": agent_id},
        headers=premium_user_headers,
    )
    assert r.status_code == 200
    assert r.json()["data"]["action"] == "added"

    # Verify member is listed
    members_r = await client.get(f"/api/v1/bars/{slug}/members")
    ids = [m["agent_id"] for m in members_r.json()["data"]]
    assert agent_id in ids

    # Remove member
    r2 = await client.delete(
        f"/api/v1/owner/bars/{slug}/members/{agent_id}",
        headers=premium_user_headers,
    )
    assert r2.status_code == 200
    assert r2.json()["data"]["action"] == "removed"


async def test_invite_only_bar_join_with_token(
    client: AsyncClient, premium_user_headers: dict,
):
    """Private bar invite flow: user joins via /join/user, agents auto-added."""
    slug = f"invite-only-{secrets.token_hex(4)}"
    await client.post(
        "/api/v1/owner/bars",
        json={"name": "Invite Bar", "slug": slug, "join_mode": "invite_only", "visibility": "private"},
        headers=premium_user_headers,
    )

    # Create invite
    inv_r = await client.post(
        f"/api/v1/owner/bars/{slug}/invites",
        json={"label": "Test invite", "max_uses": 5},
        headers=premium_user_headers,
    )
    assert inv_r.status_code == 201
    token = inv_r.json()["data"]["token"]

    # Register a new user and login
    email = f"invitee_{secrets.token_hex(4)}@test.local"
    r_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpass123", "name": "Invitee"},
    )
    assert r_reg.status_code == 201

    r_login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "testpass123"},
    )
    user_h = {"Authorization": f"Bearer {r_login.json()['data']['access_token']}"}

    # User joins via /join/user with invite token
    join_r = await client.post(
        f"/api/v1/bars/{slug}/join/user",
        json={"invite_token": token},
        headers=user_h,
    )
    assert join_r.status_code == 200
    assert join_r.json()["data"]["role"] == "member"

    # Verify used_count incremented
    invites_r = await client.get(
        f"/api/v1/owner/bars/{slug}/invites",
        headers=premium_user_headers,
    )
    invites = invites_r.json()["data"]
    found = next(i for i in invites if i["token"] == token)
    assert found["used_count"] == 1


async def test_revoke_invite(client: AsyncClient, premium_user_headers: dict):
    slug = f"rev-inv-{secrets.token_hex(4)}"
    await client.post(
        "/api/v1/owner/bars",
        json={"name": "Revoke Bar", "slug": slug, "join_mode": "invite_only", "visibility": "private"},
        headers=premium_user_headers,
    )

    inv_r = await client.post(
        f"/api/v1/owner/bars/{slug}/invites",
        json={"label": "Revokable"},
        headers=premium_user_headers,
    )
    invite_id = inv_r.json()["data"]["id"]

    del_r = await client.delete(
        f"/api/v1/owner/bars/{slug}/invites/{invite_id}",
        headers=premium_user_headers,
    )
    assert del_r.status_code == 200
    assert del_r.json()["data"]["revoked"] is True


async def test_delete_bar(client: AsyncClient, premium_user_headers: dict):
    slug = f"del-bar-{secrets.token_hex(4)}"
    await client.post(
        "/api/v1/owner/bars",
        json={"name": "To Delete", "slug": slug, "visibility": "private"},
        headers=premium_user_headers,
    )

    del_r = await client.delete(
        f"/api/v1/owner/bars/{slug}",
        headers=premium_user_headers,
    )
    assert del_r.status_code == 200

    # Bar should no longer appear in list
    list_r = await client.get("/api/v1/owner/bars", headers=premium_user_headers)
    slugs = [b["slug"] for b in list_r.json()["data"]]
    assert slug not in slugs
