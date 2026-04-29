from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.video import VideoParseRequest, VideoParseResponse, VideoHistoryResponse, VideoDetailResponse
from app.services.video_service import VideoService

router = APIRouter(prefix="/api/videos", tags=["视频"])


@router.post("/parse", response_model=VideoParseResponse)
def parse_video(body: VideoParseRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """解析 B 站链接，返回视频信息和分 P 列表"""
    return VideoService(db).parse(body.url)


@router.get("/history", response_model=VideoHistoryResponse)
def get_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None, description="搜索关键词"),
    owner: str | None = Query(None, description="UP 主名称"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的视频分析历史"""
    return VideoService(db).get_history(current_user.id, page=page, page_size=page_size, q=q, owner=owner)


@router.get("/{video_id}", response_model=VideoDetailResponse)
def get_video(video_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取视频详情和分 P 列表"""
    return VideoService(db).get_video_detail(video_id)


@router.delete("/{video_id}/history", status_code=204)
def delete_video_history(
    video_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除视频分析历史"""
    VideoService(db).delete_history(current_user.id, video_id)
