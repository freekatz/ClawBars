"""FilterEngine: generic query builder for list endpoints."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession


SORT_DIRECTION = {"-": desc, "": asc}

_CJK_RE = re.compile(r"[\u2e80-\u9fff\uf900-\ufaff\ufe30-\ufe4f]")


class FilterEngine:
    """
    Chainable query builder.

    Usage::

        engine = FilterEngine(Post, request.query_params)
        engine.exact("status")
        engine.prefix("entity_id", param="entity_id_prefix")
        engine.fulltext("q", "search_vector")
        engine.range("created_at", since_param="since", until_param="until")
        engine.numeric_range("upvotes", min_param="min_upvotes")
        engine.numeric_range("quality_score", min_param="min_score")
        engine.tags(param="tags")
        engine.jsonb("content", allowed_fields=schema_fields)
        engine.sort(default="-created_at", allowed=["-created_at", "-quality_score", ...])
        engine.paginate(mode="cursor", cursor_field="id")
        rows, next_cursor = await engine.execute(session)
    """

    def __init__(self, model: type, params: dict[str, Any] | Any):
        self.model = model
        self.params: dict[str, Any] = dict(params) if not isinstance(params, dict) else params
        self._stmt = select(model)
        self._limit: int = 20
        self._cursor_field: str = "id"
        self._offset: int = 0
        self._sort_field: str | None = None
        self._mode: str = "cursor"

    # ── filter helpers ────────────────────────────────────────────────────

    def exact(self, field: str, param: str | None = None) -> "FilterEngine":
        key = param or field
        value = self.params.get(key)
        if value is not None and value != "":
            col = getattr(self.model, field, None)
            if col is not None:
                self._stmt = self._stmt.where(col == value)
        return self

    def prefix(self, field: str, param: str) -> "FilterEngine":
        value = self.params.get(param)
        if value:
            col = getattr(self.model, field, None)
            if col is not None:
                self._stmt = self._stmt.where(col.like(f"{value}%"))
        return self

    def contains(self, field: str, param: str) -> "FilterEngine":
        """包含匹配，等价于 SQL ILIKE '%value%'"""
        value = self.params.get(param)
        if value:
            col = getattr(self.model, field, None)
            if col is not None:
                self._stmt = self._stmt.where(col.ilike(f"%{value}%"))
        return self

    def fulltext(self, param: str, vector_field: str = "search_vector") -> "FilterEngine":
        value = self.params.get(param)
        if value:
            if _CJK_RE.search(value):
                # CJK text: use ILIKE on title/summary (uses pg_trgm GIN index)
                pattern = f"%{value}%"
                title_col = getattr(self.model, "title", None)
                summary_col = getattr(self.model, "summary", None)
                conditions = []
                if title_col is not None:
                    conditions.append(title_col.ilike(pattern))
                if summary_col is not None:
                    conditions.append(summary_col.ilike(pattern))
                if conditions:
                    self._stmt = self._stmt.where(or_(*conditions))
            else:
                vec_col = getattr(self.model, vector_field, None)
                if vec_col is not None:
                    tsquery = func.plainto_tsquery("simple", value)
                    self._stmt = self._stmt.where(vec_col.op("@@")(tsquery))
        return self

    def range(
        self,
        field: str,
        since_param: str | None = None,
        until_param: str | None = None,
    ) -> "FilterEngine":
        col = getattr(self.model, field, None)
        if col is None:
            return self
        if since_param:
            since = self.params.get(since_param)
            if since:
                self._stmt = self._stmt.where(col >= since)
        if until_param:
            until = self.params.get(until_param)
            if until:
                self._stmt = self._stmt.where(col <= until)
        return self

    def numeric_range(
        self,
        field: str,
        min_param: str | None = None,
        max_param: str | None = None,
    ) -> "FilterEngine":
        return self.range(field, since_param=min_param, until_param=max_param)

    def tags(self, param: str = "tags") -> "FilterEngine":
        """Filter posts by comma-separated tag names via post_tags join."""
        value = self.params.get(param)
        if not value:
            return self
        tag_names = [t.strip() for t in str(value).split(",") if t.strip()]
        if not tag_names:
            return self
        from app.models.tag import PostTag, Tag  # local import to avoid circular

        subq = (
            select(PostTag.post_id)
            .join(Tag, Tag.id == PostTag.tag_id)
            .where(Tag.name.in_(tag_names))
        )
        pk = getattr(self.model, "id", None)
        if pk is not None:
            self._stmt = self._stmt.where(pk.in_(subq))
        return self

    def jsonb(self, field: str, allowed_fields: list[str], prefix: str = "content.") -> "FilterEngine":
        """Filter on white-listed top-level JSONB sub-fields.
        Query param pattern: ``content.sentiment=bullish``
        """
        col = getattr(self.model, field, None)
        if col is None:
            return self
        for key in allowed_fields:
            value = self.params.get(f"{prefix}{key}")
            if value is not None and value != "":
                self._stmt = self._stmt.where(col[key].astext == str(value))
        return self

    # ── sort ──────────────────────────────────────────────────────────────

    def sort(
        self,
        default: str = "-created_at",
        allowed: list[str] | None = None,
    ) -> "FilterEngine":
        sort_param = str(self.params.get("sort", default))

        # Validate against allow-list
        if allowed is not None and sort_param not in allowed:
            sort_param = default

        if sort_param.startswith("-"):
            field_name = sort_param[1:]
            direction = desc
        else:
            field_name = sort_param
            direction = asc

        col = getattr(self.model, field_name, None)
        if col is not None:
            self._sort_field = field_name
            # Clear any previous ORDER BY and apply new one
            self._stmt = self._stmt.order_by(None).order_by(direction(col))
        return self

    # ── pagination ────────────────────────────────────────────────────────

    def paginate(self, mode: str = "cursor", cursor_field: str = "id") -> "FilterEngine":
        self._cursor_field = cursor_field

        raw_limit = self.params.get("limit", 20)
        try:
            self._limit = min(max(1, int(raw_limit)), 100)
        except (TypeError, ValueError):
            self._limit = 20

        # Auto-fallback to offset mode when sorting by a field different from cursor_field
        if mode == "cursor" and self._sort_field and self._sort_field != cursor_field:
            mode = "offset"

        self._mode = mode

        if mode == "cursor":
            cursor = self.params.get("cursor")
            if cursor:
                col = getattr(self.model, cursor_field, None)
                if col is not None:
                    # Parse datetime strings for DateTime columns
                    try:
                        cursor_val = datetime.fromisoformat(str(cursor))
                    except (ValueError, TypeError):
                        cursor_val = cursor
                    self._stmt = self._stmt.where(col < cursor_val)
        else:  # offset
            # Read offset from "cursor" param (unified interface for frontend)
            # or fall back to explicit "offset" param
            raw_offset = self.params.get("cursor") or self.params.get("offset", 0)
            try:
                self._offset = max(0, int(raw_offset))
            except (TypeError, ValueError):
                self._offset = 0
            self._stmt = self._stmt.offset(self._offset)

        # Fetch one extra to know if there's a next page
        self._stmt = self._stmt.limit(self._limit + 1)
        return self

    # ── execute ───────────────────────────────────────────────────────────

    async def execute(self, session: AsyncSession) -> tuple[list[Any], str | None]:
        result = await session.execute(self._stmt)
        rows = list(result.scalars().all())

        next_cursor: str | None = None
        if len(rows) > self._limit:
            rows = rows[: self._limit]
            if self._mode == "offset":
                next_cursor = str(self._offset + self._limit)
            else:
                last = rows[-1]
                val = getattr(last, self._cursor_field, None)
                if val is not None:
                    next_cursor = str(val)

        return rows, next_cursor
