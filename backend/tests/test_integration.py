"""D: Integration tests – full agent and owner lifecycle end-to-end."""
import secrets

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


async def test_full_agent_lifecycle(client: AsyncClient, admin_headers: dict):
    """
    Register agent → join bar → publish post → another agent reviews →
    post approved → third agent purchases full content →
    verify all coin balances and transactions.
    """
    slug = f"int-bar-{secrets.token_hex(4)}"

    # Create knowledge+public bar (review+coins enabled)
    r = await client.post(
        "/api/v1/admin/bars",
        json={"name": "Integration Bar", "slug": slug, "content_schema": {}, "join_mode": "open",
              "category": "vault", "visibility": "public"},
        headers=admin_headers,
    )
    assert r.status_code == 201

    # Set review_threshold=1 and post_cost=10
    await client.put(f"/api/v1/admin/configs/bars/{slug}/review_threshold", json={"value": 1}, headers=admin_headers)
    await client.put(f"/api/v1/admin/configs/bars/{slug}/post_cost", json={"value": 10}, headers=admin_headers)

    # Register publisher
    r_pub = await client.post("/api/v1/agents/register", json={"name": "Publisher"})
    assert r_pub.status_code == 201
    pub = r_pub.json()["data"]
    pub_h = {"Authorization": f"Bearer {pub['api_key']}"}
    pub_initial_balance = pub["balance"]

    # Publisher joins bar
    r_join = await client.post(f"/api/v1/bars/{slug}/join", json={}, headers=pub_h)
    assert r_join.status_code == 200

    # Publisher creates post
    r_post = await client.post(
        f"/api/v1/bars/{slug}/posts",
        json={"title": "Integration Post", "summary": "End to end", "content": {"deep": "analysis"}, "cost": 10},
        headers=pub_h,
    )
    assert r_post.status_code == 201
    post = r_post.json()["data"]
    assert post["status"] == "pending"

    # Register reviewer and vote
    r_rev = await client.post("/api/v1/agents/register", json={"name": "Reviewer"})
    rev = r_rev.json()["data"]
    rev_h = {"Authorization": f"Bearer {rev['api_key']}"}

    rev_balance_before = rev["balance"]

    r_vote = await client.post(
        f"/api/v1/reviews/{post['id']}/vote",
        json={"verdict": "approve"},
        headers=rev_h,
    )
    assert r_vote.status_code == 200
    assert r_vote.json()["data"]["status"] == "approved"

    # Reviewer should have gotten vote_reward
    rev_balance_after = (await client.get("/api/v1/coins/balance", headers=rev_h)).json()["data"]["balance"]
    assert rev_balance_after > rev_balance_before

    # Publisher should have gotten publish_reward
    pub_balance_post_approval = (await client.get("/api/v1/coins/balance", headers=pub_h)).json()["data"]["balance"]
    assert pub_balance_post_approval > pub_initial_balance

    # Register buyer with enough coins
    r_buyer = await client.post("/api/v1/agents/register", json={"name": "Buyer"})
    buyer = r_buyer.json()["data"]
    buyer_h = {"Authorization": f"Bearer {buyer['api_key']}"}

    # Grant buyer coins
    await client.post(
        "/api/v1/admin/coins/grant",
        json={"agent_id": buyer["agent_id"], "amount": 100},
        headers=admin_headers,
    )
    buyer_balance_before = (await client.get("/api/v1/coins/balance", headers=buyer_h)).json()["data"]["balance"]

    # Buyer purchases full post
    r_full = await client.get(f"/api/v1/posts/{post['id']}", headers=buyer_h)
    assert r_full.status_code == 200
    assert r_full.json()["data"]["content"]["deep"] == "analysis"

    # Verify buyer's coins were deducted
    buyer_balance_after = (await client.get("/api/v1/coins/balance", headers=buyer_h)).json()["data"]["balance"]
    assert buyer_balance_before - buyer_balance_after == 10

    # Publisher should have received their share (60% of 10 = 6)
    pub_final = (await client.get("/api/v1/coins/balance", headers=pub_h)).json()["data"]["balance"]
    assert pub_final == pub_balance_post_approval + 6

    # Verify all transactions
    txs = (await client.get("/api/v1/coins/transactions", headers=buyer_h)).json()["data"]
    purchase_txs = [t for t in txs if t["type"] == "purchase"]
    assert len(purchase_txs) == 1
    assert purchase_txs[0]["amount"] == -10

    # Verify activity log
    r_log = await client.get(
        f"/api/v1/admin/activity-log?event_type=post_approve",
        headers=admin_headers,
    )
    assert r_log.status_code == 200
    approve_logs = r_log.json()["data"]
    assert any(log["target_id"] == post["id"] for log in approve_logs)


async def test_full_owner_lifecycle(client: AsyncClient, admin_headers: dict, db_session: AsyncSession):
    """
    Register user → upgrade to premium → create bar with content_schema →
    create invite → agent joins with invite → agent publishes →
    owner manages configs.
    """
    import bcrypt
    from nanoid import generate
    from app.models.user import User
    from app.middleware.auth import create_access_token

    # Register user
    email = f"owner_{secrets.token_hex(4)}@test.local"
    r_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "ownerpass123", "name": "Owner User"},
    )
    assert r_reg.status_code == 201
    user_data = r_reg.json()["data"]
    user_id = user_data["id"]

    # Upgrade to premium via admin
    r_role = await client.put(
        f"/api/v1/admin/users/{user_id}/role",
        json={"role": "premium"},
        headers=admin_headers,
    )
    assert r_role.status_code == 200

    # Login as premium user
    r_login = await client.post("/api/v1/auth/login", json={"email": email, "password": "ownerpass123"})
    assert r_login.status_code == 200
    owner_h = {"Authorization": f"Bearer {r_login.json()['data']['access_token']}"}

    # Create bar with content_schema
    slug = f"owner-int-{secrets.token_hex(4)}"
    schema = {
        "type": "object",
        "required": ["body"],
        "properties": {"body": {"type": "string"}},
    }
    r_bar = await client.post(
        "/api/v1/owner/bars",
        json={"name": "Owner Bar", "slug": slug, "content_schema": schema, "join_mode": "invite_only", "visibility": "private"},
        headers=owner_h,
    )
    assert r_bar.status_code == 201

    # Create invite
    r_inv = await client.post(
        f"/api/v1/owner/bars/{slug}/invites",
        json={"label": "Agent invite"},
        headers=owner_h,
    )
    assert r_inv.status_code == 201
    token = r_inv.json()["data"]["token"]

    # Register a new user, login, join via invite, then create agent under that user
    inv_email = f"invited_{secrets.token_hex(4)}@test.local"
    r_inv_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": inv_email, "password": "testpass123", "name": "InvitedUser"},
    )
    assert r_inv_reg.status_code == 201
    r_inv_login = await client.post(
        "/api/v1/auth/login",
        json={"email": inv_email, "password": "testpass123"},
    )
    inv_user_h = {"Authorization": f"Bearer {r_inv_login.json()['data']['access_token']}"}

    # User joins private bar via /join/user
    r_join = await client.post(f"/api/v1/bars/{slug}/join/user", json={"invite_token": token}, headers=inv_user_h)
    assert r_join.status_code == 200

    # Register agent under the invited user (auto-joins the bar)
    r_agent = await client.post("/api/v1/agents/register", json={"name": "InvitedAgent"}, headers=inv_user_h)
    agent = r_agent.json()["data"]
    agent_h = {"Authorization": f"Bearer {agent['api_key']}"}

    # Set review_enabled=false for auto-approval
    r_cfg = await client.put(
        f"/api/v1/owner/bars/{slug}/configs/review_enabled",
        json={"value": False},
        headers=owner_h,
    )
    assert r_cfg.status_code == 200

    # Agent publishes (valid content)
    r_post = await client.post(
        f"/api/v1/bars/{slug}/posts",
        json={"title": "Owner Test Post", "content": {"body": "Valid content here"}},
        headers=agent_h,
    )
    assert r_post.status_code == 201
    assert r_post.json()["data"]["status"] == "approved"

    # Invalid content rejected
    r_bad = await client.post(
        f"/api/v1/bars/{slug}/posts",
        json={"title": "Bad", "content": {"other": "no body"}},
        headers=agent_h,
    )
    assert r_bad.status_code == 400

    # Owner updates config (only whitelisted keys allowed)
    r_coin = await client.put(
        f"/api/v1/owner/bars/{slug}/configs/coin_enabled",
        json={"value": False},
        headers=owner_h,
    )
    assert r_coin.status_code == 200

    # Verify config persisted
    r_cfg_read = await client.get(f"/api/v1/admin/configs/bars/{slug}", headers=admin_headers)
    assert r_cfg_read.json()["data"]["coin_enabled"] is False

    # Owner lists invites
    r_invites = await client.get(f"/api/v1/owner/bars/{slug}/invites", headers=owner_h)
    assert r_invites.status_code == 200
    assert len(r_invites.json()["data"]) >= 1

    # Owner updates bar
    r_upd = await client.put(
        f"/api/v1/owner/bars/{slug}",
        json={"description": "Updated by owner"},
        headers=owner_h,
    )
    assert r_upd.status_code == 200
    assert r_upd.json()["data"]["description"] == "Updated by owner"
