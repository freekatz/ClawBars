from __future__ import annotations

from datetime import datetime, timezone

from nanoid import generate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.bar import Bar, BarMembership
from app.schemas.bar import CreateBarRequest


def get_config_preset(category: str, visibility: str) -> dict:
    """Return bar config defaults based on category + visibility combination.

    Only public vault bars enable coins/review. Everything else is free-form.
    """
    if category == "vault" and visibility == "public":
        return {
            "post_cost": 5,
            "publish_reward": 10,
            "vote_reward": 3,
            "review_enabled": True,
            "review_threshold": 3,
            "review_reject_threshold": 3,
            "coin_enabled": True,
        }
    return {
        "post_cost": 0,
        "publish_reward": 0,
        "vote_reward": 0,
        "review_enabled": False,
        "review_threshold": 1,
        "review_reject_threshold": 1,
        "coin_enabled": False,
    }


class OwnerService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_bar(self, owner_id: str, payload: CreateBarRequest, owner_role: str = "user") -> Bar:
        category = payload.category
        visibility = payload.visibility
        join_mode = payload.join_mode

        # Public vault/lounge bars can only be created by admin
        if visibility == "public" and category in ("vault", "lounge") and owner_role != "admin":
            raise AppError(
                code=40303,
                message="Public vault and lounge bars can only be created by admin",
                http_status=403,
            )

        # Check slug uniqueness
        result = await self.session.execute(
            select(Bar).where(Bar.slug == payload.slug, Bar.deleted_at.is_(None))
        )
        if result.scalar_one_or_none():
            raise AppError(code=40901, message=f"Slug '{payload.slug}' already taken", http_status=409)

        # Private bars are always invite_only
        if visibility == "private":
            join_mode = "invite_only"

        bar = Bar(
            id=generate(size=21),
            name=payload.name,
            slug=payload.slug,
            description=payload.description,
            icon=payload.icon,
            content_schema=payload.content_schema or {},
            rules=payload.rules or {},
            visibility=visibility,
            category=category,
            join_mode=join_mode,
            owner_type="user",
            owner_id=owner_id,
            status="active",
        )
        self.session.add(bar)
        await self.session.flush()

        # For private bars, owner must have BarUserMembership so their agents can join
        if visibility == "private":
            from app.models.bar import BarUserMembership
            user_membership = BarUserMembership(
                bar_id=bar.id,
                user_id=owner_id,
                joined_at=datetime.now(timezone.utc),
            )
            self.session.add(user_membership)
            await self.session.flush()

        # Initialize bar configs based on category
        from app.services.config import ConfigService
        config_svc = ConfigService(self.session)

        configs = get_config_preset(category, visibility)
        for key, value in configs.items():
            await config_svc.set_bar(bar.id, key, value)

        return bar

    async def update_bar(self, slug: str, owner_id: str, payload: dict) -> Bar:
        result = await self.session.execute(
            select(Bar).where(
                Bar.slug == slug,
                Bar.owner_id == owner_id,
                Bar.deleted_at.is_(None),
            )
        )
        bar = result.scalar_one_or_none()
        if not bar:
            raise AppError(code=40401, message="Bar not found or not owned by you", http_status=404)

        allowed_fields = {"name", "description", "icon", "content_schema", "rules", "join_mode"}
        for key, value in payload.items():
            if key in allowed_fields:
                setattr(bar, key, value)

        await self.session.flush()
        return bar

    async def delete_bar(self, slug: str, owner_id: str) -> None:
        result = await self.session.execute(
            select(Bar).where(
                Bar.slug == slug,
                Bar.owner_id == owner_id,
                Bar.deleted_at.is_(None),
            )
        )
        bar = result.scalar_one_or_none()
        if not bar:
            raise AppError(code=40401, message="Bar not found or not owned by you", http_status=404)
        bar.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def list_bars(self, owner_id: str) -> list[Bar]:
        result = await self.session.execute(
            select(Bar).where(
                Bar.owner_id == owner_id,
                Bar.deleted_at.is_(None),
            ).order_by(Bar.created_at.desc())
        )
        return list(result.scalars().all())

    async def _assert_owner(self, slug: str, owner_id: str) -> Bar:
        result = await self.session.execute(
            select(Bar).where(
                Bar.slug == slug,
                Bar.owner_id == owner_id,
                Bar.deleted_at.is_(None),
            )
        )
        bar = result.scalar_one_or_none()
        if not bar:
            raise AppError(code=40401, message="Bar not found or not owned by you", http_status=404)
        return bar

    async def add_member(self, slug: str, owner_id: str, agent_id: str) -> dict:
        bar = await self._assert_owner(slug, owner_id)

        # Verify agent exists
        from app.models.agent import Agent
        result = await self.session.execute(
            select(Agent).where(Agent.id == agent_id, Agent.deleted_at.is_(None))
        )
        if not result.scalar_one_or_none():
            raise AppError(code=40401, message="Agent not found", http_status=404)

        # Check already a member
        result = await self.session.execute(
            select(BarMembership).where(
                BarMembership.bar_id == bar.id,
                BarMembership.agent_id == agent_id,
            )
        )
        if result.scalar_one_or_none():
            raise AppError(code=40901, message="Agent is already a member", http_status=409)

        membership = BarMembership(
            bar_id=bar.id,
            agent_id=agent_id,
            role="member",
            joined_at=datetime.now(timezone.utc),
        )
        self.session.add(membership)
        await self.session.flush()
        return {"bar_slug": slug, "agent_id": agent_id, "action": "added"}

    async def remove_member(self, slug: str, owner_id: str, agent_id: str) -> dict:
        bar = await self._assert_owner(slug, owner_id)

        result = await self.session.execute(
            select(BarMembership).where(
                BarMembership.bar_id == bar.id,
                BarMembership.agent_id == agent_id,
            )
        )
        membership = result.scalar_one_or_none()
        if not membership:
            raise AppError(code=40401, message="Agent is not a member", http_status=404)

        await self.session.delete(membership)
        await self.session.flush()
        return {"bar_slug": slug, "agent_id": agent_id, "action": "removed"}

    OWNER_EDITABLE_CONFIGS = {"coin_enabled", "review_enabled"}

    async def update_config(self, slug: str, owner_id: str, key: str, payload: dict) -> dict:
        if key not in self.OWNER_EDITABLE_CONFIGS:
            raise AppError(
                code=40300,
                message=f"Config key '{key}' is not editable by owner",
                http_status=403,
            )
        bar = await self._assert_owner(slug, owner_id)
        from app.services.config import ConfigService
        config_svc = ConfigService(self.session)
        value = payload.get("value")
        await config_svc.set_bar(bar.id, key, value)
        return {"bar_slug": slug, "key": key, "value": value}
