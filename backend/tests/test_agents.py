"""Tests for agent registration and profile endpoints."""
import pytest
from httpx import AsyncClient


async def test_register_agent_success(client: AsyncClient):
    r = await client.post(
        "/api/v1/agents/register",
        json={"name": "MyBot", "agent_type": "custom", "model_info": "gpt-4o"},
    )
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["agent_id"]
    assert data["api_key"]
    assert data["balance"] >= 0


async def test_register_agent_minimal(client: AsyncClient):
    r = await client.post(
        "/api/v1/agents/register",
        json={"name": "MinimalBot"},
    )
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["agent_id"]


async def test_register_agent_name_too_short(client: AsyncClient):
    r = await client.post(
        "/api/v1/agents/register",
        json={"name": "X"},
    )
    assert r.status_code == 400


async def test_register_agent_returns_unique_keys(client: AsyncClient):
    r1 = await client.post("/api/v1/agents/register", json={"name": "Bot-A"})
    r2 = await client.post("/api/v1/agents/register", json={"name": "Bot-B"})
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["data"]["api_key"] != r2.json()["data"]["api_key"]
    assert r1.json()["data"]["agent_id"] != r2.json()["data"]["agent_id"]


async def test_get_me_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/agents/me")
    assert r.status_code == 401


async def test_get_me_success(client: AsyncClient, registered_agent: dict):
    r = await client.get(
        "/api/v1/agents/me",
        headers={"Authorization": f"Bearer {registered_agent['api_key']}"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["id"] == registered_agent["agent_id"]
    assert data["status"] == "active"
    assert "balance" in data


async def test_get_me_invalid_key(client: AsyncClient):
    r = await client.get(
        "/api/v1/agents/me",
        headers={"Authorization": "Bearer invalid-key-xyz"},
    )
    assert r.status_code == 401


async def test_get_agent_by_id(client: AsyncClient, registered_agent: dict):
    agent_id = registered_agent["agent_id"]
    r = await client.get(f"/api/v1/agents/{agent_id}")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["id"] == agent_id


async def test_get_agent_not_found(client: AsyncClient):
    r = await client.get("/api/v1/agents/nonexistent-id-12345678901")
    assert r.status_code == 404


async def test_list_agents(client: AsyncClient, registered_agent: dict):
    r = await client.get("/api/v1/agents")
    assert r.status_code == 200
    agents = r.json()["data"]
    assert isinstance(agents, list)
    ids = [a["id"] for a in agents]
    assert registered_agent["agent_id"] in ids


async def test_list_agents_filter_by_type(client: AsyncClient):
    await client.post("/api/v1/agents/register", json={"name": "TypeBot", "agent_type": "openclaw"})
    r = await client.get("/api/v1/agents?agent_type=openclaw")
    assert r.status_code == 200
    agents = r.json()["data"]
    for a in agents:
        assert a["agent_type"] == "openclaw"
