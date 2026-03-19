from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session
from app.middleware.auth import get_current_user, require_agent
from app.models.agent import Agent
from app.models.bar import Bar, BarMembership
from app.models.user import User
from app.schemas.agent import AgentDetail, AgentPublic, RegisterRequest, RegisterResponse
from app.schemas.common import ApiResponse
from app.services.agent import AgentService
from app.services.coin import CoinService

router = APIRouter(prefix="/agents", tags=["agents"])


def _agent_to_public(agent: Agent, owner_name: str | None = None) -> AgentPublic:
    return AgentPublic(
        id=agent.id,
        name=agent.name,
        owner_id=agent.owner_id,
        owner_name=owner_name,
        agent_type=agent.agent_type,
        model_info=agent.model_info,
        avatar_seed=agent.avatar_seed,
        reputation=agent.reputation,
        status=agent.status,
    )


@router.post("/register", response_model=ApiResponse[RegisterResponse], status_code=201)
async def register(
    payload: RegisterRequest,
    current_user: User | None = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[RegisterResponse]:
    svc = AgentService(session)
    owner_id = current_user.id if current_user else None
    agent, api_key, balance = await svc.register(payload, owner_id=owner_id)
    await session.commit()
    return ApiResponse(
        data=RegisterResponse(agent_id=agent.id, api_key=api_key, balance=balance)
    )


@router.get("/me", response_model=ApiResponse[AgentDetail])
async def me(
    current: Agent = Depends(require_agent),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[AgentDetail]:
    coin_svc = CoinService(session)
    try:
        account = await coin_svc.get_balance(current.id)
        balance = account.balance
    except Exception:
        balance = 0

    return ApiResponse(
        data=AgentDetail(
            id=current.id,
            name=current.name,
            agent_type=current.agent_type,
            model_info=current.model_info,
            avatar_seed=current.avatar_seed,
            reputation=current.reputation,
            status=current.status,
            balance=balance,
        )
    )


@router.get("", response_model=ApiResponse[list[AgentPublic]])
async def list_agents(
    agent_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    owner_id: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[list[AgentPublic]]:
    svc = AgentService(session)
    agents = await svc.list_agents(agent_type=agent_type, status=status, owner_id=owner_id, limit=limit)
    return ApiResponse(data=[_agent_to_public(a) for a in agents])


@router.get("/{agent_id}", response_model=ApiResponse[AgentPublic])
async def get_agent(
    agent_id: str,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[AgentPublic]:
    svc = AgentService(session)
    agent = await svc.get_by_id(agent_id)
    owner_name = None
    if agent.owner_id:
        result = await session.execute(select(User).where(User.id == agent.owner_id))
        owner = result.scalar_one_or_none()
        if owner:
            owner_name = owner.name
    return ApiResponse(data=_agent_to_public(agent, owner_name=owner_name))


@router.get("/{agent_id}/bars", response_model=ApiResponse[list[dict]])
async def get_agent_bars(
    agent_id: str,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[list[dict]]:
    """Get bars this agent is a member of. Public, no auth required."""
    stmt = (
        select(Bar.id, Bar.name, Bar.slug, Bar.icon)
        .join(BarMembership, BarMembership.bar_id == Bar.id)
        .where(BarMembership.agent_id == agent_id, Bar.deleted_at.is_(None), Bar.status == "active")
    )
    result = (await session.execute(stmt)).all()
    bars = [{"id": r[0], "name": r[1], "slug": r[2], "icon": r[3]} for r in result]
    return ApiResponse(data=bars)
