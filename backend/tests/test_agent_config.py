"""C6: Agent registration config-driven tests."""
import secrets

import pytest
from httpx import AsyncClient


async def test_registration_disabled(client: AsyncClient, admin_headers: dict):
    """registration_enabled=false blocks new agents."""
    await client.put(
        "/api/v1/admin/configs/registration_enabled",
        json={"value": False},
        headers=admin_headers,
    )
    try:
        r = await client.post("/api/v1/agents/register", json={"name": "Blocked"})
        assert r.status_code == 403
    finally:
        await client.put(
            "/api/v1/admin/configs/registration_enabled",
            json={"value": True},
            headers=admin_headers,
        )


async def test_registration_bonus_credited(client: AsyncClient, admin_headers: dict):
    """New agent starts with registration_bonus coins + transaction record."""
    await client.put(
        "/api/v1/admin/configs/registration_bonus",
        json={"value": 50},
        headers=admin_headers,
    )

    r = await client.post("/api/v1/agents/register", json={"name": "BonusAgent"})
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["balance"] == 50

    h = {"Authorization": f"Bearer {data['api_key']}"}
    r_tx = await client.get("/api/v1/coins/transactions", headers=h)
    assert r_tx.status_code == 200
    txs = r_tx.json()["data"]
    bonus_txs = [t for t in txs if t["type"] == "registration_bonus"]
    assert len(bonus_txs) == 1
    assert bonus_txs[0]["amount"] == 50


async def test_disallowed_agent_type_rejected(client: AsyncClient, admin_headers: dict):
    """Agent with type not in allowed_agent_types is rejected."""
    await client.put(
        "/api/v1/admin/configs/allowed_agent_types",
        json={"value": ["openclaw"]},
        headers=admin_headers,
    )
    try:
        r = await client.post(
            "/api/v1/agents/register",
            json={"name": "BadType", "agent_type": "forbidden_type"},
        )
        assert r.status_code == 400
    finally:
        await client.put(
            "/api/v1/admin/configs/allowed_agent_types",
            json={"value": ["openclaw", "autogpt", "custom"]},
            headers=admin_headers,
        )


async def test_api_key_uniqueness(client: AsyncClient):
    """Each registered agent gets a unique API key."""
    keys = set()
    for i in range(5):
        r = await client.post("/api/v1/agents/register", json={"name": f"UniqueKey{i}"})
        assert r.status_code == 201
        keys.add(r.json()["data"]["api_key"])
    assert len(keys) == 5


async def test_agent_api_key_not_stored_raw(client: AsyncClient, admin_headers: dict):
    """Agent list endpoint does NOT expose raw API key or key_hash."""
    r_reg = await client.post("/api/v1/agents/register", json={"name": "SecretAgent"})
    agent = r_reg.json()["data"]

    r_list = await client.get("/api/v1/admin/agents", headers=admin_headers)
    agents = r_list.json()["data"]
    found = [a for a in agents if a["id"] == agent["agent_id"]]
    assert len(found) == 1
    assert "api_key" not in found[0]
    assert "api_key_hash" not in found[0]
