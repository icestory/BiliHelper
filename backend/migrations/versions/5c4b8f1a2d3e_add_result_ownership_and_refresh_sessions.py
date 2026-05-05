"""add result ownership and refresh sessions

Revision ID: 5c4b8f1a2d3e
Revises: 2ddfb8aa9d1e
Create Date: 2026-05-05 16:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5c4b8f1a2d3e"
down_revision: Union[str, Sequence[str], None] = "2ddfb8aa9d1e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "refresh_token_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_refresh_token_sessions_user_id"), "refresh_token_sessions", ["user_id"], unique=False)
    op.create_index(op.f("ix_refresh_token_sessions_jti"), "refresh_token_sessions", ["jti"], unique=True)

    op.add_column("transcript_segments", sa.Column("part_analysis_task_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_transcript_segments_part_analysis_task_id",
        "transcript_segments",
        "part_analysis_tasks",
        ["part_analysis_task_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_transcript_segments_part_analysis_task_id"), "transcript_segments", ["part_analysis_task_id"], unique=False)

    op.add_column("transcript_chunks", sa.Column("part_analysis_task_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_transcript_chunks_part_analysis_task_id",
        "transcript_chunks",
        "part_analysis_tasks",
        ["part_analysis_task_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_transcript_chunks_part_analysis_task_id"), "transcript_chunks", ["part_analysis_task_id"], unique=False)

    op.add_column("part_summaries", sa.Column("part_analysis_task_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_part_summaries_part_analysis_task_id",
        "part_summaries",
        "part_analysis_tasks",
        ["part_analysis_task_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_part_summaries_part_analysis_task_id"), "part_summaries", ["part_analysis_task_id"], unique=False)

    op.add_column("chapters", sa.Column("part_analysis_task_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_chapters_part_analysis_task_id",
        "chapters",
        "part_analysis_tasks",
        ["part_analysis_task_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_chapters_part_analysis_task_id"), "chapters", ["part_analysis_task_id"], unique=False)

    op.add_column("video_summaries", sa.Column("analysis_task_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_video_summaries_analysis_task_id",
        "video_summaries",
        "analysis_tasks",
        ["analysis_task_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_video_summaries_analysis_task_id"), "video_summaries", ["analysis_task_id"], unique=False)

    # Legacy rows were global per video/part. Attach them to the latest matching task so existing
    # data remains visible to one owner after the new authorization model is applied.
    op.execute(
        """
        UPDATE transcript_segments target
        SET part_analysis_task_id = owner.id
        FROM (
            SELECT DISTINCT ON (video_part_id) id, video_part_id
            FROM part_analysis_tasks
            WHERE status = 'completed'
            ORDER BY video_part_id, id DESC
        ) owner
        WHERE target.video_part_id = owner.video_part_id
          AND target.part_analysis_task_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE transcript_chunks target
        SET part_analysis_task_id = owner.id
        FROM (
            SELECT DISTINCT ON (video_part_id) id, video_part_id
            FROM part_analysis_tasks
            WHERE status = 'completed'
            ORDER BY video_part_id, id DESC
        ) owner
        WHERE target.video_part_id = owner.video_part_id
          AND target.part_analysis_task_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE part_summaries target
        SET part_analysis_task_id = owner.id
        FROM (
            SELECT DISTINCT ON (video_part_id) id, video_part_id
            FROM part_analysis_tasks
            WHERE status = 'completed'
            ORDER BY video_part_id, id DESC
        ) owner
        WHERE target.video_part_id = owner.video_part_id
          AND target.part_analysis_task_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE chapters target
        SET part_analysis_task_id = owner.id
        FROM (
            SELECT DISTINCT ON (video_part_id) id, video_part_id
            FROM part_analysis_tasks
            WHERE status = 'completed'
            ORDER BY video_part_id, id DESC
        ) owner
        WHERE target.video_part_id = owner.video_part_id
          AND target.part_analysis_task_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE video_summaries target
        SET analysis_task_id = owner.id
        FROM (
            SELECT DISTINCT ON (video_id) id, video_id
            FROM analysis_tasks
            ORDER BY video_id, id DESC
        ) owner
        WHERE target.video_id = owner.video_id
          AND target.analysis_task_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_video_summaries_analysis_task_id"), table_name="video_summaries")
    op.drop_constraint("fk_video_summaries_analysis_task_id", "video_summaries", type_="foreignkey")
    op.drop_column("video_summaries", "analysis_task_id")

    op.drop_index(op.f("ix_chapters_part_analysis_task_id"), table_name="chapters")
    op.drop_constraint("fk_chapters_part_analysis_task_id", "chapters", type_="foreignkey")
    op.drop_column("chapters", "part_analysis_task_id")

    op.drop_index(op.f("ix_part_summaries_part_analysis_task_id"), table_name="part_summaries")
    op.drop_constraint("fk_part_summaries_part_analysis_task_id", "part_summaries", type_="foreignkey")
    op.drop_column("part_summaries", "part_analysis_task_id")

    op.drop_index(op.f("ix_transcript_chunks_part_analysis_task_id"), table_name="transcript_chunks")
    op.drop_constraint("fk_transcript_chunks_part_analysis_task_id", "transcript_chunks", type_="foreignkey")
    op.drop_column("transcript_chunks", "part_analysis_task_id")

    op.drop_index(op.f("ix_transcript_segments_part_analysis_task_id"), table_name="transcript_segments")
    op.drop_constraint("fk_transcript_segments_part_analysis_task_id", "transcript_segments", type_="foreignkey")
    op.drop_column("transcript_segments", "part_analysis_task_id")

    op.drop_index(op.f("ix_refresh_token_sessions_jti"), table_name="refresh_token_sessions")
    op.drop_index(op.f("ix_refresh_token_sessions_user_id"), table_name="refresh_token_sessions")
    op.drop_table("refresh_token_sessions")
