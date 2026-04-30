from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.integrations.bilibili.resolver import resolve
from app.integrations.bilibili.metadata import fetch as fetch_metadata
from app.repositories import video_repository
from app.schemas.video import (
    VideoInfoResponse,
    PartResponse,
    VideoParseResponse,
    VideoHistoryItem,
    VideoHistoryResponse,
    VideoDetailResponse,
)


class VideoService:
    def __init__(self, db: Session):
        self.db = db

    def parse(self, url: str, user_id: int | None = None) -> VideoParseResponse:
        # 1. 解析链接
        ref = resolve(url)
        if not ref.is_valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无法识别 B 站链接，请检查 URL 格式")

        # 2. 获取 B 站元信息
        try:
            info = fetch_metadata(ref)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"获取 B 站视频信息失败: {str(e)}")

        # 3. 检查数据库是否已有该视频
        existing_video = video_repository.get_video_by_bvid(self.db, info.video.bvid)
        already_analyzed = False

        if existing_video:
            video = video_repository.update_video(self.db, existing_video,
                title=info.video.title,
                owner_name=info.video.owner_name,
                cover_url=info.video.cover_url,
                duration=info.video.duration,
                description=info.video.description,
                published_at=info.video.published_at,
                part_count=info.video.part_count,
            )
            # 检查是否有分析任务
            from app.models.task import AnalysisTask
            query = self.db.query(AnalysisTask).filter(AnalysisTask.video_id == video.id)
            if user_id is not None:
                query = query.filter(AnalysisTask.user_id == user_id)
            already_analyzed = query.count() > 0
        else:
            video = video_repository.create_video(self.db,
                bvid=info.video.bvid,
                aid=info.video.aid,
                title=info.video.title,
                owner_name=info.video.owner_name,
                owner_mid=info.video.owner_mid,
                cover_url=info.video.cover_url,
                source_url=ref.source_url or f"https://www.bilibili.com/video/{info.video.bvid}",
                duration=info.video.duration,
                description=info.video.description,
                published_at=info.video.published_at,
                part_count=info.video.part_count,
            )

        # 4. 同步分 P 信息
        existing_parts = video_repository.get_parts_by_video(self.db, video.id)
        existing_cids = {p.cid for p in existing_parts}

        parts_response = []
        for part_meta in info.parts:
            if part_meta.cid not in existing_cids:
                part = video_repository.create_video_part(self.db,
                    video_id=video.id,
                    page_no=part_meta.page_no,
                    cid=part_meta.cid,
                    title=part_meta.title,
                    duration=part_meta.duration,
                    source_url=part_meta.source_url,
                )
            else:
                part = next(p for p in existing_parts if p.cid == part_meta.cid)

            parts_response.append(PartResponse(
                id=part.id,
                page_no=part.page_no,
                cid=part.cid,
                title=part.title,
                duration=part.duration,
                source_url=part.source_url,
            ))

        return VideoParseResponse(
            video=VideoInfoResponse(
                id=video.id,
                bvid=video.bvid,
                aid=video.aid,
                title=video.title,
                owner_name=video.owner_name,
                cover_url=video.cover_url,
                duration=video.duration,
                description=video.description,
                published_at=video.published_at,
                part_count=video.part_count,
                source_url=video.source_url,
            ),
            parts=parts_response,
            already_analyzed=already_analyzed,
        )

    def get_history(self, user_id: int, page: int = 1, page_size: int = 20,
                    q: str | None = None, owner: str | None = None) -> VideoHistoryResponse:
        videos = video_repository.get_video_history(self.db, user_id, page=page, page_size=page_size, q=q, owner=owner)
        total = video_repository.count_video_history(self.db, user_id, q=q, owner=owner)

        items = [
            VideoHistoryItem(
                id=v.id,
                bvid=v.bvid,
                title=v.title,
                owner_name=v.owner_name,
                cover_url=v.cover_url,
                part_count=v.part_count,
                created_at=v.created_at.isoformat() if v.created_at else "",
            )
            for v in videos
        ]

        return VideoHistoryResponse(items=items, total=total, page=page, page_size=page_size)

    def get_video_detail(self, video_id: int) -> VideoDetailResponse:
        video = video_repository.get_video_by_id(self.db, video_id)
        if not video:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="视频不存在")

        parts = video_repository.get_parts_by_video(self.db, video_id)
        return VideoDetailResponse(
            id=video.id,
            bvid=video.bvid,
            aid=video.aid,
            title=video.title,
            owner_name=video.owner_name,
            cover_url=video.cover_url,
            source_url=video.source_url,
            duration=video.duration,
            description=video.description,
            published_at=video.published_at.isoformat() if video.published_at else None,
            part_count=video.part_count,
            parts=[PartResponse(
                id=p.id,
                page_no=p.page_no,
                cid=p.cid,
                title=p.title,
                duration=p.duration,
                source_url=p.source_url,
            ) for p in parts],
            created_at=video.created_at.isoformat() if video.created_at else "",
        )

    def delete_history(self, user_id: int, video_id: int) -> int:
        return video_repository.delete_video_history(self.db, user_id, video_id)
