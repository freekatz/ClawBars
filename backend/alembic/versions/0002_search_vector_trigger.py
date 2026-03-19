"""Add tsvector trigger for posts.search_vector (B-3.2)

Revision ID: 0002_search_vector_trigger
Revises: 0001_backend_framework
Create Date: 2026-03-16
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_search_vector_trigger"
down_revision: str | None = "0001_backend_framework"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CREATE_FUNC = """
CREATE OR REPLACE FUNCTION update_post_search_vector()
RETURNS trigger AS $$
BEGIN
  NEW.search_vector :=
    setweight(to_tsvector('simple', coalesce(NEW.title, '')), 'A') ||
    setweight(to_tsvector('simple', coalesce(NEW.summary, '')), 'B') ||
    setweight(to_tsvector('simple', coalesce(NEW.entity_id, '')), 'A');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

_CREATE_TRIGGER = """
CREATE TRIGGER trig_post_search_vector
BEFORE INSERT OR UPDATE OF title, summary, entity_id
ON posts
FOR EACH ROW EXECUTE FUNCTION update_post_search_vector();
"""

_DROP_TRIGGER = "DROP TRIGGER IF EXISTS trig_post_search_vector ON posts;"
_DROP_FUNC = "DROP FUNCTION IF EXISTS update_post_search_vector();"

_BACKFILL = """
UPDATE posts
SET search_vector =
    setweight(to_tsvector('simple', coalesce(title, '')), 'A') ||
    setweight(to_tsvector('simple', coalesce(summary, '')), 'B') ||
    setweight(to_tsvector('simple', coalesce(entity_id, '')), 'A');
"""

_CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS ix_posts_search_vector
ON posts USING GIN (search_vector);
"""

_DROP_INDEX = "DROP INDEX IF EXISTS ix_posts_search_vector;"


def upgrade() -> None:
    op.execute(_CREATE_FUNC)
    op.execute(_CREATE_TRIGGER)
    op.execute(_BACKFILL)
    op.execute(_CREATE_INDEX)


def downgrade() -> None:
    op.execute(_DROP_INDEX)
    op.execute(_DROP_TRIGGER)
    op.execute(_DROP_FUNC)
