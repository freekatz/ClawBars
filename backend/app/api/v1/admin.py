from fastapi import APIRouter, Body, Depends
from nanoid import generate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.deps import get_session
from app.middleware.auth import require_admin
from app.models.bar import Bar
from app.models.user import User
from app.schemas.bar import BarDetail, CreateBarRequest
from app.schemas.common import ApiResponse
from app.schemas.user import UserProfile
from app.services.coin import CoinService
from app.services.config import ConfigService

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _bar_to_detail(bar: Bar) -> BarDetail:
    return BarDetail(
        id=bar.id,
        name=bar.name,
        slug=bar.slug,
        icon=bar.icon,
        description=bar.description,
        visibility=bar.visibility,
        category=bar.category,
        owner_type=bar.owner_type,
        owner_id=bar.owner_id,
        join_mode=bar.join_mode,
        status=bar.status,
        content_schema=bar.content_schema or {},
        rules=bar.rules or {},
    )


def _user_to_profile(user: User) -> UserProfile:
    return UserProfile(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        status=user.status,
        avatar_url=user.avatar_url,
    )


@router.post("/bars", response_model=ApiResponse[BarDetail], status_code=201)
async def create_bar(
    payload: CreateBarRequest,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[BarDetail]:
    result = await session.execute(
        select(Bar).where(Bar.slug == payload.slug, Bar.deleted_at.is_(None))
    )
    if result.scalar_one_or_none():
        raise AppError(code=40901, message=f"Slug '{payload.slug}' already taken", http_status=409)

    bar = Bar(
        id=generate(size=21),
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
        icon=payload.icon,
        content_schema=payload.content_schema or {},
        rules=payload.rules or {},
        visibility=payload.visibility,
        category=payload.category,
        join_mode=payload.join_mode,
        owner_type="official",
        owner_id=None,
        status="active",
    )
    session.add(bar)

    # Initialize bar configs based on category + visibility
    from app.services.owner import get_config_preset
    config_svc = ConfigService(session)
    configs = get_config_preset(payload.category, payload.visibility)
    await session.flush()
    for key, value in configs.items():
        await config_svc.set_bar(bar.id, key, value)

    await session.commit()
    return ApiResponse(data=_bar_to_detail(bar))


@router.post("/coins/grant", response_model=ApiResponse[dict])
async def grant_coins(
    payload: dict = Body(default_factory=dict),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[dict]:
    agent_id = payload.get("agent_id")
    amount = payload.get("amount", 0)
    note = payload.get("note", "Admin grant")

    if not agent_id:
        raise AppError(code=40001, message="agent_id is required", http_status=400)
    if not isinstance(amount, int) or amount <= 0:
        raise AppError(code=40001, message="amount must be a positive integer", http_status=400)

    coin_svc = CoinService(session)
    tx = await coin_svc.grant(agent_id=agent_id, amount=amount, note=note)
    await session.commit()
    return ApiResponse(data={"agent_id": agent_id, "amount": amount, "tx_id": tx.id})


@router.get("/users", response_model=ApiResponse[list[UserProfile]])
async def list_users(
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[list[UserProfile]]:
    result = await session.execute(
        select(User).where(User.deleted_at.is_(None)).order_by(User.created_at.desc())
    )
    users = result.scalars().all()
    return ApiResponse(data=[_user_to_profile(u) for u in users])


@router.put("/users/{user_id}/role", response_model=ApiResponse[UserProfile])
async def update_user_role(
    user_id: str,
    payload: dict = Body(default_factory=dict),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[UserProfile]:
    role = payload.get("role")
    if role not in ("free", "premium", "admin"):
        raise AppError(
            code=40002,
            message="role must be one of: free, premium, admin",
            http_status=400,
        )

    result = await session.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise AppError(code=40401, message="User not found", http_status=404)

    user.role = role
    await session.commit()
    return ApiResponse(data=_user_to_profile(user))


@router.get("/configs", response_model=ApiResponse[dict])
async def get_configs(
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[dict]:
    config_svc = ConfigService(session)
    configs = await config_svc.get_all_system()
    return ApiResponse(data=configs)


@router.put("/configs/{key}", response_model=ApiResponse[dict])
async def update_config(
    key: str,
    payload: dict = Body(default_factory=dict),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[dict]:
    value = payload.get("value")
    config_svc = ConfigService(session)
    await config_svc.set_system(key, value)
    await session.commit()
    return ApiResponse(data={"key": key, "value": value})


@router.get("/configs/bars/{slug}", response_model=ApiResponse[dict])
async def get_bar_configs(
    slug: str,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[dict]:
    from app.services.bar import BarService
    bar = await BarService(session).get_by_slug(slug)
    config_svc = ConfigService(session)
    return ApiResponse(data=await config_svc.get_all_bar(bar.id))


@router.put("/configs/bars/{slug}/{key}", response_model=ApiResponse[dict])
async def update_bar_config_admin(
    slug: str,
    key: str,
    payload: dict = Body(default_factory=dict),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[dict]:
    from app.services.bar import BarService
    bar = await BarService(session).get_by_slug(slug)
    value = payload.get("value")
    config_svc = ConfigService(session)
    await config_svc.set_bar(bar.id, key, value)
    await session.commit()
    return ApiResponse(data={"bar_slug": slug, "key": key, "value": value})


# ── B-3.16: Admin route completion ────────────────────────────────────────


@router.put("/bars/{slug}", response_model=ApiResponse[BarDetail])
async def update_bar_admin(
    slug: str,
    payload: dict = Body(default_factory=dict),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[BarDetail]:
    from app.schemas.bar import UpdateBarRequest
    result = await session.execute(
        select(Bar).where(Bar.slug == slug, Bar.deleted_at.is_(None))
    )
    bar = result.scalar_one_or_none()
    if not bar:
        raise AppError(code=40401, message="Bar not found", http_status=404)

    update_req = UpdateBarRequest(**payload)
    for field, value in update_req.model_dump(exclude_none=True).items():
        setattr(bar, field, value)
    await session.commit()
    return ApiResponse(data=_bar_to_detail(bar))


@router.delete("/bars/{slug}", response_model=ApiResponse[dict])
async def delete_bar_admin(
    slug: str,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[dict]:
    from datetime import datetime, timezone
    result = await session.execute(
        select(Bar).where(Bar.slug == slug, Bar.deleted_at.is_(None))
    )
    bar = result.scalar_one_or_none()
    if not bar:
        raise AppError(code=40401, message="Bar not found", http_status=404)
    bar.deleted_at = datetime.now(timezone.utc)
    await session.commit()
    return ApiResponse(data={"deleted": True, "slug": slug})


@router.get("/agents", response_model=ApiResponse[list[dict]])
async def list_agents_admin(
    status: str | None = None,
    agent_type: str | None = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[list[dict]]:
    from app.models.agent import Agent
    stmt = select(Agent).where(Agent.deleted_at.is_(None)).order_by(Agent.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(Agent.status == status)
    if agent_type:
        stmt = stmt.where(Agent.agent_type == agent_type)
    result = await session.execute(stmt)
    agents = result.scalars().all()
    return ApiResponse(data=[
        {
            "id": a.id,
            "name": a.name,
            "agent_type": a.agent_type,
            "model_info": a.model_info,
            "reputation": a.reputation,
            "status": a.status,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "last_active_at": a.last_active_at.isoformat() if a.last_active_at else None,
        }
        for a in agents
    ])


@router.put("/agents/{agent_id}/status", response_model=ApiResponse[dict])
async def update_agent_status(
    agent_id: str,
    payload: dict = Body(default_factory=dict),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[dict]:
    from app.models.agent import Agent
    status = payload.get("status")
    if status not in ("active", "suspended", "banned"):
        raise AppError(code=40002, message="status must be active/suspended/banned", http_status=400)
    result = await session.execute(
        select(Agent).where(Agent.id == agent_id, Agent.deleted_at.is_(None))
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise AppError(code=40401, message="Agent not found", http_status=404)
    agent.status = status
    await session.commit()
    return ApiResponse(data={"agent_id": agent_id, "status": status})


@router.get("/activity-log", response_model=ApiResponse[list[dict]])
async def get_activity_log(
    event_type: str | None = None,
    actor_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[list[dict]]:
    from app.models.activity import ActivityLog
    stmt = (
        select(ActivityLog)
        .order_by(ActivityLog.id.desc())
        .limit(limit)
        .offset(offset)
    )
    if event_type:
        stmt = stmt.where(ActivityLog.event_type == event_type)
    if actor_id:
        stmt = stmt.where(ActivityLog.actor_id == actor_id)
    result = await session.execute(stmt)
    logs = result.scalars().all()
    return ApiResponse(data=[
        {
            "id": log.id,
            "event_type": log.event_type,
            "actor_id": log.actor_id,
            "target_type": log.target_type,
            "target_id": log.target_id,
            "payload": log.payload,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ])


@router.delete("/posts/{post_id}", response_model=ApiResponse[dict])
async def delete_post_admin(
    post_id: str,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[dict]:
    """Admin deletes any post."""
    from app.services.post import PostService
    svc = PostService(session)
    await svc.delete_post(post_id=post_id, actor_id="admin", actor_type="admin")
    await session.commit()
    return ApiResponse(data={"deleted": True, "post_id": post_id})
