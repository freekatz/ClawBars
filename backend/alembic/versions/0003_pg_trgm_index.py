"""add pg_trgm extension and trigram index on posts

Revision ID: 0003_pg_trgm_index
Revises: b1943b103d92
Create Date: 2026-03-18
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0003_pg_trgm_index"
down_revision: Union[str, Sequence[str], None] = "b1943b103d92"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_posts_title_trgm ON posts USING GIN (title gin_trgm_ops);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_posts_title_trgm;")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm;")
