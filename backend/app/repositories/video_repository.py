from sqlalchemy.orm import Session

from app.models.video import Video, VideoPart


def get_video_by_bvid(db: Session, bvid: str) -> Video | None:
    return db.query(Video).filter(Video.bvid == bvid).first()


def get_video_by_id(db: Session, video_id: int) -> Video | None:
    return db.query(Video).filter(Video.id == video_id).first()


def create_video(db: Session, **kwargs) -> Video:
    video = Video(**kwargs)
    db.add(video)
    db.commit()
    db.refresh(video)
    return video


def update_video(db: Session, video: Video, **kwargs) -> Video:
    for key, value in kwargs.items():
        setattr(video, key, value)
    db.commit()
    db.refresh(video)
    return video


def create_video_part(db: Session, **kwargs) -> VideoPart:
    part = VideoPart(**kwargs)
    db.add(part)
    db.commit()
    db.refresh(part)
    return part


def update_video_part(db: Session, part: VideoPart, **kwargs) -> VideoPart:
    for key, value in kwargs.items():
        setattr(part, key, value)
    db.commit()
    db.refresh(part)
    return part


def get_parts_by_video(db: Session, video_id: int) -> list[VideoPart]:
    return db.query(VideoPart).filter(VideoPart.video_id == video_id).order_by(VideoPart.page_no).all()


def get_part_by_id(db: Session, part_id: int) -> VideoPart | None:
    return db.query(VideoPart).filter(VideoPart.id == part_id).first()


def get_video_history(
    db: Session,
    user_id: int,
    page: int = 1,
    page_size: int = 20,
    q: str | None = None,
    owner: str | None = None,
) -> list[Video]:
    """获取用户分析过的视频历史（通过 analysis_tasks 关联）"""
    from app.models.task import AnalysisTask

    query = (
        db.query(Video)
        .join(AnalysisTask, AnalysisTask.video_id == Video.id)
        .filter(AnalysisTask.user_id == user_id)
        .distinct()
    )

    if q:
        query = query.filter(Video.title.ilike(f"%{q}%"))
    if owner:
        query = query.filter(Video.owner_name.ilike(f"%{owner}%"))

    query = query.order_by(Video.created_at.desc())
    return query.offset((page - 1) * page_size).limit(page_size).all()


def count_video_history(
    db: Session, user_id: int, q: str | None = None, owner: str | None = None
) -> int:
    from app.models.task import AnalysisTask

    query = (
        db.query(Video)
        .join(AnalysisTask, AnalysisTask.video_id == Video.id)
        .filter(AnalysisTask.user_id == user_id)
    )
    if q:
        query = query.filter(Video.title.ilike(f"%{q}%"))
    if owner:
        query = query.filter(Video.owner_name.ilike(f"%{owner}%"))
    return query.count()


def delete_video_history(db: Session, user_id: int, video_id: int) -> int:
    """删除用户对某个视频的分析记录（保留视频元数据）"""
    from app.models.task import AnalysisTask

    deleted = (
        db.query(AnalysisTask)
        .filter(AnalysisTask.user_id == user_id, AnalysisTask.video_id == video_id)
        .delete()
    )
    db.commit()
    return deleted
