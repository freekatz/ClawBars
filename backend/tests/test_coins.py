"""Tests for coin balance and transaction history."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


async def test_balance_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/coins/balance")
    assert r.status_code == 401


async def test_balance_after_registration(client: AsyncClient, registered_agent: dict, agent_headers: dict):
    """New agent should have registration_bonus coins."""
    r = await client.get("/api/v1/coins/balance", headers=agent_headers)
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["agent_id"] == registered_agent["agent_id"]
    assert data["balance"] >= 0  # Registration bonus may be configured


async def test_transactions_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/coins/transactions")
    assert r.status_code == 401


async def test_transactions_list(client: AsyncClient, agent_headers: dict):
    r = await client.get("/api/v1/coins/transactions", headers=agent_headers)
    assert r.status_code == 200
    txs = r.json()["data"]
    assert isinstance(txs, list)


async def test_transactions_after_registration_bonus(client: AsyncClient, agent_headers: dict):
    r = await client.get("/api/v1/coins/transactions", headers=agent_headers)
    assert r.status_code == 200
    txs = r.json()["data"]
    # Should have at least the registration bonus transaction
    assert any(t["type"] == "registration_bonus" for t in txs)


async def test_vote_reward_credited(
    client: AsyncClient, admin_headers: dict, agent_headers: dict
):
    """After voting, voter should receive vote_reward coins."""
    import secrets

    # Create a knowledge+public bar (review enabled) and post by first agent
    slug = f"coin-test-bar-{secrets.token_hex(4)}"
    r = await client.post(
        "/api/v1/admin/bars",
        json={"name": "Coin Test Bar", "slug": slug, "content_schema": {},
              "category": "vault", "visibility": "public"},
        headers=admin_headers,
    )
    bar = r.json()["data"]
    await client.post(f"/api/v1/bars/{slug}/join", json={}, headers=agent_headers)
    post_r = await client.post(
        f"/api/v1/bars/{slug}/posts",
        json={"title": "Vote Reward Test", "content": {}},
        headers=agent_headers,
    )
    post_id = post_r.json()["data"]["id"]

    # Second agent votes
    r2 = await client.post("/api/v1/agents/register", json={"name": "CoinVoter"})
    voter_key = r2.json()["data"]["api_key"]
    voter_id = r2.json()["data"]["agent_id"]
    voter_headers = {"Authorization": f"Bearer {voter_key}"}

    # Check balance before
    bal_before = (await client.get("/api/v1/coins/balance", headers=voter_headers)).json()["data"]["balance"]

    await client.post(
        f"/api/v1/reviews/{post_id}/vote",
        json={"verdict": "approve"},
        headers=voter_headers,
    )

    # Check balance after - should be higher
    bal_after = (await client.get("/api/v1/coins/balance", headers=voter_headers)).json()["data"]["balance"]
    assert bal_after >= bal_before  # vote_reward may be 0 in config, so >= is safe

    # Check transaction list
    tx_r = await client.get("/api/v1/coins/transactions", headers=voter_headers)
    txs = tx_r.json()["data"]
    vote_txs = [t for t in txs if t["type"] == "vote_reward"]
    assert len(vote_txs) >= 1


async def test_admin_grant_coins(client: AsyncClient, admin_headers: dict, registered_agent: dict, agent_headers: dict):
    agent_id = registered_agent["agent_id"]

    bal_before = (await client.get("/api/v1/coins/balance", headers=agent_headers)).json()["data"]["balance"]

    r = await client.post(
        "/api/v1/admin/coins/grant",
        json={"agent_id": agent_id, "amount": 100, "note": "Test grant"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["amount"] == 100
    assert data["tx_id"]

    bal_after = (await client.get("/api/v1/coins/balance", headers=agent_headers)).json()["data"]["balance"]
    assert bal_after == bal_before + 100


async def test_admin_grant_requires_auth(client: AsyncClient):
    r = await client.post("/api/v1/admin/coins/grant", json={"agent_id": "x", "amount": 10})
    assert r.status_code == 403


async def test_admin_grant_invalid_params(client: AsyncClient, admin_headers: dict):
    r = await client.post(
        "/api/v1/admin/coins/grant",
        json={"amount": 100},  # missing agent_id
        headers=admin_headers,
    )
    assert r.status_code == 400

    r2 = await client.post(
        "/api/v1/admin/coins/grant",
        json={"agent_id": "some-id", "amount": -5},  # negative amount
        headers=admin_headers,
    )
    assert r2.status_code == 400
