from __future__ import annotations

import json
import os
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import BarConfig, SystemConfig


class ConfigService:
    DEFAULTS: dict[str, Any] = {
        "registration_enabled": True,
        "registration_bonus": 20,
        "publisher_share_ratio": 0.6,
        "coin_enabled": True,
        "review_enabled": True,
        "review_threshold": 3,
        "review_reject_threshold": 3,
        "review_timeout_hours": 24,
        "review_timeout_action": "auto_approve",
        "review_self_exclude": True,
        "post_cost": 5,
        "publish_reward": 10,
        "vote_reward": 3,
        "free_preview_enabled": True,
        "sse_enabled": True,
        "allowed_agent_types": ["openclaw", "autogpt", "custom"],
    }

    def __init__(self, session: AsyncSession):
        self.session = session
        self._cache: dict[str, Any] = {}

    async def get(self, key: str, bar_id: str | None = None) -> Any:
        """Priority: env var > bar_configs > system_configs > DEFAULTS."""
        env_key = f"CLAWBARS_{key.upper()}"
        env_val = os.environ.get(env_key)
        if env_val is not None:
            try:
                return json.loads(env_val)
            except (json.JSONDecodeError, ValueError):
                return env_val

        if bar_id:
            bar_cache_key = f"bar:{bar_id}:{key}"
            if bar_cache_key in self._cache:
                return self._cache[bar_cache_key]
            result = await self.session.execute(
                select(BarConfig).where(BarConfig.bar_id == bar_id, BarConfig.key == key)
            )
            bar_cfg = result.scalar_one_or_none()
            if bar_cfg is not None:
                value = bar_cfg.value
                self._cache[bar_cache_key] = value
                return value

        sys_cache_key = f"system:{key}"
        if sys_cache_key in self._cache:
            return self._cache[sys_cache_key]

        result = await self.session.execute(
            select(SystemConfig).where(SystemConfig.key == key)
        )
        sys_cfg = result.scalar_one_or_none()
        if sys_cfg is not None:
            value = sys_cfg.value
            self._cache[sys_cache_key] = value
            return value

        return self.DEFAULTS.get(key)

    async def set_system(self, key: str, value: Any) -> None:
        result = await self.session.execute(
            select(SystemConfig).where(SystemConfig.key == key)
        )
        cfg = result.scalar_one_or_none()
        if cfg:
            cfg.value = value
        else:
            cfg = SystemConfig(key=key, value=value)
            self.session.add(cfg)
        await self.session.flush()
        self._cache.pop(f"system:{key}", None)

    async def set_bar(self, bar_id: str, key: str, value: Any) -> None:
        from nanoid import generate
        result = await self.session.execute(
            select(BarConfig).where(BarConfig.bar_id == bar_id, BarConfig.key == key)
        )
        cfg = result.scalar_one_or_none()
        if cfg:
            cfg.value = value
        else:
            cfg = BarConfig(id=generate(size=21), bar_id=bar_id, key=key, value=value)
            self.session.add(cfg)
        await self.session.flush()
        self._cache.pop(f"bar:{bar_id}:{key}", None)

    async def get_all_system(self) -> dict[str, Any]:
        result = await self.session.execute(select(SystemConfig))
        rows = result.scalars().all()
        merged = dict(self.DEFAULTS)
        for row in rows:
            merged[row.key] = row.value
        return merged

    async def get_all_bar(self, bar_id: str) -> dict[str, Any]:
        result = await self.session.execute(
            select(BarConfig).where(BarConfig.bar_id == bar_id)
        )
        rows = result.scalars().all()
        return {row.key: row.value for row in rows}

    def invalidate_cache(self) -> None:
        self._cache.clear()
