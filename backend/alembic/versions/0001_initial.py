"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-20

"""
import sqlalchemy as sa

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "shows",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String(255), nullable=False, unique=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("section", sa.String(64), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_shows_slug", "shows", ["slug"])

    op.create_table(
        "seasons",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("show_id", sa.Integer, sa.ForeignKey("shows.id", ondelete="CASCADE"), nullable=False),
        sa.Column("season_number", sa.Integer, nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("show_id", "season_number", name="uq_season_show_number"),
    )

    op.create_table(
        "episodes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("season_id", sa.Integer, sa.ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("show_id", sa.Integer, sa.ForeignKey("shows.id", ondelete="CASCADE"), nullable=False),
        sa.Column("episode_number", sa.Integer, nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("synopsis", sa.Text, nullable=True),
        sa.Column("content_group", sa.String(128), nullable=False),
        sa.Column("language", sa.String(8), nullable=False),
        sa.Column("duration_seconds", sa.Integer, nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_episodes_content_group", "episodes", ["content_group"])
    op.create_index(
        "ix_episode_season_number_language", "episodes", ["season_id", "episode_number", "language"]
    )

    op.create_table(
        "artwork",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("owner_type", sa.String(16), nullable=False),
        sa.Column("owner_id", sa.Integer, nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column("storage_key", sa.String(1000), nullable=False),
        sa.Column("width", sa.Integer, nullable=False),
        sa.Column("height", sa.Integer, nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=False),
        sa.Column("mime_type", sa.String(64), nullable=False),
        sa.Column("alt_text", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("owner_type", "owner_id", "kind", name="uq_artwork_owner_kind"),
    )

    op.create_table(
        "publish_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("run_id", sa.String(64), nullable=False, unique=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("version", sa.Integer, nullable=True),
        sa.Column("published_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column("dry_run", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("counts_json", sa.Text, nullable=True),
        sa.Column("warnings_json", sa.Text, nullable=True),
        sa.Column("catalog_hash", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "uq_publish_run_running",
        "publish_runs",
        ["status"],
        unique=True,
        postgresql_where=sa.text("status = 'running'"),
    )


def downgrade() -> None:
    op.drop_table("publish_runs")
    op.drop_table("artwork")
    op.drop_table("episodes")
    op.drop_table("seasons")
    op.drop_table("shows")
    op.drop_table("users")
