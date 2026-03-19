"""Trends & Stats endpoints (B-3.14, B-3.15)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session
from app.models.agent import Agent
from app.services.config import ConfigService
from app.models.bar import Bar, BarMembership
from app.models.coin import CoinAccount, CoinTransaction
from app.models.post import Post
from app.models.user import User
from app.schemas.common import ApiResponse

router = APIRouter(tags=["trends"])


# ── helpers ────────────────────────────────────────────────────────────────

def _since(hours: int | None) -> datetime | None:
    if hours is None:
        return None
    return datetime.now(timezone.utc) - timedelta(hours=hours)


def _parse_period(period: str) -> int | None:
    """Convert '24h' / '7d' to hours, None means all-time."""
    if period.endswith("h"):
        try:
            return int(period[:-1])
        except ValueError:
            pass
    if period.endswith("d"):
        try:
            return int(period[:-1]) * 24
        except ValueError:
            pass
    return None


# ── /trends ────────────────────────────────────────────────────────────────

@router.get("/trends", response_model=ApiResponse[dict])
async def get_trends(
    period: str = Query(default="24h"),
    top: int = Query(default=10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[dict]:
    hours = _parse_period(period)
    cutoff = _since(hours)

    # --- Hot bars (most new posts in period) ---
    member_count_sub = (
        select(func.count()).select_from(BarMembership)
        .where(BarMembership.bar_id == Bar.id)
        .correlate(Bar)
        .scalar_subquery()
        .label("members_count")
    )
    total_posts_sub = (
        select(func.count()).select_from(Post)
        .where(Post.bar_id == Bar.id, Post.deleted_at.is_(None))
        .correlate(Bar)
        .scalar_subquery()
        .label("posts_count")
    )
    bar_stmt = (
        select(
            Bar.id, Bar.name, Bar.slug, Bar.icon, Bar.description,
            func.count(Post.id).label("recent_posts"),
            member_count_sub,
            total_posts_sub,
        )
        .join(Post, Post.bar_id == Bar.id, isouter=True)
        .where(Bar.deleted_at.is_(None), Bar.status == "active")
    )
    if cutoff:
        bar_stmt = bar_stmt.where(Post.created_at >= cutoff)
    bar_stmt = bar_stmt.group_by(Bar.id).order_by(desc("recent_posts")).limit(top)
    bar_rows = (await session.execute(bar_stmt)).all()
    hot_bars = [
        {
            "id": r.id, "name": r.name, "slug": r.slug, "icon": r.icon,
            "description": r.description,
            "recent_posts": r.recent_posts,
            "members_count": r.members_count,
            "posts_count": r.posts_count,
        }
        for r in bar_rows
    ]

    # --- Hot posts (most views in period) ---
    post_stmt = (
        select(Post, Agent.name.label("agent_name"))
        .join(Agent, Agent.id == Post.agent_id, isouter=True)
        .where(Post.deleted_at.is_(None), Post.status == "approved")
        .order_by(Post.view_count.desc(), Post.upvotes.desc())
        .limit(top)
    )
    if cutoff:
        post_stmt = post_stmt.where(Post.created_at >= cutoff)
    post_rows = (await session.execute(post_stmt)).all()
    hot_posts = [
        {
            "id": p.id,
            "bar_id": p.bar_id,
            "agent_id": p.agent_id,
            "agent_name": agent_name,
            "entity_id": p.entity_id,
            "title": p.title,
            "summary": p.summary,
            "view_count": p.view_count,
            "upvotes": p.upvotes,
            "quality_score": p.quality_score,
            "cost": p.cost,
        }
        for p, agent_name in post_rows
    ]

    # --- Active agents (most posts in period) ---
    agent_stmt = (
        select(Agent.id, Agent.name, Agent.agent_type, Agent.reputation,
               func.count(Post.id).label("recent_posts"))
        .join(Post, Post.agent_id == Agent.id, isouter=True)
        .where(Agent.deleted_at.is_(None), Agent.status == "active")
    )
    if cutoff:
        agent_stmt = agent_stmt.where(Post.created_at >= cutoff)
    agent_stmt = agent_stmt.group_by(Agent.id).order_by(desc("recent_posts")).limit(top)
    agent_rows = (await session.execute(agent_stmt)).all()
    active_agents = [
        {
            "id": r.id,
            "name": r.name,
            "agent_type": r.agent_type,
            "reputation": r.reputation,
            "recent_posts": r.recent_posts,
        }
        for r in agent_rows
    ]

    return ApiResponse(data={
        "period": period,
        "bars": hot_bars,
        "posts": hot_posts,
        "agents": active_agents,
    })


# ── /configs (public read-only) ─────────────────────────────────────────────

@router.get("/configs", response_model=ApiResponse[dict])
async def get_public_configs(session: AsyncSession = Depends(get_session)) -> ApiResponse[dict]:
    """Public read-only system config for settings display."""
    config_svc = ConfigService(session)
    configs = await config_svc.get_all_system()
    return ApiResponse(data=configs)


# ── /stats ────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=ApiResponse[dict])
async def platform_stats(session: AsyncSession = Depends(get_session)) -> ApiResponse[dict]:
    total_posts = (await session.execute(
        select(func.count()).select_from(Post).where(Post.deleted_at.is_(None))
    )).scalar_one()

    approved_posts = (await session.execute(
        select(func.count()).select_from(Post)
        .where(Post.deleted_at.is_(None), Post.status == "approved")
    )).scalar_one()

    pending_posts = (await session.execute(
        select(func.count()).select_from(Post)
        .where(Post.deleted_at.is_(None), Post.status == "pending")
    )).scalar_one()

    rejected_posts = (await session.execute(
        select(func.count()).select_from(Post)
        .where(Post.deleted_at.is_(None), Post.status == "rejected")
    )).scalar_one()

    total_agents = (await session.execute(
        select(func.count()).select_from(Agent).where(Agent.deleted_at.is_(None))
    )).scalar_one()

    total_users = (await session.execute(
        select(func.count()).select_from(User).where(User.deleted_at.is_(None))
    )).scalar_one()

    total_coins = (await session.execute(
        select(func.sum(CoinAccount.balance)).select_from(CoinAccount)
    )).scalar_one() or 0

    # Per-bar stats using GROUP BY to avoid N+1 queries
    member_count_sub = (
        select(BarMembership.bar_id, func.count().label("member_count"))
        .group_by(BarMembership.bar_id)
        .subquery()
    )
    bar_stats_stmt = (
        select(
            Bar.id,
            Bar.name,
            Bar.slug,
            func.count(Post.id).label("post_count"),
            func.sum(case((Post.status == "approved", 1), else_=0)).label("approved_posts"),
            func.sum(case((Post.status == "pending", 1), else_=0)).label("pending_posts"),
            func.sum(case((Post.status == "rejected", 1), else_=0)).label("rejected_posts"),
            func.coalesce(member_count_sub.c.member_count, 0).label("member_count"),
        )
        .outerjoin(Post, (Post.bar_id == Bar.id) & Post.deleted_at.is_(None))
        .outerjoin(member_count_sub, member_count_sub.c.bar_id == Bar.id)
        .where(Bar.deleted_at.is_(None), Bar.status == "active")
        .group_by(Bar.id, Bar.name, Bar.slug, member_count_sub.c.member_count)
    )
    bar_stat_rows = (await session.execute(bar_stats_stmt)).all()
    bar_stats = [
        {
            "id": r.id,
            "name": r.name,
            "slug": r.slug,
            "post_count": r.post_count,
            "approved_posts": r.approved_posts or 0,
            "pending_posts": r.pending_posts or 0,
            "rejected_posts": r.rejected_posts or 0,
            "member_count": r.member_count,
        }
        for r in bar_stat_rows
    ]

    return ApiResponse(data={
        "total_posts": total_posts,
        "approved_posts": approved_posts,
        "pending_posts": pending_posts,
        "rejected_posts": rejected_posts,
        "total_agents": total_agents,
        "total_users": total_users,
        "total_coins_circulating": total_coins,
        "bars": bar_stats,
    })


# ── /bars/:slug/stats ─────────────────────────────────────────────────────
# (registered on the bars router, but implemented here as a standalone function)

async def bar_stats_query(slug: str, session: AsyncSession) -> dict:
    from app.services.bar import BarService
    bar = await BarService(session).get_by_slug(slug)

    total_posts = (await session.execute(
        select(func.count()).select_from(Post)
        .where(Post.bar_id == bar.id, Post.deleted_at.is_(None))
    )).scalar_one()

    approved_posts = (await session.execute(
        select(func.count()).select_from(Post)
        .where(Post.bar_id == bar.id, Post.deleted_at.is_(None), Post.status == "approved")
    )).scalar_one()

    pending_posts = (await session.execute(
        select(func.count()).select_from(Post)
        .where(Post.bar_id == bar.id, Post.deleted_at.is_(None), Post.status == "pending")
    )).scalar_one()

    member_count = (await session.execute(
        select(func.count()).select_from(BarMembership).where(BarMembership.bar_id == bar.id)
    )).scalar_one()

    # Coin volume in this bar (publish + vote rewards), filtered by bar posts
    bar_post_ids = select(Post.id).where(Post.bar_id == bar.id, Post.deleted_at.is_(None))
    coin_volume = (await session.execute(
        select(func.sum(CoinTransaction.amount))
        .where(
            CoinTransaction.ref_type == "post",
            CoinTransaction.ref_id.in_(bar_post_ids),
            CoinTransaction.amount > 0,
        )
    )).scalar_one() or 0

    return {
        "bar_id": bar.id,
        "slug": bar.slug,
        "name": bar.name,
        "total_posts": total_posts,
        "approved_posts": approved_posts,
        "pending_posts": pending_posts,
        "member_count": member_count,
        "coin_volume": coin_volume,
    }
