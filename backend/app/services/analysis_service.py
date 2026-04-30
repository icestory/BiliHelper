from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.task import AnalysisTask, PartAnalysisTask
from app.models.video import VideoPart
from app.repositories import video_repository
from app.schemas.analysis import (
    AnalysisTaskCreate,
    AnalysisTaskResponse,
    PartAnalysisStatus,
    PartAnalysisDetail,
)


def _utcnow():
    return datetime.now(timezone.utc)


class AnalysisService:
    def __init__(self, db: Session):
        self.db = db

    def create_task(self, user_id: int, data: AnalysisTaskCreate) -> AnalysisTaskResponse:
        # 验证视频存在
        video = video_repository.get_video_by_id(self.db, data.video_id)
        if not video:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="视频不存在")

        # 获取要分析的分 P
        all_parts = video_repository.get_parts_by_video(self.db, data.video_id)
        if data.part_ids:
            selected_parts = [p for p in all_parts if p.id in data.part_ids]
        else:
            selected_parts = all_parts

        if not selected_parts:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="没有选择需要分析的分 P")

        # 创建总任务
        task = AnalysisTask(
            user_id=user_id,
            video_id=data.video_id,
            selected_part_ids=[p.id for p in selected_parts],
            force_reanalyze=data.force_reanalyze,
            status="waiting",
            progress=0,
        )
        self.db.add(task)
        self.db.flush()  # 获取 task.id

        # 为每个分 P 创建子任务
        for part in selected_parts:
            sub = PartAnalysisTask(
                analysis_task_id=task.id,
                video_part_id=part.id,
                status="waiting",
                progress=0,
            )
            self.db.add(sub)

        self.db.commit()
        self.db.refresh(task)

        # 异步投递 Celery 任务
        from app.workers.tasks.analyze_part import start_analysis
        start_analysis.delay(task.id)

        return self._to_response(task)

    def get_task(self, task_id: int, user_id: int | None = None) -> AnalysisTaskResponse:
        task = self.db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
        if user_id and task.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问此任务")
        return self._to_response(task)

    def get_part_analysis(self, part_id: int, user_id: int | None = None) -> PartAnalysisDetail:
        from app.models.transcript import TranscriptSegment
        from app.models.summary import PartSummary, Chapter

        # 获取最新的子任务
        sub = (
            self.db.query(PartAnalysisTask)
            .filter(PartAnalysisTask.video_part_id == part_id)
            .order_by(PartAnalysisTask.id.desc())
            .first()
        )

        # 权限检查：验证用户是否拥有该分析数据
        if user_id is not None and sub is not None:
            task = self.db.query(AnalysisTask).filter(AnalysisTask.id == sub.analysis_task_id).first()
            if task and task.user_id != user_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问此分析数据")

        part = video_repository.get_part_by_id(self.db, part_id)

        segments = None
        if sub and sub.status == "completed":
            segs = (
                self.db.query(TranscriptSegment)
                .filter(TranscriptSegment.video_part_id == part_id)
                .order_by(TranscriptSegment.sequence_no)
                .all()
            )
            segments = [
                {"start_time": s.start_time, "end_time": s.end_time, "text": s.text, "source": s.source}
                for s in segs
            ]

        summary = None
        chapters = None
        if sub and sub.status == "completed":
            ps = (
                self.db.query(PartSummary)
                .filter(PartSummary.video_part_id == part_id)
                .order_by(PartSummary.id.desc())
                .first()
            )
            if ps:
                summary = {
                    "summary": ps.summary,
                    "detailed_summary": ps.detailed_summary,
                    "key_points": ps.key_points,
                }

            chs = (
                self.db.query(Chapter)
                .filter(Chapter.video_part_id == part_id)
                .order_by(Chapter.sequence_no)
                .all()
            )
            chapters = [
                {
                    "start_time": c.start_time,
                    "end_time": c.end_time,
                    "title": c.title,
                    "description": c.description,
                    "keywords": c.keywords,
                }
                for c in chs
            ]

        return PartAnalysisDetail(
            id=sub.id if sub else 0,
            video_part_id=part_id,
            status=sub.status if sub else "unknown",
            transcript_source=sub.transcript_source if sub else None,
            transcript_segments=segments,
            summary=summary,
            chapters=chapters,
            error_message=sub.error_message if sub else None,
            started_at=sub.started_at.isoformat() if sub and sub.started_at else None,
            finished_at=sub.finished_at.isoformat() if sub and sub.finished_at else None,
        )

    def retry_task(self, user_id: int, task_id: int) -> AnalysisTaskResponse:
        task = self.db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
        if task.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作此任务")

        if task.status not in ("failed", "partial_failed"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅失败任务支持重试")

        # 重置失败子任务的状态
        failed_subs = (
            self.db.query(PartAnalysisTask)
            .filter(PartAnalysisTask.analysis_task_id == task_id, PartAnalysisTask.status == "failed")
            .all()
        )
        for sub in failed_subs:
            sub.status = "waiting"
            sub.progress = 0
            sub.error_message = None
            sub.started_at = None
            sub.finished_at = None
            sub.retry_count = (sub.retry_count or 0) + 1

        task.status = "waiting"
        task.error_message = None
        task.finished_at = None
        self.db.commit()

        # 重新投递
        from app.workers.tasks.analyze_part import start_analysis
        start_analysis.delay(task.id)

        return self._to_response(task)

    def reanalyze_part(self, user_id: int, part_id: int, force: bool = False) -> PartAnalysisDetail:
        """重新分析单个分 P"""
        part = video_repository.get_part_by_id(self.db, part_id)
        if not part:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分 P 不存在")

        # 获取视频归属判断权限
        video = video_repository.get_video_by_id(self.db, part.video_id)
        if not video:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="视频不存在")

        # 创建独立的任务
        task = AnalysisTask(
            user_id=user_id,
            video_id=part.video_id,
            selected_part_ids=[part_id],
            force_reanalyze=force,
            status="waiting",
            progress=0,
        )
        self.db.add(task)
        self.db.flush()

        sub = PartAnalysisTask(
            analysis_task_id=task.id,
            video_part_id=part_id,
            status="waiting",
            progress=0,
        )
        self.db.add(sub)
        self.db.commit()

        from app.workers.tasks.analyze_part import start_analysis
        start_analysis.delay(task.id)

        return PartAnalysisDetail(
            id=sub.id,
            video_part_id=part_id,
            status="waiting",
            transcript_source=None,
            transcript_segments=None,
            summary=None,
            chapters=None,
            error_message=None,
        )

    def _to_response(self, task: AnalysisTask) -> AnalysisTaskResponse:
        subs = (
            self.db.query(PartAnalysisTask)
            .filter(PartAnalysisTask.analysis_task_id == task.id)
            .all()
        )

        parts_status = []
        for sub in subs:
            part = video_repository.get_part_by_id(self.db, sub.video_part_id)
            parts_status.append(PartAnalysisStatus(
                id=sub.id,
                video_part_id=sub.video_part_id,
                page_no=part.page_no if part else None,
                part_title=part.title if part else None,
                status=sub.status,
                transcript_source=sub.transcript_source,
                progress=sub.progress,
                error_message=sub.error_message,
            ))

        return AnalysisTaskResponse(
            id=task.id,
            video_id=task.video_id,
            status=task.status,
            progress=task.progress,
            error_message=task.error_message,
            parts=parts_status,
            started_at=task.started_at.isoformat() if task.started_at else None,
            finished_at=task.finished_at.isoformat() if task.finished_at else None,
            created_at=task.created_at.isoformat() if task.created_at else "",
        )
