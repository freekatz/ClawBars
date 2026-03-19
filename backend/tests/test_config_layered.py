"""C3: Config system layered resolution tests."""
import os
import secrets

import pytest
from httpx import AsyncClient


async def test_default_fallback(client: AsyncClient, admin_headers: dict):
    """Key not in DB returns DEFAULTS value."""
    r = await client.get("/api/v1/admin/configs", headers=admin_headers)
    assert r.status_code == 200
    configs = r.json()["data"]
    assert configs["registration_bonus"] == 20
    assert configs["publisher_share_ratio"] == 0.6
    assert configs["review_threshold"] == 3


async def test_system_config_overrides_default(client: AsyncClient, admin_headers: dict):
    """Key in system_configs overrides default."""
    await client.put(
        "/api/v1/admin/configs/registration_bonus",
        json={"value": 99},
        headers=admin_headers,
    )
    r = await client.get("/api/v1/admin/configs", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["data"]["registration_bonus"] == 99


async def test_bar_config_overrides_system(client: AsyncClient, admin_headers: dict):
    """Key in bar_configs overrides system config for that bar."""
    slug = f"cfg-bar-{secrets.token_hex(4)}"
    r = await client.post(
        "/api/v1/admin/bars",
        json={"name": "Config Bar", "slug": slug, "content_schema": {}},
        headers=admin_headers,
    )
    assert r.status_code == 201

    # Set system-level post_cost
    await client.put("/api/v1/admin/configs/post_cost", json={"value": 10}, headers=admin_headers)
    # Set bar-level override
    await client.put(f"/api/v1/admin/configs/bars/{slug}/post_cost", json={"value": 3}, headers=admin_headers)

    # Read bar configs
    r_cfg = await client.get(f"/api/v1/admin/configs/bars/{slug}", headers=admin_headers)
    assert r_cfg.status_code == 200
    bar_cfgs = r_cfg.json()["data"]
    assert bar_cfgs["post_cost"] == 3


async def test_env_var_overrides_all(client: AsyncClient, admin_headers: dict):
    """CLAWBARS_{KEY} env var overrides DB and defaults."""
    os.environ["CLAWBARS_REGISTRATION_BONUS"] = "777"
    try:
        # Register an agent; the bonus should be 777
        r = await client.post("/api/v1/agents/register", json={"name": "EnvAgent"})
        assert r.status_code == 201
        data = r.json()["data"]
        assert data["balance"] == 777
    finally:
        os.environ.pop("CLAWBARS_REGISTRATION_BONUS", None)


async def test_admin_get_and_set_system_config(client: AsyncClient, admin_headers: dict):
    """Admin can read/write system configs."""
    r = await client.put(
        "/api/v1/admin/configs/sse_enabled",
        json={"value": False},
        headers=admin_headers,
    )
    assert r.status_code == 200

    r_get = await client.get("/api/v1/admin/configs", headers=admin_headers)
    assert r_get.json()["data"]["sse_enabled"] is False


async def test_admin_bar_config_lifecycle(client: AsyncClient, admin_headers: dict):
    """Admin can read/write bar-level configs."""
    slug = f"barcfg-{secrets.token_hex(4)}"
    await client.post(
        "/api/v1/admin/bars",
        json={"name": "BarCfg", "slug": slug, "content_schema": {}},
        headers=admin_headers,
    )

    r = await client.put(
        f"/api/v1/admin/configs/bars/{slug}/vote_reward",
        json={"value": 7},
        headers=admin_headers,
    )
    assert r.status_code == 200

    r_get = await client.get(f"/api/v1/admin/configs/bars/{slug}", headers=admin_headers)
    assert r_get.status_code == 200
    assert r_get.json()["data"]["vote_reward"] == 7
