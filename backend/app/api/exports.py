from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.export_service import export_video_md, export_part_md

router = APIRouter(prefix="/api/exports", tags=["导出"])


@router.get("/videos/{video_id}.md")
def download_video_md(
    video_id: int,
    include_transcript: bool = Query(True),
    include_chapters: bool = Query(True),
    include_qa: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """导出全视频 Markdown"""
    md = export_video_md(
        db, video_id,
        include_transcript=include_transcript,
        include_chapters=include_chapters,
        include_qa=include_qa,
    )
    return PlainTextResponse(content=md, media_type="text/markdown; charset=utf-8")


@router.get("/parts/{part_id}.md")
def download_part_md(
    part_id: int,
    include_transcript: bool = Query(True),
    include_chapters: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """导出单 P Markdown"""
    md = export_part_md(
        db, part_id,
        include_transcript=include_transcript,
        include_chapters=include_chapters,
    )
    return PlainTextResponse(content=md, media_type="text/markdown; charset=utf-8")
