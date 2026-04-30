from datetime import datetime, timezone

from sqlalchemy import String, Integer, BigInteger, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bvid: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    aid: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    owner_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    owner_mid: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 秒
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    part_count: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class VideoPart(Base):
    __tablename__ = "video_parts"
    __table_args__ = (
        UniqueConstraint("video_id", "page_no", name="uq_video_part_page"),
        UniqueConstraint("video_id", "cid", name="uq_video_part_cid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), nullable=False, index=True)
    page_no: Mapped[int] = mapped_column(Integer, nullable=False)  # P 序号，从 1 开始
    cid: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 秒
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
