"""C9: Admin full suite tests."""
import secrets

import pytest
from httpx import AsyncClient


async def test_grant_coins_increases_balance(client: AsyncClient, admin_headers: dict):
    """Admin grant coins → balance increases + transaction created."""
    r_agent = await client.post("/api/v1/agents/register", json={"name": "GrantTarget"})
    agent = r_agent.json()["data"]
    agent_h = {"Authorization": f"Bearer {agent['api_key']}"}

    initial = (await client.get("/api/v1/coins/balance", headers=agent_h)).json()["data"]["balance"]

    r = await client.post(
        "/api/v1/admin/coins/grant",
        json={"agent_id": agent["agent_id"], "amount": 100, "note": "Test grant"},
        headers=admin_headers,
    )
    assert r.status_code == 200

    after = (await client.get("/api/v1/coins/balance", headers=agent_h)).json()["data"]["balance"]
    assert after - initial == 100

    txs = (await client.get("/api/v1/coins/transactions", headers=agent_h)).json()["data"]
    grant_txs = [t for t in txs if t["type"] == "system_grant"]
    assert len(grant_txs) >= 1
    assert grant_txs[0]["amount"] == 100


async def test_update_user_role(client: AsyncClient, admin_headers: dict, registered_user: dict):
    """Admin updates user role from free → premium."""
    user_id = registered_user["id"]

    r = await client.put(
        f"/api/v1/admin/users/{user_id}/role",
        json={"role": "premium"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["data"]["role"] == "premium"


async def test_update_agent_status_suspended(client: AsyncClient, admin_headers: dict):
    """Admin suspends agent → agent auth fails."""
    r_agent = await client.post("/api/v1/agents/register", json={"name": "SuspendMe"})
    agent = r_agent.json()["data"]
    agent_h = {"Authorization": f"Bearer {agent['api_key']}"}

    # Verify agent works
    r = await client.get("/api/v1/coins/balance", headers=agent_h)
    assert r.status_code == 200

    # Suspend
    r_susp = await client.put(
        f"/api/v1/admin/agents/{agent['agent_id']}/status",
        json={"status": "suspended"},
        headers=admin_headers,
    )
    assert r_susp.status_code == 200

    # Verify agent auth now fails (returns None → 401)
    r_fail = await client.get("/api/v1/coins/balance", headers=agent_h)
    assert r_fail.status_code == 401


async def test_activity_log_filter_by_event_type(client: AsyncClient, admin_headers: dict):
    """Activity log can be filtered by event_type."""
    # Register an agent to generate activity
    await client.post("/api/v1/agents/register", json={"name": "LogAgent"})

    r = await client.get("/api/v1/admin/activity-log?event_type=agent_register", headers=admin_headers)
    assert r.status_code == 200
    logs = r.json()["data"]
    assert len(logs) >= 1
    assert all(log["event_type"] == "agent_register" for log in logs)


async def test_bar_config_management(client: AsyncClient, admin_headers: dict):
    """Admin reads/writes bar-level configs."""
    slug = f"admcfg-{secrets.token_hex(4)}"
    await client.post(
        "/api/v1/admin/bars",
        json={"name": "AdminCfgBar", "slug": slug, "content_schema": {}},
        headers=admin_headers,
    )

    r_set = await client.put(
        f"/api/v1/admin/configs/bars/{slug}/review_threshold",
        json={"value": 5},
        headers=admin_headers,
    )
    assert r_set.status_code == 200

    r_get = await client.get(f"/api/v1/admin/configs/bars/{slug}", headers=admin_headers)
    assert r_get.status_code == 200
    assert r_get.json()["data"]["review_threshold"] == 5


async def test_admin_invalid_role_rejected(client: AsyncClient, admin_headers: dict, registered_user: dict):
    """Invalid role value → 400."""
    user_id = registered_user["id"]
    r = await client.put(
        f"/api/v1/admin/users/{user_id}/role",
        json={"role": "superadmin"},
        headers=admin_headers,
    )
    assert r.status_code == 400


async def test_admin_grant_invalid_amount(client: AsyncClient, admin_headers: dict):
    """Granting 0 or negative coins → 400."""
    r_agent = await client.post("/api/v1/agents/register", json={"name": "BadGrant"})
    agent = r_agent.json()["data"]

    r = await client.post(
        "/api/v1/admin/coins/grant",
        json={"agent_id": agent["agent_id"], "amount": -5},
        headers=admin_headers,
    )
    assert r.status_code == 400
