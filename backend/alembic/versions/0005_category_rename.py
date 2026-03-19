"""rename category values: knowledge→vault, forum→lounge, premium→vip

Revision ID: 0005_category_rename
Revises: 0004_bar_visibility_category
Create Date: 2026-03-18
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0005_category_rename"
down_revision: Union[str, Sequence[str], None] = "0004_bar_visibility_category"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename category values to match new ClawBars terminology
    op.execute("UPDATE bars SET category = 'vault' WHERE category = 'knowledge'")
    op.execute("UPDATE bars SET category = 'lounge' WHERE category = 'forum'")
    op.execute("UPDATE bars SET category = 'vip' WHERE category = 'premium'")

    # Update server_default to new value
    op.alter_column(
        "bars",
        "category",
        server_default="lounge",
    )


def downgrade() -> None:
    # Revert category names
    op.execute("UPDATE bars SET category = 'knowledge' WHERE category = 'vault'")
    op.execute("UPDATE bars SET category = 'forum' WHERE category = 'lounge'")
    op.execute("UPDATE bars SET category = 'premium' WHERE category = 'vip'")

    # Restore server_default
    op.alter_column(
        "bars",
        "category",
        server_default="knowledge",
    )
