from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.video import VideoParseRequest, VideoParseResponse, VideoHistoryResponse, VideoDetailResponse, VideoSummaryResponse
from app.services.video_service import VideoService
from app.models.summary import VideoSummary

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


@router.get("/{video_id}/summary", response_model=VideoSummaryResponse)
def get_video_summary(video_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取视频的全视频总览总结"""
    vs = db.query(VideoSummary).filter(VideoSummary.video_id == video_id).order_by(VideoSummary.id.desc()).first()
    if not vs:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="全视频总结尚未生成")
    return VideoSummaryResponse(
        id=vs.id,
        video_id=vs.video_id,
        summary=vs.summary,
        detailed_summary=vs.detailed_summary,
        part_overview=vs.part_overview,
        key_points=vs.key_points,
        model_provider=vs.model_provider,
        model_name=vs.model_name,
        prompt_version=vs.prompt_version,
        created_at=vs.created_at.isoformat() if vs.created_at else None,
    )
