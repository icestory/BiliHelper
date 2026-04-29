from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class AnalysisTask(Base):
    __tablename__ = "analysis_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="waiting")  # waiting / running / completed / failed / partial_failed
    selected_part_ids: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)  # 选中的分 P ID 列表
    force_reanalyze: Mapped[bool] = mapped_column(default=False)
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class PartAnalysisTask(Base):
    __tablename__ = "part_analysis_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    analysis_task_id: Mapped[int] = mapped_column(ForeignKey("analysis_tasks.id"), nullable=False, index=True)
    video_part_id: Mapped[int] = mapped_column(ForeignKey("video_parts.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="waiting")  # waiting / fetching_subtitle / asr / summarizing / completed / failed
    transcript_source: Mapped[str | None] = mapped_column(String(20), nullable=True)  # bili_subtitle / asr / manual
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
