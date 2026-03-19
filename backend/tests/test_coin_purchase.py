"""C1: Coin system purchase flow tests."""
import secrets

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _setup_bar_and_approved_post(
    client: AsyncClient,
    admin_headers: dict,
    publisher_headers: dict,
    publisher_id: str,
    *,
    post_cost: int | None = None,
    bar_slug: str | None = None,
) -> tuple[dict, dict]:
    """Create a knowledge+public bar, join, post, approve, and return (bar, post)."""
    slug = bar_slug or f"coin-bar-{secrets.token_hex(4)}"
    r = await client.post(
        "/api/v1/admin/bars",
        json={"name": "Coin Bar", "slug": slug, "content_schema": {}, "join_mode": "open",
              "category": "vault", "visibility": "public"},
        headers=admin_headers,
    )
    assert r.status_code == 201
    bar = r.json()["data"]

    # Set review_threshold to 1 for easy approval
    await client.put(
        f"/api/v1/admin/configs/bars/{slug}/review_threshold",
        json={"value": 1},
        headers=admin_headers,
    )

    await client.post(f"/api/v1/bars/{slug}/join", json={}, headers=publisher_headers)

    post_data = {"title": "Paid Post", "summary": "A valuable insight", "content": {"secret": "data"}}
    if post_cost is not None:
        post_data["cost"] = post_cost
    r_post = await client.post(f"/api/v1/bars/{slug}/posts", json=post_data, headers=publisher_headers)
    assert r_post.status_code == 201
    post = r_post.json()["data"]

    # Approve with a different agent
    r_voter = await client.post("/api/v1/agents/register", json={"name": f"Approver-{secrets.token_hex(3)}"})
    voter_h = {"Authorization": f"Bearer {r_voter.json()['data']['api_key']}"}
    vote_r = await client.post(
        f"/api/v1/reviews/{post['id']}/vote",
        json={"verdict": "approve"},
        headers=voter_h,
    )
    assert vote_r.status_code == 200
    assert vote_r.json()["data"]["status"] == "approved"

    return bar, post


async def _get_balance(client: AsyncClient, headers: dict) -> int:
    r = await client.get("/api/v1/coins/balance", headers=headers)
    assert r.status_code == 200
    return r.json()["data"]["balance"]


# ── Tests ──────────────────────────────────────────────────────────────────────

async def test_paid_access_deducts_coins(
    client: AsyncClient, admin_headers: dict, agent_headers: dict, registered_agent: dict,
):
    """Agent buys full post → coins debited, PostAccess created, publisher paid."""
    publisher = registered_agent
    pub_h = agent_headers

    # Create buyer
    r_buyer = await client.post("/api/v1/agents/register", json={"name": "Buyer"})
    buyer = r_buyer.json()["data"]
    buyer_h = {"Authorization": f"Bearer {buyer['api_key']}"}

    bar, post = await _setup_bar_and_approved_post(client, admin_headers, pub_h, publisher["agent_id"])

    balance_before = await _get_balance(client, buyer_h)

    r = await client.get(f"/api/v1/posts/{post['id']}", headers=buyer_h)
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["content"]["secret"] == "data"

    balance_after = await _get_balance(client, buyer_h)
    assert balance_after < balance_before


async def test_already_purchased_no_second_charge(
    client: AsyncClient, admin_headers: dict, agent_headers: dict, registered_agent: dict,
):
    """Second request for same post → no additional coin deduction."""
    r_buyer = await client.post("/api/v1/agents/register", json={"name": "RepeatBuyer"})
    buyer = r_buyer.json()["data"]
    buyer_h = {"Authorization": f"Bearer {buyer['api_key']}"}

    bar, post = await _setup_bar_and_approved_post(client, admin_headers, agent_headers, registered_agent["agent_id"])

    r1 = await client.get(f"/api/v1/posts/{post['id']}", headers=buyer_h)
    assert r1.status_code == 200
    balance_after_first = await _get_balance(client, buyer_h)

    r2 = await client.get(f"/api/v1/posts/{post['id']}", headers=buyer_h)
    assert r2.status_code == 200
    balance_after_second = await _get_balance(client, buyer_h)

    assert balance_after_first == balance_after_second


async def test_insufficient_balance_returns_402(
    client: AsyncClient, admin_headers: dict, agent_headers: dict, registered_agent: dict,
):
    """Agent with 0 coins cannot buy a post → 402."""
    bar, post = await _setup_bar_and_approved_post(client, admin_headers, agent_headers, registered_agent["agent_id"])

    # Set a high post cost
    await client.put(
        f"/api/v1/admin/configs/bars/{bar['slug']}/post_cost",
        json={"value": 9999},
        headers=admin_headers,
    )

    # Create a buyer and drain their coins
    r_buyer = await client.post("/api/v1/agents/register", json={"name": "PoorBuyer"})
    buyer = r_buyer.json()["data"]
    buyer_h = {"Authorization": f"Bearer {buyer['api_key']}"}

    r = await client.get(f"/api/v1/posts/{post['id']}", headers=buyer_h)
    assert r.status_code == 402


async def test_free_mode_no_deduction(
    client: AsyncClient, admin_headers: dict, agent_headers: dict, registered_agent: dict,
):
    """When coin_enabled=false at bar level, agent gets full content without charge."""
    bar, post = await _setup_bar_and_approved_post(client, admin_headers, agent_headers, registered_agent["agent_id"])

    # Disable coins at bar level (bar-level config takes precedence over system-level)
    await client.put(
        f"/api/v1/admin/configs/bars/{bar['slug']}/coin_enabled",
        json={"value": False},
        headers=admin_headers,
    )

    r_buyer = await client.post("/api/v1/agents/register", json={"name": "FreeBuyer"})
    buyer_h = {"Authorization": f"Bearer {r_buyer.json()['data']['api_key']}"}
    balance_before = await _get_balance(client, buyer_h)

    r = await client.get(f"/api/v1/posts/{post['id']}", headers=buyer_h)
    assert r.status_code == 200
    assert r.json()["data"]["content"]["secret"] == "data"

    balance_after = await _get_balance(client, buyer_h)
    assert balance_after == balance_before


async def test_custom_post_cost(
    client: AsyncClient, admin_headers: dict, agent_headers: dict, registered_agent: dict,
):
    """Post with explicit cost overrides bar default."""
    bar, post = await _setup_bar_and_approved_post(
        client, admin_headers, agent_headers, registered_agent["agent_id"],
        post_cost=2,
    )

    r_buyer = await client.post("/api/v1/agents/register", json={"name": "CostBuyer"})
    buyer_h = {"Authorization": f"Bearer {r_buyer.json()['data']['api_key']}"}
    balance_before = await _get_balance(client, buyer_h)

    r = await client.get(f"/api/v1/posts/{post['id']}", headers=buyer_h)
    assert r.status_code == 200

    balance_after = await _get_balance(client, buyer_h)
    assert balance_before - balance_after == 2


async def test_publisher_receives_share(
    client: AsyncClient, admin_headers: dict, agent_headers: dict, registered_agent: dict,
):
    """Publisher gets publisher_share_ratio of the purchase price."""
    bar, post = await _setup_bar_and_approved_post(
        client, admin_headers, agent_headers, registered_agent["agent_id"],
        post_cost=10,
    )

    publisher_balance_before = await _get_balance(client, agent_headers)

    r_buyer = await client.post("/api/v1/agents/register", json={"name": "ShareBuyer"})
    buyer_h = {"Authorization": f"Bearer {r_buyer.json()['data']['api_key']}"}

    # Grant buyer enough coins
    await client.post(
        "/api/v1/admin/coins/grant",
        json={"agent_id": r_buyer.json()["data"]["agent_id"], "amount": 100},
        headers=admin_headers,
    )

    r = await client.get(f"/api/v1/posts/{post['id']}", headers=buyer_h)
    assert r.status_code == 200

    publisher_balance_after = await _get_balance(client, agent_headers)
    # Default publisher_share_ratio is 0.6 → int(10 * 0.6) = 6
    share = publisher_balance_after - publisher_balance_before
    assert share == 6


async def test_view_count_incremented(
    client: AsyncClient, admin_headers: dict, agent_headers: dict, registered_agent: dict,
):
    """view_count increases after purchase."""
    bar, post = await _setup_bar_and_approved_post(
        client, admin_headers, agent_headers, registered_agent["agent_id"],
        post_cost=0,
    )

    r_buyer = await client.post("/api/v1/agents/register", json={"name": "ViewBuyer"})
    buyer_h = {"Authorization": f"Bearer {r_buyer.json()['data']['api_key']}"}

    # Get preview to check initial view_count
    r_preview = await client.get(f"/api/v1/posts/{post['id']}/preview")
    initial_views = r_preview.json()["data"]["view_count"]

    r = await client.get(f"/api/v1/posts/{post['id']}", headers=buyer_h)
    assert r.status_code == 200

    r_preview2 = await client.get(f"/api/v1/posts/{post['id']}/preview")
    assert r_preview2.json()["data"]["view_count"] == initial_views + 1


async def test_post_author_views_own_post_free(
    client: AsyncClient, admin_headers: dict, agent_headers: dict, registered_agent: dict,
):
    """Post author can view their own post without paying."""
    bar, post = await _setup_bar_and_approved_post(
        client, admin_headers, agent_headers, registered_agent["agent_id"],
    )
    balance_before = await _get_balance(client, agent_headers)

    r = await client.get(f"/api/v1/posts/{post['id']}", headers=agent_headers)
    assert r.status_code == 200

    balance_after = await _get_balance(client, agent_headers)
    assert balance_after == balance_before
