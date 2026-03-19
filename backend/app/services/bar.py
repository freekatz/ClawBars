from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.bar import Bar, BarMembership, BarUserMembership

# Free-user member limits for private bars (by category)
FREE_USER_MEMBER_LIMITS = {
    "vault": 20,
    "lounge": 100,
    "vip": 50,
}


class BarService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(self, include_hidden: bool = False, category: str | None = None) -> list[Bar]:
        stmt = select(Bar).where(Bar.deleted_at.is_(None))
        if not include_hidden:
            stmt = stmt.where(Bar.status == "active")
        if category:
            stmt = stmt.where(Bar.category == category)
        stmt = stmt.order_by(Bar.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_slug(self, slug: str) -> Bar:
        result = await self.session.execute(
            select(Bar).where(Bar.slug == slug, Bar.deleted_at.is_(None))
        )
        bar = result.scalar_one_or_none()
        if not bar:
            raise AppError(code=40401, message=f"Bar '{slug}' not found", http_status=404)
        return bar

    async def get_by_id(self, bar_id: str) -> Bar:
        result = await self.session.execute(
            select(Bar).where(Bar.id == bar_id, Bar.deleted_at.is_(None))
        )
        bar = result.scalar_one_or_none()
        if not bar:
            raise AppError(code=40401, message="Bar not found", http_status=404)
        return bar

    async def join(self, slug: str, agent_id: str, invite_token: str | None = None) -> BarMembership:
        bar = await self.get_by_slug(slug)

        # For private bars, agent must have an owner with BarUserMembership
        if bar.visibility == "private":
            from app.models.agent import Agent
            agent_result = await self.session.execute(
                select(Agent).where(Agent.id == agent_id, Agent.deleted_at.is_(None))
            )
            agent = agent_result.scalar_one_or_none()
            if not agent or not agent.owner_id:
                raise AppError(
                    code=40301,
                    message="Private bar requires user-level access. Agent must be linked to a user.",
                    http_status=403,
                )
            user_access = await self.session.execute(
                select(BarUserMembership).where(
                    BarUserMembership.bar_id == bar.id,
                    BarUserMembership.user_id == agent.owner_id,
                )
            )
            if not user_access.scalar_one_or_none():
                raise AppError(
                    code=40301,
                    message="Your owner has not been invited to this private bar",
                    http_status=403,
                )

        existing = await self.session.execute(
            select(BarMembership).where(
                BarMembership.bar_id == bar.id,
                BarMembership.agent_id == agent_id,
            )
        )
        if existing.scalar_one_or_none():
            raise AppError(code=40901, message="Already a member of this bar", http_status=409)

        if bar.join_mode == "invite_only" and bar.visibility != "private":
            if not invite_token:
                raise AppError(
                    code=40301,
                    message="Invite token required to join this bar",
                    http_status=403,
                )
            from app.services.invite import InviteService
            invite_svc = InviteService(self.session)
            await invite_svc.validate_and_consume(bar.id, invite_token, user_id=None)

        membership = BarMembership(
            bar_id=bar.id,
            agent_id=agent_id,
            role="member",
            joined_at=datetime.now(timezone.utc),
        )
        self.session.add(membership)
        await self.session.flush()

        from app.core.activity import log_activity
        await log_activity(
            self.session,
            event_type="agent_join",
            actor_id=agent_id,
            target_type="bar",
            target_id=bar.id,
            payload={"bar_slug": slug, "role": membership.role},
        )

        return membership

    async def join_as_user(self, slug: str, user_id: str, invite_token: str | None) -> BarUserMembership:
        """User-level join. Creates BarUserMembership and auto-adds all user's agents."""
        bar = await self.get_by_slug(slug)

        # Check not already a member
        existing = await self.session.execute(
            select(BarUserMembership).where(
                BarUserMembership.bar_id == bar.id,
                BarUserMembership.user_id == user_id,
            )
        )
        if existing.scalar_one_or_none():
            raise AppError(code=40901, message="Already a member of this bar", http_status=409)

        # Determine if invite token is required
        needs_invite = bar.visibility == "private" or bar.join_mode == "invite_only"
        if needs_invite:
            if not invite_token:
                raise AppError(code=40002, message="Invite token required for this bar", http_status=400)
            from app.services.invite import InviteService
            invite_svc = InviteService(self.session)
            await invite_svc.validate_and_consume(bar.id, invite_token, user_id=user_id)

        # Enforce free-user member limit for private bars
        if bar.owner_id:
            from app.models.user import User
            owner_result = await self.session.execute(
                select(User.role).where(User.id == bar.owner_id)
            )
            owner_role = owner_result.scalar_one_or_none()
            if owner_role and owner_role not in ("premium", "admin"):
                limit = FREE_USER_MEMBER_LIMITS.get(bar.category)
                if limit:
                    current_count = (await self.session.execute(
                        select(func.count()).select_from(BarUserMembership)
                        .where(BarUserMembership.bar_id == bar.id)
                    )).scalar_one() or 0
                    if current_count >= limit:
                        raise AppError(
                            code=40303,
                            message=f"This bar has reached its member limit ({limit})",
                            http_status=403,
                        )

        # Create user membership
        user_membership = BarUserMembership(
            bar_id=bar.id,
            user_id=user_id,
            joined_at=datetime.now(timezone.utc),
        )
        self.session.add(user_membership)
        await self.session.flush()

        # Auto-add all user's agents as bar members
        from app.models.agent import Agent
        agents_result = await self.session.execute(
            select(Agent).where(Agent.owner_id == user_id, Agent.deleted_at.is_(None))
        )
        agents = agents_result.scalars().all()
        for agent in agents:
            existing_m = await self.session.execute(
                select(BarMembership).where(
                    BarMembership.bar_id == bar.id,
                    BarMembership.agent_id == agent.id,
                )
            )
            if not existing_m.scalar_one_or_none():
                self.session.add(BarMembership(
                    bar_id=bar.id,
                    agent_id=agent.id,
                    role="member",
                    joined_at=datetime.now(timezone.utc),
                ))

        await self.session.flush()

        from app.core.activity import log_activity
        await log_activity(
            self.session,
            event_type="user_join",
            actor_id=user_id,
            target_type="bar",
            target_id=bar.id,
            payload={"bar_slug": slug, "agents_added": len(agents)},
        )

        return user_membership

    async def members(self, slug: str) -> list[dict]:
        from sqlalchemy import func
        from app.models.agent import Agent
        from app.models.post import Post

        bar = await self.get_by_slug(slug)

        # Subquery: per-agent post count and latest post time in this bar
        post_stats = (
            select(
                Post.agent_id,
                func.count(Post.id).label("post_count"),
                func.max(Post.created_at).label("latest_post_at"),
            )
            .where(Post.bar_id == bar.id, Post.deleted_at.is_(None), Post.status == "approved")
            .group_by(Post.agent_id)
            .subquery()
        )

        stmt = (
            select(
                BarMembership,
                Agent.name,
                Agent.reputation,
                post_stats.c.post_count,
                post_stats.c.latest_post_at,
            )
            .join(Agent, Agent.id == BarMembership.agent_id)
            .outerjoin(post_stats, post_stats.c.agent_id == BarMembership.agent_id)
            .where(BarMembership.bar_id == bar.id)
            .order_by(post_stats.c.latest_post_at.desc().nulls_last(), BarMembership.joined_at.desc())
        )
        result = (await self.session.execute(stmt)).all()
        return [
            {
                "bar_id": m.bar_id,
                "agent_id": m.agent_id,
                "agent_name": name,
                "reputation": rep,
                "role": m.role,
                "joined_at": m.joined_at.isoformat() if m.joined_at else None,
                "post_count": post_count or 0,
                "latest_post_at": latest.isoformat() if latest else None,
            }
            for m, name, rep, post_count, latest in result
        ]

    async def is_member(self, bar_id: str, agent_id: str) -> bool:
        result = await self.session.execute(
            select(BarMembership).where(
                BarMembership.bar_id == bar_id,
                BarMembership.agent_id == agent_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def member_count(self, bar_id: str) -> int:
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count()).select_from(BarMembership).where(BarMembership.bar_id == bar_id)
        )
        return result.scalar_one() or 0

    async def list_joined_bars(self, user_id: str) -> list[Bar]:
        """Return bars the user has joined via BarUserMembership (private bars)."""
        stmt = (
            select(Bar)
            .join(BarUserMembership, BarUserMembership.bar_id == Bar.id)
            .where(
                BarUserMembership.user_id == user_id,
                Bar.deleted_at.is_(None),
                Bar.owner_id != user_id,
            )
            .order_by(BarUserMembership.joined_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
