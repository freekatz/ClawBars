from __future__ import annotations

import secrets
from datetime import datetime, timezone

from nanoid import generate
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.invite import BarInvite


class InviteService:
    # TODO: Implement invite limits based on payment tier.
    # Map of user role/tier → max active invite links per bar.
    # Currently not enforced; set to None (unlimited) for all tiers.
    INVITE_LIMITS_PER_BAR: dict[str, int | None] = {
        "premium": None,   # e.g. change to 5 for basic premium
        "admin": None,     # unlimited
    }

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _check_invite_limit(self, bar_id: str, owner_role: str) -> None:
        """Placeholder: enforce per-bar invite link limit based on owner's payment tier."""
        limit = self.INVITE_LIMITS_PER_BAR.get(owner_role)
        if limit is None:
            return  # No limit for this tier
        count_result = await self.session.execute(
            select(func.count()).select_from(BarInvite).where(BarInvite.bar_id == bar_id)
        )
        current_count = count_result.scalar_one()
        if current_count >= limit:
            raise AppError(
                code=40303,
                message=f"Invite link limit reached ({limit}) for your current plan",
                http_status=403,
            )

    async def create_invite(
        self,
        bar_slug: str,
        created_by: str,
        label: str | None = None,
        max_uses: int | None = None,
        target_user_id: str | None = None,
        expires_at: datetime | None = None,
        owner_role: str = "premium",
    ) -> BarInvite:
        from app.services.bar import BarService
        bar_svc = BarService(self.session)
        bar = await bar_svc.get_by_slug(bar_slug)

        # Verify caller owns the bar
        from app.models.bar import Bar
        result = await self.session.execute(
            select(Bar).where(Bar.id == bar.id, Bar.owner_id == created_by)
        )
        owned = result.scalar_one_or_none()
        if not owned:
            raise AppError(code=40302, message="Not the bar owner", http_status=403)

        # Check invite limit based on payment tier
        await self._check_invite_limit(bar.id, owner_role)

        token = f"clawbars_inv_{secrets.token_urlsafe(16)}"
        invite = BarInvite(
            id=generate(size=21),
            bar_id=bar.id,
            created_by=created_by,
            token=token,
            label=label,
            max_uses=max_uses,
            target_user_id=target_user_id,
            expires_at=expires_at,
        )
        self.session.add(invite)
        await self.session.flush()
        return invite

    async def list_invites(self, bar_slug: str, owner_id: str) -> list[BarInvite]:
        from app.services.bar import BarService
        bar_svc = BarService(self.session)
        bar = await bar_svc.get_by_slug(bar_slug)

        from app.models.bar import Bar
        result = await self.session.execute(
            select(Bar).where(Bar.id == bar.id, Bar.owner_id == owner_id)
        )
        if not result.scalar_one_or_none():
            raise AppError(code=40302, message="Not the bar owner", http_status=403)

        result = await self.session.execute(
            select(BarInvite).where(BarInvite.bar_id == bar.id)
            .order_by(BarInvite.created_at.desc())
        )
        return list(result.scalars().all())

    async def revoke_invite(self, bar_slug: str, invite_id: str, owner_id: str) -> dict:
        from app.services.bar import BarService
        bar_svc = BarService(self.session)
        bar = await bar_svc.get_by_slug(bar_slug)

        from app.models.bar import Bar
        result = await self.session.execute(
            select(Bar).where(Bar.id == bar.id, Bar.owner_id == owner_id)
        )
        if not result.scalar_one_or_none():
            raise AppError(code=40302, message="Not the bar owner", http_status=403)

        result = await self.session.execute(
            select(BarInvite).where(
                BarInvite.id == invite_id,
                BarInvite.bar_id == bar.id,
            )
        )
        invite = result.scalar_one_or_none()
        if not invite:
            raise AppError(code=40401, message="Invite not found", http_status=404)

        await self.session.delete(invite)
        await self.session.flush()
        return {"id": invite_id, "revoked": True}

    async def validate_and_consume(self, bar_id: str, token: str, user_id: str | None = None) -> BarInvite:
        """Validate token and atomically increment usage count."""
        result = await self.session.execute(
            select(BarInvite).where(BarInvite.token == token, BarInvite.bar_id == bar_id)
        )
        invite = result.scalar_one_or_none()
        if not invite:
            raise AppError(code=40401, message="Invalid invite token", http_status=404)

        now = datetime.now(timezone.utc)
        expires = invite.expires_at
        if expires and expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires and expires < now:
            raise AppError(code=40002, message="Invite token has expired", http_status=400)

        if invite.target_user_id and user_id and invite.target_user_id != user_id:
            raise AppError(code=40302, message="Invite token is not for this user", http_status=403)

        # Atomic increment with max_uses check to prevent race conditions
        stmt = (
            update(BarInvite)
            .where(BarInvite.id == invite.id)
        )
        if invite.max_uses is not None:
            stmt = stmt.where(BarInvite.used_count < invite.max_uses)
        stmt = stmt.values(used_count=BarInvite.used_count + 1).returning(BarInvite.used_count)

        result = await self.session.execute(stmt)
        row = result.one_or_none()
        if row is None:
            raise AppError(code=40002, message="Invite token has reached max uses", http_status=400)

        invite.used_count = row[0]
        return invite
