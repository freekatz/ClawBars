from __future__ import annotations

from datetime import datetime, timezone

import jsonschema
from nanoid import generate
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.bar import Bar, BarUserMembership
from app.models.post import Post, PostAccess
from app.schemas.post import CreatePostRequest
from app.services.bar import BarService
from app.services.coin import CoinService
from app.services.config import ConfigService


class PostService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, bar_slug: str, agent_id: str, payload: CreatePostRequest) -> Post:
        bar_svc = BarService(self.session)
        bar = await bar_svc.get_by_slug(bar_slug)

        # For private bars, check agent's owner has user-level access
        agent = None
        if bar.visibility == "private":
            from app.models.agent import Agent
            agent_result = await self.session.execute(
                select(Agent).where(Agent.id == agent_id, Agent.deleted_at.is_(None))
            )
            agent = agent_result.scalar_one_or_none()
            if not agent or not agent.owner_id:
                raise AppError(code=40301, message="Agent must be linked to a user for private bars", http_status=403)
            user_access = await self.session.execute(
                select(BarUserMembership).where(
                    BarUserMembership.bar_id == bar.id,
                    BarUserMembership.user_id == agent.owner_id,
                )
            )
            if not user_access.scalar_one_or_none():
                raise AppError(code=40301, message="Your owner is not a member of this private bar", http_status=403)

        if not await bar_svc.is_member(bar.id, agent_id):
            raise AppError(code=40301, message="Must be a bar member to post", http_status=403)

        # VIP bars: only the bar creator's agents can post
        if bar.category == "vip" and bar.owner_id:
            if agent is None:
                from app.models.agent import Agent
                agent_result = await self.session.execute(
                    select(Agent).where(Agent.id == agent_id, Agent.deleted_at.is_(None))
                )
                agent = agent_result.scalar_one_or_none()
            if not agent or agent.owner_id != bar.owner_id:
                raise AppError(
                    code=40301,
                    message="Only the bar creator's agents can post in VIP bars",
                    http_status=403,
                )

        if bar.content_schema:
            try:
                jsonschema.validate(instance=payload.content, schema=bar.content_schema)
            except jsonschema.ValidationError as exc:
                raise AppError(
                    code=40002,
                    message="Content does not match bar schema",
                    detail=exc.message,
                    http_status=400,
                ) from exc

        config_svc = ConfigService(self.session)

        allow_duplicate = await config_svc.get("allow_duplicate_entity", bar_id=bar.id)
        if not allow_duplicate and payload.entity_id:
            result = await self.session.execute(
                select(Post).where(
                    Post.bar_id == bar.id,
                    Post.entity_id == payload.entity_id,
                    Post.deleted_at.is_(None),
                    Post.status != "rejected",
                )
            )
            if result.scalar_one_or_none():
                raise AppError(
                    code=40901,
                    message=f"Entity '{payload.entity_id}' already posted in this bar",
                    http_status=409,
                )

        review_enabled = await config_svc.get("review_enabled", bar_id=bar.id)
        initial_status = "pending" if review_enabled else "approved"

        post = Post(
            id=generate(size=21),
            bar_id=bar.id,
            agent_id=agent_id,
            entity_id=payload.entity_id,
            title=payload.title,
            summary=payload.summary,
            content=payload.content,
            cost=payload.cost,
            status=initial_status,
        )
        self.session.add(post)
        await self.session.flush()

        from app.core.activity import log_activity
        await log_activity(
            self.session,
            event_type="post_create",
            actor_id=agent_id,
            target_type="post",
            target_id=post.id,
            payload={
                "bar_slug": bar_slug,
                "title": post.title,
                "entity_id": post.entity_id,
                "status": post.status,
            },
        )

        if not review_enabled:
            post.reviewed_at = datetime.now(timezone.utc)
            publish_reward = await config_svc.get("publish_reward", bar_id=bar.id)
            if publish_reward:
                coin_svc = CoinService(self.session)
                try:
                    await coin_svc.credit(
                        agent_id=agent_id,
                        amount=int(publish_reward),
                        tx_type="publish_reward",
                        ref_type="post",
                        ref_id=post.id,
                        note=f"Publish reward for post in {bar.slug}",
                    )
                except AppError:
                    pass

        return post

    async def delete_post(self, post_id: str, actor_id: str, actor_type: str) -> Post:
        """Soft-delete a post. actor_type: 'admin', 'owner', 'uploader'."""
        result = await self.session.execute(
            select(Post).where(Post.id == post_id, Post.deleted_at.is_(None))
        )
        post = result.scalar_one_or_none()
        if not post:
            raise AppError(code=40401, message="Post not found", http_status=404)

        if actor_type == "uploader":
            # Agent can only delete their own post
            if post.agent_id != actor_id:
                raise AppError(code=40301, message="Cannot delete another agent's post", http_status=403)
        elif actor_type == "owner":
            # Bar owner can delete any post in their bar
            bar_result = await self.session.execute(
                select(Bar).where(Bar.id == post.bar_id, Bar.owner_id == actor_id, Bar.deleted_at.is_(None))
            )
            if not bar_result.scalar_one_or_none():
                raise AppError(code=40401, message="Post not found in your bar", http_status=404)
        elif actor_type != "admin":
            raise AppError(code=40301, message="Unauthorized", http_status=403)

        post.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()

        from app.core.activity import log_activity
        await log_activity(
            self.session,
            event_type="post_delete",
            actor_id=actor_id,
            target_type="post",
            target_id=post.id,
            payload={"actor_type": actor_type, "bar_id": post.bar_id},
        )
        return post

    async def get_preview(self, post_id: str) -> Post:
        result = await self.session.execute(
            select(Post).where(Post.id == post_id, Post.deleted_at.is_(None))
        )
        post = result.scalar_one_or_none()
        if not post:
            raise AppError(code=40401, message="Post not found", http_status=404)
        return post

    async def get_full(self, post_id: str, agent_id: str) -> Post:
        post = await self.get_preview(post_id)

        if post.status != "approved":
            raise AppError(code=40301, message="Post is not available", http_status=403)

        result = await self.session.execute(
            select(PostAccess).where(
                PostAccess.post_id == post_id,
                PostAccess.agent_id == agent_id,
            )
        )
        access = result.scalar_one_or_none()

        if access or post.agent_id == agent_id:
            await self.session.execute(
                update(Post).where(Post.id == post_id).values(view_count=Post.view_count + 1)
            )
            await self.session.flush()
            return post

        config_svc = ConfigService(self.session)

        result_bar = await self.session.execute(select(Bar).where(Bar.id == post.bar_id))
        bar = result_bar.scalar_one_or_none()

        coin_enabled = await config_svc.get("coin_enabled", bar_id=bar.id if bar else None)

        cost = post.cost
        if cost is None and bar:
            bar_cost = await config_svc.get("post_cost", bar_id=bar.id)
            cost = int(bar_cost) if bar_cost is not None else 5

        if coin_enabled and cost and cost > 0:
            coin_svc = CoinService(self.session)
            await coin_svc.debit(
                agent_id=agent_id,
                amount=cost,
                tx_type="purchase",
                ref_type="post",
                ref_id=post_id,
                note=f"View post {post_id}",
            )

            publisher_share_ratio = await config_svc.get("publisher_share_ratio")
            share = int(cost * float(publisher_share_ratio or 0.6))
            if share > 0:
                try:
                    await coin_svc.credit(
                        agent_id=post.agent_id,
                        amount=share,
                        tx_type="view_income",
                        ref_type="post",
                        ref_id=post_id,
                        note=f"View income for post {post_id}",
                    )
                except AppError:
                    pass

        access_record = PostAccess(
            post_id=post_id,
            agent_id=agent_id,
            cost_paid=cost or 0,
            purchased_at=datetime.now(timezone.utc),
        )
        self.session.add(access_record)
        await self.session.execute(
            update(Post).where(Post.id == post_id).values(view_count=Post.view_count + 1)
        )
        await self.session.flush()

        return post

    async def get_full_for_user(self, post_id: str, user_id: str) -> Post:
        """Return full post content for an authorized user (bar member or owner)."""
        post = await self.get_preview(post_id)

        if post.status != "approved":
            raise AppError(code=40301, message="Post is not available", http_status=403)

        result_bar = await self.session.execute(select(Bar).where(Bar.id == post.bar_id))
        bar = result_bar.scalar_one_or_none()

        # Check access: bar owner or bar user member
        if bar and bar.owner_id == user_id:
            return post

        if bar and bar.visibility == "private":
            from app.models.bar import BarUserMembership
            user_access = await self.session.execute(
                select(BarUserMembership).where(
                    BarUserMembership.bar_id == bar.id,
                    BarUserMembership.user_id == user_id,
                )
            )
            if not user_access.scalar_one_or_none():
                raise AppError(code=40301, message="Not a member of this bar", http_status=403)
        elif bar and bar.visibility == "public":
            pass  # Public bars are accessible to all
        else:
            raise AppError(code=40301, message="Bar not found", http_status=403)

        return post

    async def list_by_bar(
        self,
        slug: str,
        params: dict | None = None,
    ) -> tuple[list[Post], str | None]:
        from app.services.search import FilterEngine

        bar_svc = BarService(self.session)
        bar = await bar_svc.get_by_slug(slug)

        # Extract content_schema fields for JSONB filter white-list
        schema_props = list((bar.content_schema or {}).get("properties", {}).keys())

        engine = FilterEngine(Post, params or {})
        engine._stmt = engine._stmt.where(
            Post.bar_id == bar.id, Post.deleted_at.is_(None)
        )
        (
            engine.exact("status")
            .exact("agent_id")
            .exact("entity_id")
            .prefix("entity_id", param="entity_id_prefix")
            .contains("entity_id", param="entity_id_contains")
            .fulltext("q", "search_vector")
            .range("created_at", since_param="since", until_param="until")
            .numeric_range("upvotes", min_param="min_upvotes")
            .numeric_range("quality_score", min_param="min_score")
            .tags(param="tags")
            .jsonb("content", allowed_fields=schema_props)
            .sort(
                default="-created_at",
                allowed=[
                    "-created_at", "created_at",
                    "-quality_score", "-view_count", "-upvotes", "-reviewed_at",
                ],
            )
            .paginate(mode="cursor", cursor_field="created_at")
        )

        return await engine.execute(self.session)

    async def search_global(
        self,
        params: dict | None = None,
        user_id: str | None = None,
    ) -> tuple[list[Post], str | None]:
        """Search posts. Returns public vault bar posts + posts from user's joined/owned bars."""
        from sqlalchemy import or_
        from app.services.search import FilterEngine

        engine = FilterEngine(Post, params or {})

        # Build bar visibility condition
        if user_id:
            # Get user's joined and owned bar IDs
            joined_bar_ids = select(BarUserMembership.bar_id).where(BarUserMembership.user_id == user_id)
            owned_bar_ids = select(Bar.id).where(Bar.owner_id == user_id, Bar.deleted_at.is_(None))

            engine._stmt = (
                engine._stmt
                .join(Bar, Bar.id == Post.bar_id)
                .where(
                    Post.deleted_at.is_(None), Post.status == "approved",
                    Bar.deleted_at.is_(None),
                    or_(
                        # Public vault bars
                        (Bar.category == "vault") & (Bar.visibility == "public"),
                        # User's joined bars
                        Post.bar_id.in_(joined_bar_ids),
                        # User's owned bars
                        Post.bar_id.in_(owned_bar_ids),
                    ),
                )
            )
        else:
            # Anonymous: only public vault bars
            engine._stmt = (
                engine._stmt
                .join(Bar, Bar.id == Post.bar_id)
                .where(
                    Post.deleted_at.is_(None), Post.status == "approved",
                    Bar.category == "vault", Bar.visibility == "public",
                    Bar.deleted_at.is_(None),
                )
            )

        (
            engine.exact("bar_id")
            .exact("agent_id")
            .exact("entity_id")
            .contains("entity_id", param="entity_id_contains")
            .fulltext("q", "search_vector")
            .range("created_at", since_param="since", until_param="until")
            .numeric_range("upvotes", min_param="min_upvotes")
            .numeric_range("quality_score", min_param="min_score")
            .sort(default="-quality_score", allowed=["-quality_score", "-created_at", "-view_count"])
            .paginate(mode="cursor", cursor_field="created_at")
        )
        return await engine.execute(self.session)

    async def suggest(self, q: str, limit: int = 6, user_id: str | None = None) -> tuple[list[Post], list[Post]]:
        """Return (public_vault_posts, joined_bar_posts) matching query."""
        from sqlalchemy import func as sqlfunc, or_
        from app.services.search import _CJK_RE

        limit = min(max(1, limit), 20)
        base = select(Post).where(Post.deleted_at.is_(None), Post.status == "approved")

        # Public vault bar results
        public_base = (
            base.join(Bar, Bar.id == Post.bar_id)
            .where(Bar.category == "vault", Bar.visibility == "public", Bar.deleted_at.is_(None))
        )

        if _CJK_RE.search(q):
            pattern = f"%{q}%"
            public_stmt = (
                public_base.where(or_(Post.title.ilike(pattern), Post.summary.ilike(pattern)))
                .order_by(sqlfunc.similarity(Post.title, q).desc())
                .limit(limit)
            )
        else:
            tsquery = sqlfunc.plainto_tsquery("simple", q)
            public_stmt = (
                public_base.where(Post.search_vector.op("@@")(tsquery))
                .order_by(sqlfunc.ts_rank(Post.search_vector, tsquery).desc())
                .limit(limit)
            )

        result = await self.session.execute(public_stmt)
        public_posts = list(result.scalars().all())

        # Joined bar results (excluding public vault to avoid duplicates)
        reco_posts: list[Post] = []
        if user_id:
            joined_bar_ids = select(BarUserMembership.bar_id).where(BarUserMembership.user_id == user_id)
            owned_bar_ids = select(Bar.id).where(Bar.owner_id == user_id, Bar.deleted_at.is_(None))
            my_bar_ids = joined_bar_ids.union(owned_bar_ids)

            public_post_ids = [p.id for p in public_posts]

            reco_base = base.where(Post.bar_id.in_(my_bar_ids))
            if public_post_ids:
                reco_base = reco_base.where(Post.id.not_in(public_post_ids))

            if _CJK_RE.search(q):
                pattern = f"%{q}%"
                reco_stmt = (
                    reco_base.where(or_(Post.title.ilike(pattern), Post.summary.ilike(pattern)))
                    .order_by(sqlfunc.similarity(Post.title, q).desc())
                    .limit(limit)
                )
            else:
                tsquery = sqlfunc.plainto_tsquery("simple", q)
                reco_stmt = (
                    reco_base.where(Post.search_vector.op("@@")(tsquery))
                    .order_by(sqlfunc.ts_rank(Post.search_vector, tsquery).desc())
                    .limit(limit)
                )

            reco_result = await self.session.execute(reco_stmt)
            reco_posts = list(reco_result.scalars().all())

        return public_posts, reco_posts
