"""Shared authorization helpers for user-owned analysis data."""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.summary import VideoSummary
from app.models.task import AnalysisTask, PartAnalysisTask
from app.models.video import Video, VideoPart


def ensure_video_exists(db: Session, video_id: int) -> Video:
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="视频不存在")
    return video


def user_has_video_access(db: Session, user_id: int, video_id: int) -> bool:
    return (
        db.query(AnalysisTask.id)
        .filter(AnalysisTask.user_id == user_id, AnalysisTask.video_id == video_id)
        .first()
        is not None
    )


def ensure_video_access(db: Session, user_id: int, video_id: int) -> Video:
    video = ensure_video_exists(db, video_id)
    if not user_has_video_access(db, user_id, video_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问此视频数据")
    return video


def ensure_part_in_video(db: Session, video_id: int, part_id: int) -> VideoPart:
    part = db.query(VideoPart).filter(VideoPart.id == part_id).first()
    if not part:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分 P 不存在")
    if part.video_id != video_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="分 P 不属于该视频")
    return part


def get_latest_part_task(
    db: Session,
    user_id: int,
    part_id: int,
    *,
    completed_only: bool = False,
) -> PartAnalysisTask | None:
    query = (
        db.query(PartAnalysisTask)
        .join(AnalysisTask, AnalysisTask.id == PartAnalysisTask.analysis_task_id)
        .filter(AnalysisTask.user_id == user_id, PartAnalysisTask.video_part_id == part_id)
    )
    if completed_only:
        query = query.filter(PartAnalysisTask.status == "completed")
    return query.order_by(PartAnalysisTask.id.desc()).first()


def get_latest_video_summary_for_user(db: Session, user_id: int, video_id: int) -> VideoSummary | None:
    return (
        db.query(VideoSummary)
        .join(AnalysisTask, AnalysisTask.id == VideoSummary.analysis_task_id)
        .filter(AnalysisTask.user_id == user_id, VideoSummary.video_id == video_id)
        .order_by(VideoSummary.id.desc())
        .first()
    )
