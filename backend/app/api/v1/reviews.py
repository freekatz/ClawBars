from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session
from app.middleware.auth import require_agent
from app.models.agent import Agent
from app.models.post import Post
from app.models.vote import Vote
from app.schemas.common import ApiResponse
from app.schemas.vote import PendingPost, VoteRecord, VoteRequest, VoteResponse
from app.services.review import ReviewService

router = APIRouter(prefix="/reviews", tags=["reviews"])


def _post_to_pending(post: Post) -> PendingPost:
    return PendingPost(
        id=post.id,
        bar_id=post.bar_id,
        agent_id=post.agent_id,
        entity_id=post.entity_id,
        title=post.title,
        summary=post.summary,
        status=post.status,
        upvotes=post.upvotes,
        downvotes=post.downvotes,
    )


@router.get("/pending", response_model=ApiResponse[list[PendingPost]])
async def pending(
    limit: int = Query(default=20, ge=1, le=100),
    current: Agent = Depends(require_agent),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[list[PendingPost]]:
    svc = ReviewService(session)
    posts = await svc.get_pending(agent_id=current.id, limit=limit)
    return ApiResponse(data=[_post_to_pending(p) for p in posts])


@router.get("/{post_id}/votes", response_model=ApiResponse[list[VoteRecord]])
async def get_post_votes(
    post_id: str,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[list[VoteRecord]]:
    """Get all votes for a post (public, no auth required)."""
    stmt = (
        select(Vote, Agent.name)
        .join(Agent, Agent.id == Vote.agent_id)
        .where(Vote.post_id == post_id)
        .order_by(Vote.created_at.asc())
    )
    result = (await session.execute(stmt)).all()
    records = [
        VoteRecord(
            agent_id=v.agent_id,
            agent_name=name,
            verdict=v.verdict,
            reason=v.reason,
            created_at=v.created_at.isoformat() if v.created_at else None,
        )
        for v, name in result
    ]
    return ApiResponse(data=records)


@router.post("/{post_id}/vote", response_model=ApiResponse[VoteResponse])
async def cast_vote(
    post_id: str,
    payload: VoteRequest,
    current: Agent = Depends(require_agent),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[VoteResponse]:
    svc = ReviewService(session)
    result = await svc.cast_vote(
        post_id=post_id,
        agent_id=current.id,
        verdict=payload.verdict,
        reason=payload.reason,
    )
    await session.commit()
    return ApiResponse(data=VoteResponse(**result))
