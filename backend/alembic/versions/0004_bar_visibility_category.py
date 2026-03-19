"""rename bar_type to visibility, add category column

Revision ID: 0004_bar_visibility_category
Revises: 0003_pg_trgm_index
Create Date: 2026-03-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_bar_visibility_category"
down_revision: Union[str, Sequence[str], None] = "0003_pg_trgm_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename bar_type → visibility
    op.alter_column("bars", "bar_type", new_column_name="visibility")
    op.drop_index("ix_bars_bar_type", table_name="bars")
    op.create_index("ix_bars_visibility", "bars", ["visibility"], unique=False)

    # Add category column
    op.add_column(
        "bars",
        sa.Column("category", sa.String(length=20), server_default="knowledge", nullable=False),
    )
    op.create_index("ix_bars_category", "bars", ["category"], unique=False)

    # Data migration: private user-owned bars → premium category
    op.execute(
        "UPDATE bars SET category = 'premium' WHERE visibility = 'private' AND owner_type = 'user'"
    )


def downgrade() -> None:
    op.drop_index("ix_bars_category", table_name="bars")
    op.drop_column("bars", "category")

    op.alter_column("bars", "visibility", new_column_name="bar_type")
    op.drop_index("ix_bars_visibility", table_name="bars")
    op.create_index("ix_bars_bar_type", "bars", ["bar_type"], unique=False)
