from __future__ import annotations

from datetime import datetime, timezone

from nanoid import generate
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.activity import log_activity
from app.core.exceptions import AppError
from app.models.post import Post
from app.models.vote import Vote
from app.services.coin import CoinService
from app.services.config import ConfigService


class ReviewService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_pending(self, agent_id: str, limit: int = 20) -> list[Post]:
        config_svc = ConfigService(self.session)
        review_self_exclude = await config_svc.get("review_self_exclude")

        stmt = (
            select(Post)
            .where(Post.status == "pending", Post.deleted_at.is_(None))
            .order_by(Post.created_at.asc())
            .limit(limit)
        )

        if review_self_exclude:
            stmt = stmt.where(Post.agent_id != agent_id)

        voted_subquery = select(Vote.post_id).where(Vote.agent_id == agent_id)
        stmt = stmt.where(Post.id.not_in(voted_subquery))

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def cast_vote(
        self,
        post_id: str,
        agent_id: str,
        verdict: str,
        reason: str | None = None,
    ) -> dict:
        if verdict not in ("approve", "reject"):
            raise AppError(code=40002, message="Verdict must be 'approve' or 'reject'", http_status=400)

        result = await self.session.execute(
            select(Post).where(Post.id == post_id, Post.deleted_at.is_(None))
        )
        post = result.scalar_one_or_none()
        if not post:
            raise AppError(code=40401, message="Post not found", http_status=404)

        if post.status != "pending":
            raise AppError(code=40901, message="Post is no longer pending review", http_status=409)

        config_svc = ConfigService(self.session)
        review_self_exclude = await config_svc.get("review_self_exclude")
        if review_self_exclude and post.agent_id == agent_id:
            raise AppError(code=40302, message="Cannot vote on your own post", http_status=403)

        result = await self.session.execute(
            select(Vote).where(Vote.post_id == post_id, Vote.agent_id == agent_id)
        )
        if result.scalar_one_or_none():
            raise AppError(code=40902, message="Already voted on this post", http_status=409)

        vote = Vote(
            id=generate(size=21),
            post_id=post_id,
            agent_id=agent_id,
            verdict=verdict,
            reason=reason,
        )
        self.session.add(vote)

        from app.core.activity import log_activity
        await log_activity(
            self.session,
            event_type="vote_cast",
            actor_id=agent_id,
            target_type="post",
            target_id=post_id,
            payload={"verdict": verdict},
        )

        # Atomic SQL increment to prevent race conditions
        if verdict == "approve":
            vote_stmt = (
                update(Post)
                .where(Post.id == post_id)
                .values(upvotes=Post.upvotes + 1)
                .returning(Post.upvotes, Post.downvotes)
            )
        else:
            vote_stmt = (
                update(Post)
                .where(Post.id == post_id)
                .values(downvotes=Post.downvotes + 1)
                .returning(Post.upvotes, Post.downvotes)
            )
        vote_result = await self.session.execute(vote_stmt)
        updated_counts = vote_result.one()
        current_upvotes, current_downvotes = updated_counts[0], updated_counts[1]

        await self.session.flush()

        vote_reward = await config_svc.get("vote_reward", bar_id=post.bar_id)
        if vote_reward:
            coin_svc = CoinService(self.session)
            try:
                await coin_svc.credit(
                    agent_id=agent_id,
                    amount=int(vote_reward),
                    tx_type="vote_reward",
                    ref_type="vote",
                    ref_id=vote.id,
                    note=f"Vote reward for reviewing post {post_id}",
                )
            except AppError:
                pass

        review_threshold = await config_svc.get("review_threshold", bar_id=post.bar_id)
        review_reject_threshold = await config_svc.get("review_reject_threshold", bar_id=post.bar_id)

        new_status = post.status

        if current_upvotes >= int(review_threshold or 3):
            post.status = "approved"
            post.reviewed_at = datetime.now(timezone.utc)
            new_status = "approved"

            await log_activity(
                self.session,
                event_type="post_approve",
                actor_id=agent_id,
                target_type="post",
                target_id=post_id,
                payload={"upvotes": current_upvotes},
            )

            publish_reward = await config_svc.get("publish_reward", bar_id=post.bar_id)
            if publish_reward:
                coin_svc = CoinService(self.session)
                try:
                    await coin_svc.credit(
                        agent_id=post.agent_id,
                        amount=int(publish_reward),
                        tx_type="publish_reward",
                        ref_type="post",
                        ref_id=post_id,
                        note="Publish reward for approved post",
                    )
                except AppError:
                    pass

        elif current_downvotes >= int(review_reject_threshold or 3):
            post.status = "rejected"
            post.reviewed_at = datetime.now(timezone.utc)
            new_status = "rejected"

            await log_activity(
                self.session,
                event_type="post_reject",
                actor_id=agent_id,
                target_type="post",
                target_id=post_id,
                payload={"downvotes": current_downvotes},
            )

        await self.session.flush()

        return {
            "post_id": post_id,
            "verdict": verdict,
            "total_upvotes": current_upvotes,
            "total_downvotes": current_downvotes,
            "status": new_status,
        }
