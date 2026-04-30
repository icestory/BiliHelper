from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.qa_service import QAService

router = APIRouter(prefix="/api", tags=["问答"])


class CreateSessionRequest(BaseModel):
    title: str | None = None
    scope: str = "video"  # video / selected_parts
    part_ids: list[int] | None = None


class AskRequest(BaseModel):
    question: str


class CitationResponse(BaseModel):
    part_id: int | None = None
    page_no: int | None = None
    start_time: float
    end_time: float | None = None
    text: str | None = None


class MessageResponse(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    citations: list[CitationResponse] | None = None
    created_at: str


class SessionResponse(BaseModel):
    id: int
    video_id: int
    title: str | None = None
    scope: str
    selected_part_ids: list[int] | None = None
    created_at: str


@router.get("/videos/{video_id}/qa-sessions", response_model=list[SessionResponse])
def list_sessions(
    video_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取视频的问答会话列表"""
    sessions = (
        db.query(QASession)
        .filter(QASession.video_id == video_id, QASession.user_id == current_user.id)
        .order_by(QASession.created_at.desc())
        .all()
    )
    return [
        SessionResponse(
            id=s.id,
            video_id=s.video_id,
            title=s.title,
            scope=s.scope,
            selected_part_ids=s.selected_part_ids,
            created_at=s.created_at.isoformat() if s.created_at else "",
        )
        for s in sessions
    ]


@router.post("/videos/{video_id}/qa-sessions", response_model=SessionResponse, status_code=201)
def create_session(
    video_id: int,
    body: CreateSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建问答会话"""
    from app.models.qa import QASession
    svc = QAService(db)
    session = svc.create_session(
        user_id=current_user.id,
        video_id=video_id,
        scope=body.scope,
        part_ids=body.part_ids,
        title=body.title,
    )
    return SessionResponse(
        id=session.id,
        video_id=session.video_id,
        title=session.title,
        scope=session.scope,
        selected_part_ids=session.selected_part_ids,
        created_at=session.created_at.isoformat() if session.created_at else "",
    )


@router.get("/qa-sessions/{session_id}/messages", response_model=list[MessageResponse])
def get_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取会话的消息历史"""
    messages = QAService(db).get_messages(current_user.id, session_id)
    return [
        MessageResponse(
            id=m.id,
            session_id=m.session_id,
            role=m.role,
            content=m.content,
            citations=m.citations,
            created_at=m.created_at.isoformat() if m.created_at else "",
        )
        for m in messages
    ]


@router.post("/qa-sessions/{session_id}/messages", response_model=MessageResponse, status_code=201)
def ask_question(
    session_id: int,
    body: AskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """向会话发送问题，返回 AI 回答（含引用）"""
    msg = QAService(db).ask(current_user.id, session_id, body.question)
    return MessageResponse(
        id=msg.id,
        session_id=msg.session_id,
        role=msg.role,
        content=msg.content,
        citations=msg.citations,
        created_at=msg.created_at.isoformat() if msg.created_at else "",
    )
