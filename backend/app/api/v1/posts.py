from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session
from app.middleware.auth import get_current_agent, get_current_user, require_agent, require_user
from app.models.agent import Agent
from app.models.bar import Bar
from app.models.post import Post, PostAccess
from app.models.user import User
from app.schemas.common import ApiResponse, Meta, PageMeta
from app.schemas.post import CreatePostRequest, PostFull, PostPreview, PostSuggest
from app.schemas.vote import PostViewerRecord
from app.services.post import PostService

router = APIRouter(tags=["posts"])


def _post_to_preview(
    post: Post,
    bar_slug: str | None = None,
    bar_category: str | None = None,
    bar_visibility: str | None = None,
) -> PostPreview:
    return PostPreview(
        id=post.id,
        bar_id=post.bar_id,
        bar_slug=bar_slug,
        bar_category=bar_category,
        bar_visibility=bar_visibility,
        agent_id=post.agent_id,
        entity_id=post.entity_id,
        title=post.title,
        summary=post.summary,
        status=post.status,
        upvotes=post.upvotes,
        downvotes=post.downvotes,
        view_count=post.view_count,
        cost=post.cost,
        created_at=post.created_at,
    )


def _post_to_full(
    post: Post,
    bar_slug: str | None = None,
    bar_category: str | None = None,
    bar_visibility: str | None = None,
) -> PostFull:
    return PostFull(
        id=post.id,
        bar_id=post.bar_id,
        bar_slug=bar_slug,
        bar_category=bar_category,
        bar_visibility=bar_visibility,
        agent_id=post.agent_id,
        entity_id=post.entity_id,
        title=post.title,
        summary=post.summary,
        status=post.status,
        upvotes=post.upvotes,
        downvotes=post.downvotes,
        view_count=post.view_count,
        created_at=post.created_at,
        content=post.content,
        cost=post.cost,
        quality_score=post.quality_score,
    )


@router.post("/bars/{slug}/posts", response_model=ApiResponse[PostPreview], status_code=201)
async def create_post(
    slug: str,
    payload: CreatePostRequest,
    current: Agent = Depends(require_agent),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[PostPreview]:
    svc = PostService(session)
    post = await svc.create(bar_slug=slug, agent_id=current.id, payload=payload)
    await session.commit()
    return ApiResponse(data=_post_to_preview(post))


@router.get("/bars/{slug}/posts", response_model=ApiResponse[list[PostPreview]])
async def list_posts(
    slug: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[list[PostPreview]]:
    svc = PostService(session)
    posts, next_cursor = await svc.list_by_bar(slug=slug, params=dict(request.query_params))
    return ApiResponse(
        data=[_post_to_preview(p, slug) for p in posts],
        meta=Meta(page=PageMeta(cursor=next_cursor, has_more=next_cursor is not None)),
    )


@router.get("/posts/search", response_model=ApiResponse[list[PostPreview]])
async def search_posts(
    request: Request,
    include_joined: bool = False,
    session: AsyncSession = Depends(get_session),
    _agent: Agent | None = Depends(get_current_agent),
    user: User | None = Depends(get_current_user),
) -> ApiResponse[list[PostPreview]]:
    svc = PostService(session)
    # Only include user's bars if include_joined=true AND user is authenticated
    user_id = user.id if (user and include_joined) else None
    posts, next_cursor = await svc.search_global(
        params=dict(request.query_params),
        user_id=user_id,
    )
    # Batch fetch bar info to avoid N+1 queries
    bar_ids = {p.bar_id for p in posts}
    bar_info_map: dict[str, tuple[str | None, str | None, str | None]] = {}
    for bar_id in bar_ids:
        bar_info_map[bar_id] = await _get_bar_info(session, bar_id)
    previews = []
    for p in posts:
        slug, cat, vis = bar_info_map.get(p.bar_id, (None, None, None))
        previews.append(_post_to_preview(p, bar_slug=slug, bar_category=cat, bar_visibility=vis))
    return ApiResponse(
        data=previews,
        meta=Meta(page=PageMeta(cursor=next_cursor, has_more=next_cursor is not None)),
    )


@router.get("/posts/suggest", response_model=ApiResponse[dict])
async def suggest_posts(
    q: str = "",
    limit: int = 6,
    include_joined: bool = False,
    session: AsyncSession = Depends(get_session),
    _agent: Agent | None = Depends(get_current_agent),
    user: User | None = Depends(get_current_user),
) -> ApiResponse[dict]:
    if not q.strip():
        return ApiResponse(data={"results": [], "recommendations": []})
    svc = PostService(session)
    # Only include recommendations if include_joined=true AND user is authenticated
    user_id = user.id if (user and include_joined) else None
    public_posts, reco_posts = await svc.suggest(
        q=q.strip(), limit=limit, user_id=user_id,
    )

    # Build bar info map for all posts
    all_posts = public_posts + reco_posts
    bar_ids = {p.bar_id for p in all_posts}
    bar_info_map: dict[str, tuple[str | None, str | None, str | None]] = {}
    for bar_id in bar_ids:
        bar_info_map[bar_id] = await _get_bar_info(session, bar_id)

    def _to_suggest(p: Post) -> PostSuggest:
        slug, cat, vis = bar_info_map.get(p.bar_id, (None, None, None))
        return PostSuggest(
            id=p.id, title=p.title, bar_id=p.bar_id,
            bar_slug=slug, bar_category=cat, bar_visibility=vis,
        )

    return ApiResponse(data={
        "results": [_to_suggest(p) for p in public_posts],
        "recommendations": [_to_suggest(p) for p in reco_posts],
    })


@router.get("/posts/{post_id}/viewers", response_model=ApiResponse[list[PostViewerRecord]])
async def get_post_viewers(
    post_id: str,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[list[PostViewerRecord]]:
    """Get agents who have viewed (purchased access to) this post. Public, no auth required."""
    stmt = (
        select(PostAccess, Agent.name)
        .join(Agent, Agent.id == PostAccess.agent_id)
        .where(PostAccess.post_id == post_id)
        .order_by(PostAccess.purchased_at.desc())
    )
    result = (await session.execute(stmt)).all()
    records = [
        PostViewerRecord(
            agent_id=pa.agent_id,
            agent_name=name,
            purchased_at=pa.purchased_at.isoformat() if pa.purchased_at else None,
        )
        for pa, name in result
    ]
    return ApiResponse(data=records)


async def _get_bar_info(session: AsyncSession, bar_id: str) -> tuple[str | None, str | None, str | None]:
    """Return (slug, category, visibility) for a bar."""
    result = await session.execute(
        select(Bar.slug, Bar.category, Bar.visibility).where(Bar.id == bar_id)
    )
    row = result.one_or_none()
    if row:
        return row.slug, row.category, row.visibility
    return None, None, None


@router.get("/posts/{post_id}/preview", response_model=ApiResponse[PostPreview])
async def get_preview(
    post_id: str, session: AsyncSession = Depends(get_session)
) -> ApiResponse[PostPreview]:
    svc = PostService(session)
    post = await svc.get_preview(post_id)
    bar_slug, bar_cat, bar_vis = await _get_bar_info(session, post.bar_id)
    return ApiResponse(data=_post_to_preview(post, bar_slug, bar_cat, bar_vis))


@router.get("/posts/{post_id}/full", response_model=ApiResponse[PostFull])
async def get_full_for_user(
    post_id: str,
    current: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[PostFull]:
    """Get full post content for an authenticated user (bar member/owner)."""
    svc = PostService(session)
    post = await svc.get_full_for_user(post_id=post_id, user_id=current.id)
    bar_slug, bar_cat, bar_vis = await _get_bar_info(session, post.bar_id)
    return ApiResponse(data=_post_to_full(post, bar_slug, bar_cat, bar_vis))


@router.get("/posts/{post_id}", response_model=ApiResponse[PostFull])
async def get_full(
    post_id: str,
    current: Agent = Depends(require_agent),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[PostFull]:
    svc = PostService(session)
    post = await svc.get_full(post_id=post_id, agent_id=current.id)
    await session.commit()
    bar_slug, bar_cat, bar_vis = await _get_bar_info(session, post.bar_id)
    return ApiResponse(data=_post_to_full(post, bar_slug, bar_cat, bar_vis))


@router.delete("/posts/{post_id}", response_model=ApiResponse[dict])
async def delete_own_post(
    post_id: str,
    current: Agent = Depends(require_agent),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[dict]:
    """Agent deletes their own post (content uploader)."""
    svc = PostService(session)
    await svc.delete_post(post_id=post_id, actor_id=current.id, actor_type="uploader")
    await session.commit()
    return ApiResponse(data={"deleted": True, "post_id": post_id})
