from sqlalchemy import String, Integer, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TranscriptSegment(Base):
    """字幕/ASR 细粒度分段"""
    __tablename__ = "transcript_segments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    video_part_id: Mapped[int] = mapped_column(ForeignKey("video_parts.id"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # bili_subtitle / asr
    start_time: Mapped[float] = mapped_column(Float, nullable=False)  # 秒
    end_time: Mapped[float] = mapped_column(Float, nullable=False)  # 秒
    text: Mapped[str] = mapped_column(Text, nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)  # ASR 置信度，可选


class TranscriptChunk(Base):
    """聚合后的文案分块，用于问答检索"""
    __tablename__ = "transcript_chunks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    video_part_id: Mapped[int] = mapped_column(ForeignKey("video_parts.id"), nullable=False, index=True)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    embedding: Mapped[str | None] = mapped_column(Text, nullable=True)  # 可选向量（JSON 字符串）
    meta: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
