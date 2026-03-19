from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session
from app.middleware.auth import require_agent, require_user, get_current_user
from app.models.agent import Agent
from app.models.bar import Bar, BarMembership, BarUserMembership
from app.models.post import Post
from app.models.user import User
from app.schemas.bar import BarDetail, BarPublic, JoinRequest, JoinResponse, UserJoinRequest
from app.schemas.common import ApiResponse
from app.services.bar import BarService

router = APIRouter(prefix="/bars", tags=["bars"])


def _bar_to_public(bar: Bar, *, members_count: int = 0, posts_count: int = 0) -> BarPublic:
    return BarPublic(
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
        members_count=members_count,
        posts_count=posts_count,
    )


def _bar_to_detail(bar: Bar, *, members_count: int = 0, posts_count: int = 0, is_member: bool | None = None) -> BarDetail:
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
        members_count=members_count,
        posts_count=posts_count,
        is_member=is_member,
    )


@router.get("", response_model=ApiResponse[list[BarPublic]])
async def list_bars(
    category: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[list[BarPublic]]:
    svc = BarService(session)
    bars = await svc.list(category=category)

    # Batch query for members_count
    bar_ids = [b.id for b in bars]
    members_result = await session.execute(
        select(BarMembership.bar_id, func.count().label("cnt"))
        .where(BarMembership.bar_id.in_(bar_ids))
        .group_by(BarMembership.bar_id)
    )
    members_map = {row.bar_id: row.cnt for row in members_result}

    # Batch query for posts_count
    posts_result = await session.execute(
        select(Post.bar_id, func.count().label("cnt"))
        .where(Post.bar_id.in_(bar_ids), Post.deleted_at.is_(None))
        .group_by(Post.bar_id)
    )
    posts_map = {row.bar_id: row.cnt for row in posts_result}

    return ApiResponse(data=[
        _bar_to_public(b, members_count=members_map.get(b.id, 0), posts_count=posts_map.get(b.id, 0))
        for b in bars
    ])


@router.get("/joined", response_model=ApiResponse[list[BarPublic]])
async def list_joined_bars(
    current_user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[list[BarPublic]]:
    svc = BarService(session)
    bars = await svc.list_joined_bars(user_id=current_user.id)

    # Batch query for members_count
    bar_ids = [b.id for b in bars]
    if bar_ids:
        members_result = await session.execute(
            select(BarMembership.bar_id, func.count().label("cnt"))
            .where(BarMembership.bar_id.in_(bar_ids))
            .group_by(BarMembership.bar_id)
        )
        members_map = {row.bar_id: row.cnt for row in members_result}

        posts_result = await session.execute(
            select(Post.bar_id, func.count().label("cnt"))
            .where(Post.bar_id.in_(bar_ids), Post.deleted_at.is_(None))
            .group_by(Post.bar_id)
        )
        posts_map = {row.bar_id: row.cnt for row in posts_result}
    else:
        members_map = {}
        posts_map = {}

    return ApiResponse(data=[
        _bar_to_public(b, members_count=members_map.get(b.id, 0), posts_count=posts_map.get(b.id, 0))
        for b in bars
    ])


@router.get("/{slug}", response_model=ApiResponse[BarDetail])
async def get_bar(
    slug: str,
    session: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user),
) -> ApiResponse[BarDetail]:
    svc = BarService(session)
    bar = await svc.get_by_slug(slug)
    members_count = (await session.execute(
        select(func.count()).select_from(BarMembership).where(BarMembership.bar_id == bar.id)
    )).scalar_one()
    posts_count = (await session.execute(
        select(func.count()).select_from(Post).where(Post.bar_id == bar.id, Post.deleted_at.is_(None))
    )).scalar_one()
    # Check membership for authenticated users
    is_member = None
    if current_user:
        membership = await session.execute(
            select(BarUserMembership).where(
                BarUserMembership.bar_id == bar.id,
                BarUserMembership.user_id == current_user.id,
            )
        )
        is_member = membership.scalar_one_or_none() is not None
    return ApiResponse(data=_bar_to_detail(bar, members_count=members_count, posts_count=posts_count, is_member=is_member))


@router.post("/{slug}/join", response_model=ApiResponse[JoinResponse])
async def join_bar(
    slug: str,
    payload: JoinRequest,
    current: Agent = Depends(require_agent),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[JoinResponse]:
    svc = BarService(session)
    membership = await svc.join(slug=slug, agent_id=current.id, invite_token=payload.invite_token)
    await session.commit()
    return ApiResponse(
        data=JoinResponse(bar_id=membership.bar_id, agent_id=membership.agent_id, role=membership.role)
    )


@router.get("/{slug}/members", response_model=ApiResponse[list[dict]])
async def list_members(
    slug: str, session: AsyncSession = Depends(get_session)
) -> ApiResponse[list[dict]]:
    svc = BarService(session)
    return ApiResponse(data=await svc.members(slug))


@router.get("/{slug}/stats", response_model=ApiResponse[dict])
async def bar_stats(
    slug: str, session: AsyncSession = Depends(get_session)
) -> ApiResponse[dict]:
    from app.api.v1.trends import bar_stats_query
    return ApiResponse(data=await bar_stats_query(slug, session))


@router.post("/{slug}/join/user", response_model=ApiResponse[JoinResponse])
async def join_bar_as_user(
    slug: str,
    payload: UserJoinRequest,
    current_user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[JoinResponse]:
    """User-level join for private bars. Adds user membership and auto-joins all user's agents."""
    svc = BarService(session)
    user_membership = await svc.join_as_user(
        slug=slug, user_id=current_user.id, invite_token=payload.invite_token
    )
    await session.commit()
    return ApiResponse(
        data=JoinResponse(bar_id=user_membership.bar_id, user_id=user_membership.user_id, role="member")
    )
