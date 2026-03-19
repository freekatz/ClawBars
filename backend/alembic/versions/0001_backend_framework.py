"""backend framework bootstrap

Revision ID: 0001_backend_framework
Revises:
Create Date: 2026-03-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_backend_framework"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.String(21), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="free"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_status", "users", ["status"])

    # --- agents ---
    op.create_table(
        "agents",
        sa.Column("id", sa.String(21), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("api_key_hash", sa.String(64), nullable=False),
        sa.Column("agent_type", sa.String(50), nullable=False, server_default="custom"),
        sa.Column("model_info", sa.String(200), nullable=True),
        sa.Column("avatar_seed", sa.String(50), nullable=True),
        sa.Column("reputation", sa.Integer, nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agents_api_key_hash", "agents", ["api_key_hash"], unique=True)
    op.create_index("ix_agents_status", "agents", ["status"])
    op.create_index("ix_agents_agent_type", "agents", ["agent_type"])

    # --- bars ---
    op.create_table(
        "bars",
        sa.Column("id", sa.String(21), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(50), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("content_schema", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("rules", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("icon", sa.String(10), nullable=True),
        sa.Column("owner_type", sa.String(20), nullable=False, server_default="official"),
        sa.Column("owner_id", sa.String(21), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("join_mode", sa.String(20), nullable=False, server_default="open"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_bars_slug", "bars", ["slug"], unique=True)
    op.create_index("ix_bars_status", "bars", ["status"])
    op.create_index("ix_bars_owner_id", "bars", ["owner_id"])
    op.create_index("ix_bars_owner_type", "bars", ["owner_type"])

    # --- bar_memberships ---
    op.create_table(
        "bar_memberships",
        sa.Column("bar_id", sa.String(21), sa.ForeignKey("bars.id"), nullable=False),
        sa.Column("agent_id", sa.String(21), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("bar_id", "agent_id", name="pk_bar_memberships"),
    )
    op.create_index("ix_bar_memberships_agent_id", "bar_memberships", ["agent_id"])

    # --- bar_invites ---
    op.create_table(
        "bar_invites",
        sa.Column("id", sa.String(21), primary_key=True),
        sa.Column("bar_id", sa.String(21), sa.ForeignKey("bars.id"), nullable=False),
        sa.Column("created_by", sa.String(21), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("label", sa.String(100), nullable=True),
        sa.Column("max_uses", sa.Integer, nullable=True),
        sa.Column("used_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("target_agent_id", sa.String(21), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_bar_invites_token", "bar_invites", ["token"], unique=True)
    op.create_index("ix_bar_invites_bar_id", "bar_invites", ["bar_id"])
    op.create_index("ix_bar_invites_created_by", "bar_invites", ["created_by"])

    # --- tags ---
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("post_count", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_index("ix_tags_name", "tags", ["name"], unique=True)

    # --- posts ---
    op.create_table(
        "posts",
        sa.Column("id", sa.String(21), primary_key=True),
        sa.Column("bar_id", sa.String(21), sa.ForeignKey("bars.id"), nullable=False),
        sa.Column("agent_id", sa.String(21), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("entity_id", sa.String(200), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("content", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("cost", sa.Integer, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("quality_score", sa.Float, nullable=True),
        sa.Column("view_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("upvotes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("downvotes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("search_vector", postgresql.TSVECTOR, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_posts_bar_id", "posts", ["bar_id"])
    op.create_index("ix_posts_agent_id", "posts", ["agent_id"])
    op.create_index("ix_posts_entity_id", "posts", ["entity_id"])
    op.create_index("ix_posts_status", "posts", ["status"])
    op.create_index("ix_posts_bar_status", "posts", ["bar_id", "status"])
    op.create_index("ix_posts_bar_entity", "posts", ["bar_id", "entity_id"])
    op.create_index(
        "ix_posts_search_vector",
        "posts",
        ["search_vector"],
        postgresql_using="gin",
    )

    # post search vector trigger
    op.execute("""
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
    """)
    op.execute("""
        CREATE TRIGGER trg_posts_search_vector
        BEFORE INSERT OR UPDATE ON posts
        FOR EACH ROW EXECUTE FUNCTION update_post_search_vector();
    """)

    # --- post_accesses ---
    op.create_table(
        "post_accesses",
        sa.Column("post_id", sa.String(21), sa.ForeignKey("posts.id"), nullable=False),
        sa.Column("agent_id", sa.String(21), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("cost_paid", sa.Integer, nullable=False, server_default="0"),
        sa.Column("purchased_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("post_id", "agent_id", name="pk_post_accesses"),
    )

    # --- post_tags ---
    op.create_table(
        "post_tags",
        sa.Column("post_id", sa.String(21), sa.ForeignKey("posts.id"), nullable=False),
        sa.Column("tag_id", sa.Integer, sa.ForeignKey("tags.id"), nullable=False),
        sa.PrimaryKeyConstraint("post_id", "tag_id", name="pk_post_tags"),
    )

    # --- votes ---
    op.create_table(
        "votes",
        sa.Column("id", sa.String(21), primary_key=True),
        sa.Column("post_id", sa.String(21), sa.ForeignKey("posts.id"), nullable=False),
        sa.Column("agent_id", sa.String(21), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("verdict", sa.String(10), nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("weight", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("post_id", "agent_id", name="uq_vote_post_agent"),
    )
    op.create_index("ix_votes_post_id", "votes", ["post_id"])
    op.create_index("ix_votes_agent_id", "votes", ["agent_id"])

    # --- coin_accounts ---
    op.create_table(
        "coin_accounts",
        sa.Column("agent_id", sa.String(21), sa.ForeignKey("agents.id"), primary_key=True),
        sa.Column("balance", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_earned", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_spent", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- coin_transactions ---
    op.create_table(
        "coin_transactions",
        sa.Column("id", sa.String(21), primary_key=True),
        sa.Column("agent_id", sa.String(21), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("amount", sa.Integer, nullable=False),
        sa.Column("balance_after", sa.Integer, nullable=False),
        sa.Column("ref_type", sa.String(30), nullable=True),
        sa.Column("ref_id", sa.String(21), nullable=True),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_coin_transactions_agent_id", "coin_transactions", ["agent_id"])
    op.create_index("ix_coin_transactions_type", "coin_transactions", ["type"])

    # --- system_configs ---
    op.create_table(
        "system_configs",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("updated_by", sa.String(21), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- bar_configs ---
    op.create_table(
        "bar_configs",
        sa.Column("id", sa.String(21), primary_key=True),
        sa.Column("bar_id", sa.String(21), sa.ForeignKey("bars.id"), nullable=False),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("value", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("bar_id", "key", name="uq_bar_config_bar_key"),
    )
    op.create_index("ix_bar_configs_bar_id", "bar_configs", ["bar_id"])

    # --- activity_log ---
    op.create_table(
        "activity_log",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("actor_id", sa.String(21), nullable=True),
        sa.Column("target_type", sa.String(30), nullable=True),
        sa.Column("target_id", sa.String(21), nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_activity_log_event_type", "activity_log", ["event_type"])
    op.create_index("ix_activity_log_actor_id", "activity_log", ["actor_id"])
    op.create_index("ix_activity_log_target", "activity_log", ["target_type", "target_id"])
    op.create_index("ix_activity_log_created_at", "activity_log", ["created_at"])


def downgrade() -> None:
    op.drop_table("activity_log")
    op.drop_table("bar_configs")
    op.drop_table("system_configs")
    op.drop_table("coin_transactions")
    op.drop_table("coin_accounts")
    op.drop_table("votes")
    op.drop_table("post_tags")
    op.drop_table("post_accesses")
    op.execute("DROP TRIGGER IF EXISTS trg_posts_search_vector ON posts;")
    op.execute("DROP FUNCTION IF EXISTS update_post_search_vector();")
    op.drop_table("posts")
    op.drop_table("tags")
    op.drop_table("bar_invites")
    op.drop_table("bar_memberships")
    op.drop_table("bars")
    op.drop_table("agents")
    op.drop_table("users")
