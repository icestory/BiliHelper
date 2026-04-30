"""
Markdown 导出服务
按模板生成全视频或单 P 的 Markdown 文档
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.video import Video, VideoPart
from app.models.transcript import TranscriptSegment
from app.models.summary import PartSummary, Chapter, VideoSummary
from app.models.qa import QASession, QAMessage


def _format_time(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


def export_video_md(db: Session, video_id: int, *,
                    include_transcript: bool = True,
                    include_chapters: bool = True,
                    include_qa: bool = False) -> str:
    """导出全视频 Markdown"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="视频不存在")

    parts = db.query(VideoPart).filter(VideoPart.video_id == video_id).order_by(VideoPart.page_no).all()
    vs = db.query(VideoSummary).filter(VideoSummary.video_id == video_id).order_by(VideoSummary.id.desc()).first()

    md = f"# {video.title}\n\n"
    md += f"- UP 主：{video.owner_name or '未知'}\n"
    md += f"- 链接：{video.source_url}\n"
    md += f"- 分 P 数量：{video.part_count}\n"
    if vs and vs.created_at:
        md += f"- 分析时间：{vs.created_at.isoformat()}\n"
    md += "\n"

    # 全视频总结
    if vs:
        md += "## 全视频总结\n\n"
        if vs.summary:
            md += f"{vs.summary}\n\n"
        if vs.detailed_summary:
            md += f"### 详细总结\n\n{vs.detailed_summary}\n\n"
        if vs.key_points:
            md += "### 全局要点\n\n"
            for kp in vs.key_points:
                md += f"- {kp}\n"
            md += "\n"
        if vs.part_overview:
            md += "### 各分 P 概述\n\n"
            for pn, desc in vs.part_overview.items():
                md += f"- **P{pn}**: {desc}\n"
            md += "\n"

    # 分 P 目录
    md += "## 分 P 目录\n\n"
    for p in parts:
        md += f"- P{p.page_no} {p.title or ''}\n"
    md += "\n"

    # 每个分 P 详情
    for p in parts:
        md += f"## P{p.page_no} {p.title or ''}\n\n"

        ps = db.query(PartSummary).filter(PartSummary.video_part_id == p.id).order_by(PartSummary.id.desc()).first()
        if ps:
            md += "### 摘要\n\n"
            if ps.summary:
                md += f"{ps.summary}\n\n"
            if ps.detailed_summary:
                md += f"### 详细总结\n\n{ps.detailed_summary}\n\n"
            if ps.key_points:
                md += "### 关键要点\n\n"
                for kp in ps.key_points:
                    md += f"- {kp}\n"
                md += "\n"

        if include_chapters:
            chapters = db.query(Chapter).filter(Chapter.video_part_id == p.id).order_by(Chapter.sequence_no).all()
            if chapters:
                md += "### 章节\n\n"
                for ch in chapters:
                    ts = _format_time(ch.start_time)
                    md += f"- **{ts}** {ch.title}"
                    if ch.description:
                        md += f"：{ch.description}"
                    md += "\n"
                md += "\n"

        if include_transcript:
            segments = (
                db.query(TranscriptSegment)
                .filter(TranscriptSegment.video_part_id == p.id)
                .order_by(TranscriptSegment.sequence_no)
                .all()
            )
            if segments:
                md += "### 文案\n\n"
                for seg in segments:
                    md += f"- {_format_time(seg.start_time)} {seg.text}\n"
                md += "\n"

    # 问答记录
    if include_qa:
        sessions = db.query(QASession).filter(QASession.video_id == video_id).order_by(QASession.created_at).all()
        if sessions:
            md += "## 问答记录\n\n"
            for sess in sessions:
                if sess.title:
                    md += f"### {sess.title}\n\n"
                messages = (
                    db.query(QAMessage)
                    .filter(QAMessage.session_id == sess.id)
                    .order_by(QAMessage.created_at)
                    .all()
                )
                for msg in messages:
                    role = "Q" if msg.role == "user" else "A"
                    md += f"**{role}**: {msg.content}\n\n"
                md += "\n"

    return md


def export_part_md(db: Session, part_id: int, *,
                   include_transcript: bool = True,
                   include_chapters: bool = True) -> str:
    """导出单 P Markdown"""
    part = db.query(VideoPart).filter(VideoPart.id == part_id).first()
    if not part:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分 P 不存在")
    video = db.query(Video).filter(Video.id == part.video_id).first()

    md = f"# {video.title if video else ''} — P{part.page_no} {part.title or ''}\n\n"
    if video:
        md += f"- UP 主：{video.owner_name or '未知'}\n"
        md += f"- 链接：{part.source_url or video.source_url}\n"
    md += "\n"

    ps = db.query(PartSummary).filter(PartSummary.video_part_id == part_id).order_by(PartSummary.id.desc()).first()
    if ps:
        md += "## 摘要\n\n"
        if ps.summary:
            md += f"{ps.summary}\n\n"
        if ps.detailed_summary:
            md += f"### 详细总结\n\n{ps.detailed_summary}\n\n"
        if ps.key_points:
            md += "### 关键要点\n\n"
            for kp in ps.key_points:
                md += f"- {kp}\n"
            md += "\n"

    if include_chapters:
        chapters = db.query(Chapter).filter(Chapter.video_part_id == part_id).order_by(Chapter.sequence_no).all()
        if chapters:
            md += "## 章节\n\n"
            for ch in chapters:
                md += f"- **{_format_time(ch.start_time)}** {ch.title}"
                if ch.description:
                    md += f"：{ch.description}"
                md += "\n"
            md += "\n"

    if include_transcript:
        segments = (
            db.query(TranscriptSegment)
            .filter(TranscriptSegment.video_part_id == part_id)
            .order_by(TranscriptSegment.sequence_no)
            .all()
        )
        if segments:
            md += "## 文案\n\n"
            for seg in segments:
                md += f"- {_format_time(seg.start_time)} {seg.text}\n"

    return md
