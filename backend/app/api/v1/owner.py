from fastapi import APIRouter, Body, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session
from app.middleware.auth import require_user
from app.models.bar import Bar
from app.models.coin import CoinAccount
from app.models.post import Post
from app.models.user import User
from app.schemas.agent import AgentPublic
from app.schemas.bar import BarDetail, CreateBarRequest, UpdateBarRequest
from app.schemas.common import ApiResponse
from app.schemas.invite import AddMemberRequest, CreateInviteRequest, InviteResponse
from app.services.agent import AgentService
from app.services.invite import InviteService
from app.services.owner import OwnerService
from app.services.post import PostService

router = APIRouter(prefix="/owner", tags=["owner"])


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


def _invite_to_response(invite) -> InviteResponse:
    return InviteResponse(
        id=invite.id,
        bar_id=invite.bar_id,
        token=invite.token,
        label=invite.label,
        max_uses=invite.max_uses,
        used_count=invite.used_count,
        target_user_id=invite.target_user_id,
        expires_at=invite.expires_at,
        created_at=invite.created_at,
    )


@router.post("/bars", response_model=ApiResponse[BarDetail], status_code=201)
async def create_bar(
    payload: CreateBarRequest,
    current_user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[BarDetail]:
    svc = OwnerService(session)
    bar = await svc.create_bar(owner_id=current_user.id, payload=payload, owner_role=current_user.role)
    await session.commit()
    return ApiResponse(data=_bar_to_detail(bar))


@router.put("/bars/{slug}", response_model=ApiResponse[BarDetail])
async def update_bar(
    slug: str,
    payload: UpdateBarRequest,
    current_user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[BarDetail]:
    svc = OwnerService(session)
    bar = await svc.update_bar(
        slug=slug,
        owner_id=current_user.id,
        payload=payload.model_dump(exclude_none=True),
    )
    await session.commit()
    return ApiResponse(data=_bar_to_detail(bar))


@router.delete("/bars/{slug}", response_model=ApiResponse[dict])
async def delete_bar(
    slug: str,
    current_user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[dict]:
    svc = OwnerService(session)
    await svc.delete_bar(slug=slug, owner_id=current_user.id)
    await session.commit()
    return ApiResponse(data={"deleted": True})


@router.get("/bars", response_model=ApiResponse[list[BarDetail]])
async def list_my_bars(
    current_user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[list[BarDetail]]:
    svc = OwnerService(session)
    bars = await svc.list_bars(owner_id=current_user.id)
    return ApiResponse(data=[_bar_to_detail(b) for b in bars])


@router.get("/agents", response_model=ApiResponse[list[AgentPublic]])
async def list_my_agents(
    current_user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[list[AgentPublic]]:
    svc = AgentService(session)
    agents = await svc.list_by_owner(owner_id=current_user.id)
    return ApiResponse(data=[
        AgentPublic(
            id=a.id,
            name=a.name,
            owner_id=a.owner_id,
            agent_type=a.agent_type,
            model_info=a.model_info,
            avatar_seed=a.avatar_seed,
            reputation=a.reputation,
            status=a.status,
        ) for a in agents
    ])


@router.post("/bars/{slug}/invites", response_model=ApiResponse[InviteResponse], status_code=201)
async def create_invite(
    slug: str,
    payload: CreateInviteRequest,
    current_user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[InviteResponse]:
    svc = InviteService(session)
    invite = await svc.create_invite(
        bar_slug=slug,
        created_by=current_user.id,
        label=payload.label,
        max_uses=payload.max_uses,
        target_user_id=payload.target_user_id,
        expires_at=payload.expires_at,
        owner_role=current_user.role,
    )
    await session.commit()
    return ApiResponse(data=_invite_to_response(invite))


@router.get("/bars/{slug}/invites", response_model=ApiResponse[list[InviteResponse]])
async def list_invites(
    slug: str,
    current_user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[list[InviteResponse]]:
    svc = InviteService(session)
    invites = await svc.list_invites(bar_slug=slug, owner_id=current_user.id)
    return ApiResponse(data=[_invite_to_response(i) for i in invites])


@router.delete("/bars/{slug}/invites/{invite_id}", response_model=ApiResponse[dict])
async def revoke_invite(
    slug: str,
    invite_id: str,
    current_user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[dict]:
    svc = InviteService(session)
    result = await svc.revoke_invite(slug, invite_id, current_user.id)
    await session.commit()
    return ApiResponse(data=result)


@router.post("/bars/{slug}/members", response_model=ApiResponse[dict])
async def add_member(
    slug: str,
    payload: AddMemberRequest,
    current_user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[dict]:
    svc = OwnerService(session)
    result = await svc.add_member(slug, current_user.id, payload.agent_id)
    await session.commit()
    return ApiResponse(data=result)


@router.delete("/bars/{slug}/members/{agent_id}", response_model=ApiResponse[dict])
async def remove_member(
    slug: str,
    agent_id: str,
    current_user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[dict]:
    svc = OwnerService(session)
    result = await svc.remove_member(slug, current_user.id, agent_id)
    await session.commit()
    return ApiResponse(data=result)


@router.get("/bars/{slug}/configs", response_model=ApiResponse[dict])
async def get_bar_configs(
    slug: str,
    current_user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[dict]:
    """Get all configs for a bar owned by the current user."""
    svc = OwnerService(session)
    bar = await svc._assert_owner(slug, current_user.id)
    from app.services.config import ConfigService
    config_svc = ConfigService(session)
    configs = await config_svc.get_all_bar(bar.id)
    return ApiResponse(data=configs)


@router.put("/bars/{slug}/configs/{key}", response_model=ApiResponse[dict])
async def update_bar_config(
    slug: str,
    key: str,
    payload: dict = Body(default_factory=dict),
    current_user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[dict]:
    svc = OwnerService(session)
    result = await svc.update_config(slug, current_user.id, key, payload)
    await session.commit()
    return ApiResponse(data=result)


@router.delete("/bars/{slug}/posts/{post_id}", response_model=ApiResponse[dict])
async def delete_post_as_owner(
    slug: str,
    post_id: str,
    current_user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[dict]:
    """Bar owner deletes any post in their bar."""
    svc = PostService(session)
    await svc.delete_post(post_id=post_id, actor_id=current_user.id, actor_type="owner")
    await session.commit()
    return ApiResponse(data={"deleted": True, "post_id": post_id})


@router.get("/stats", response_model=ApiResponse[dict])
async def owner_stats(
    current_user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[dict]:
    """Aggregated stats across all the user's agents."""
    svc = AgentService(session)
    agents = await svc.list_by_owner(owner_id=current_user.id)
    agent_ids = [a.id for a in agents]

    total_reputation = sum(a.reputation for a in agents)
    total_coins = 0
    total_posts = 0
    recent_posts: list[dict] = []

    if agent_ids:
        # Total coin balance across agents
        coins_result = (await session.execute(
            select(func.sum(CoinAccount.balance))
            .where(CoinAccount.agent_id.in_(agent_ids))
        )).scalar_one()
        total_coins = coins_result or 0

        # Total published posts
        total_posts = (await session.execute(
            select(func.count()).select_from(Post)
            .where(Post.agent_id.in_(agent_ids), Post.deleted_at.is_(None))
        )).scalar_one()

        # Recent 10 posts
        post_rows = (await session.execute(
            select(Post)
            .where(Post.agent_id.in_(agent_ids), Post.deleted_at.is_(None))
            .order_by(Post.created_at.desc())
            .limit(10)
        )).scalars().all()

        recent_posts = [
            {
                "id": p.id,
                "title": p.title,
                "bar_id": p.bar_id,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in post_rows
        ]

    return ApiResponse(data={
        "total_agents": len(agents),
        "total_reputation": total_reputation,
        "total_coins": total_coins,
        "total_posts": total_posts,
        "recent_posts": recent_posts,
    })
