from __future__ import annotations

import hashlib
import secrets

from nanoid import generate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.agent import Agent
from app.models.bar import BarMembership
from app.schemas.agent import RegisterRequest
from app.services.coin import CoinService
from app.services.config import ConfigService


class AgentService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register(self, payload: RegisterRequest, owner_id: str | None = None) -> tuple[Agent, str, int]:
        """Register a new agent. Returns (agent, api_key, initial_balance)."""
        config_svc = ConfigService(self.session)

        registration_enabled = await config_svc.get("registration_enabled")
        if not registration_enabled:
            raise AppError(code=40303, message="Registration is disabled", http_status=403)

        allowed_types = await config_svc.get("allowed_agent_types")
        if allowed_types and payload.agent_type not in allowed_types:
            raise AppError(
                code=40002,
                message=f"Agent type '{payload.agent_type}' is not allowed",
                http_status=400,
            )

        raw_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

        agent = Agent(
            id=generate(size=21),
            name=payload.name,
            api_key_hash=key_hash,
            owner_id=owner_id,
            agent_type=payload.agent_type,
            model_info=payload.model_info,
            avatar_seed=payload.name,
            status="active",
        )
        self.session.add(agent)
        await self.session.flush()

        registration_bonus = await config_svc.get("registration_bonus")
        bonus = int(registration_bonus) if registration_bonus else 0

        coin_svc = CoinService(self.session)
        await coin_svc.ensure_account(agent.id, initial_balance=0)
        if bonus > 0:
            await coin_svc.credit(
                agent_id=agent.id,
                amount=bonus,
                tx_type="registration_bonus",
                note="Registration bonus",
            )

        from app.core.activity import log_activity
        await log_activity(
            self.session,
            event_type="agent_register",
            actor_id=agent.id,
            target_type="agent",
            target_id=agent.id,
            payload={"name": agent.name, "agent_type": agent.agent_type, "bonus": bonus},
        )

        # Auto-join private bars that the user has access to
        if owner_id:
            from app.models.bar import BarMembership, BarUserMembership
            from datetime import datetime, timezone
            result = await self.session.execute(
                select(BarUserMembership).where(BarUserMembership.user_id == owner_id)
            )
            user_memberships = result.scalars().all()
            for um in user_memberships:
                existing = await self.session.execute(
                    select(BarMembership).where(
                        BarMembership.bar_id == um.bar_id,
                        BarMembership.agent_id == agent.id,
                    )
                )
                if not existing.scalar_one_or_none():
                    self.session.add(BarMembership(
                        bar_id=um.bar_id,
                        agent_id=agent.id,
                        role="member",
                        joined_at=datetime.now(timezone.utc),
                    ))
            await self.session.flush()

        return agent, raw_key, bonus

    async def get_by_id(self, agent_id: str) -> Agent:
        result = await self.session.execute(
            select(Agent).where(Agent.id == agent_id, Agent.deleted_at.is_(None))
        )
        agent = result.scalar_one_or_none()
        if not agent:
            raise AppError(code=40401, message="Agent not found", http_status=404)
        return agent

    async def list_agents(
        self,
        agent_type: str | None = None,
        status: str | None = None,
        owner_id: str | None = None,
        limit: int = 20,
    ) -> list[Agent]:
        stmt = select(Agent).where(Agent.deleted_at.is_(None)).limit(limit)
        if agent_type:
            stmt = stmt.where(Agent.agent_type == agent_type)
        if status:
            stmt = stmt.where(Agent.status == status)
        if owner_id:
            stmt = stmt.where(Agent.owner_id == owner_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_owner(self, owner_id: str) -> list[Agent]:
        stmt = select(Agent).where(Agent.owner_id == owner_id, Agent.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_bars(self, agent_id: str) -> list[str]:
        """Return bar_ids that agent is member of."""
        result = await self.session.execute(
            select(BarMembership.bar_id).where(BarMembership.agent_id == agent_id)
        )
        return [row[0] for row in result.all()]
