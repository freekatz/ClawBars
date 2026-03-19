"""C2: Review system enhanced tests."""
import secrets

import pytest
from httpx import AsyncClient


async def _create_bar_and_member(client: AsyncClient, admin_headers: dict) -> tuple[dict, dict, dict]:
    """Create knowledge+public bar, register + join agent, return (bar, agent_data, agent_headers)."""
    slug = f"rev-bar-{secrets.token_hex(4)}"
    r = await client.post(
        "/api/v1/admin/bars",
        json={"name": "Review Bar", "slug": slug, "content_schema": {}, "join_mode": "open",
              "category": "vault", "visibility": "public"},
        headers=admin_headers,
    )
    bar = r.json()["data"]

    r_agent = await client.post("/api/v1/agents/register", json={"name": f"Poster-{secrets.token_hex(3)}"})
    agent = r_agent.json()["data"]
    h = {"Authorization": f"Bearer {agent['api_key']}"}
    await client.post(f"/api/v1/bars/{slug}/join", json={}, headers=h)

    return bar, agent, h


async def _post(client: AsyncClient, slug: str, headers: dict) -> dict:
    r = await client.post(
        f"/api/v1/bars/{slug}/posts",
        json={"title": f"Post-{secrets.token_hex(3)}", "summary": "Review me", "content": {"body": "x"}},
        headers=headers,
    )
    assert r.status_code == 201
    return r.json()["data"]


async def _get_balance(client: AsyncClient, headers: dict) -> int:
    r = await client.get("/api/v1/coins/balance", headers=headers)
    return r.json()["data"]["balance"]


async def test_publish_reward_on_approval(client: AsyncClient, admin_headers: dict):
    """Publisher receives publish_reward coins when post is approved."""
    bar, publisher, pub_h = await _create_bar_and_member(client, admin_headers)
    slug = bar["slug"]

    await client.put(f"/api/v1/admin/configs/bars/{slug}/review_threshold", json={"value": 1}, headers=admin_headers)

    balance_before = await _get_balance(client, pub_h)
    post = await _post(client, slug, pub_h)

    # Vote to approve
    r_voter = await client.post("/api/v1/agents/register", json={"name": "ApproverR"})
    voter_h = {"Authorization": f"Bearer {r_voter.json()['data']['api_key']}"}
    r = await client.post(f"/api/v1/reviews/{post['id']}/vote", json={"verdict": "approve"}, headers=voter_h)
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "approved"

    balance_after = await _get_balance(client, pub_h)
    # Default publish_reward is 10
    assert balance_after - balance_before == 10


async def test_vote_reward_credited(client: AsyncClient, admin_headers: dict):
    """Voter receives vote_reward coins for casting a vote."""
    bar, publisher, pub_h = await _create_bar_and_member(client, admin_headers)
    post = await _post(client, bar["slug"], pub_h)

    r_voter = await client.post("/api/v1/agents/register", json={"name": "RewardVoter"})
    voter = r_voter.json()["data"]
    voter_h = {"Authorization": f"Bearer {voter['api_key']}"}

    balance_before = await _get_balance(client, voter_h)
    await client.post(f"/api/v1/reviews/{post['id']}/vote", json={"verdict": "approve"}, headers=voter_h)
    balance_after = await _get_balance(client, voter_h)

    # Default vote_reward is 3
    assert balance_after - balance_before == 3


async def test_review_disabled_auto_approves(client: AsyncClient, admin_headers: dict):
    """When review_enabled=false, post is auto-approved with publish_reward."""
    bar, publisher, pub_h = await _create_bar_and_member(client, admin_headers)
    slug = bar["slug"]

    # Disable review at bar level (overrides the knowledge+public default)
    await client.put(f"/api/v1/admin/configs/bars/{slug}/review_enabled", json={"value": False}, headers=admin_headers)

    balance_before = await _get_balance(client, pub_h)

    r = await client.post(
        f"/api/v1/bars/{slug}/posts",
        json={"title": "Auto Approved", "summary": "No review needed", "content": {"body": "x"}},
        headers=pub_h,
    )
    assert r.status_code == 201
    post = r.json()["data"]
    assert post["status"] == "approved"

    balance_after = await _get_balance(client, pub_h)
    assert balance_after - balance_before == 10  # publish_reward


async def test_self_exclusion_in_pending(client: AsyncClient, admin_headers: dict):
    """Agent cannot see own pending posts in /reviews/pending."""
    bar, publisher, pub_h = await _create_bar_and_member(client, admin_headers)
    post = await _post(client, bar["slug"], pub_h)

    r = await client.get("/api/v1/reviews/pending", headers=pub_h)
    assert r.status_code == 200
    pending_ids = [p["id"] for p in r.json()["data"]]
    assert post["id"] not in pending_ids


async def test_other_agent_sees_pending(client: AsyncClient, admin_headers: dict):
    """A different agent can see the pending post."""
    bar, publisher, pub_h = await _create_bar_and_member(client, admin_headers)
    post = await _post(client, bar["slug"], pub_h)

    r_other = await client.post("/api/v1/agents/register", json={"name": "OtherReviewer"})
    other_h = {"Authorization": f"Bearer {r_other.json()['data']['api_key']}"}

    r = await client.get("/api/v1/reviews/pending", headers=other_h)
    assert r.status_code == 200
    pending_ids = [p["id"] for p in r.json()["data"]]
    assert post["id"] in pending_ids


async def test_vote_on_own_post_rejected(client: AsyncClient, admin_headers: dict):
    """Agent cannot vote on own post → 403."""
    bar, publisher, pub_h = await _create_bar_and_member(client, admin_headers)
    post = await _post(client, bar["slug"], pub_h)

    r = await client.post(f"/api/v1/reviews/{post['id']}/vote", json={"verdict": "approve"}, headers=pub_h)
    assert r.status_code == 403


async def test_double_vote_rejected(client: AsyncClient, admin_headers: dict):
    """Agent cannot vote twice on same post → 409."""
    bar, publisher, pub_h = await _create_bar_and_member(client, admin_headers)
    post = await _post(client, bar["slug"], pub_h)

    r_voter = await client.post("/api/v1/agents/register", json={"name": "DoubleVoter"})
    voter_h = {"Authorization": f"Bearer {r_voter.json()['data']['api_key']}"}

    r1 = await client.post(f"/api/v1/reviews/{post['id']}/vote", json={"verdict": "approve"}, headers=voter_h)
    assert r1.status_code == 200
    r2 = await client.post(f"/api/v1/reviews/{post['id']}/vote", json={"verdict": "reject"}, headers=voter_h)
    assert r2.status_code == 409
