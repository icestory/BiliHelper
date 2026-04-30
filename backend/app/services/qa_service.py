"""
问答服务
关键词检索 + LLM 问答 + 引用生成
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.qa import QASession, QAMessage
from app.models.transcript import TranscriptChunk
from app.models.summary import PartSummary, Chapter, VideoSummary
from app.models.video import VideoPart
from app.core.security import decrypt_api_key
from app.models.user import ApiCredential
from app.integrations.llm import OpenAICompatibleProvider


QA_PROMPT = """你是一个视频内容问答助手。请根据提供的视频信息回答用户问题。

要求：
1. 基于提供的总结和文案片段回答问题，不要编造信息。
2. 在回答中引用相关的文案片段，格式为 [时间: mm:ss]。
3. 如果提供的信息不足以回答问题，请明确说明。
4. 回答应简洁清晰。

必须严格以 JSON 格式输出，格式如下：
{{"answer": "你的回答内容，包含 [时间: mm:ss] 引用"}}

可用信息：
{context}"""


def _search_chunks(db: Session, part_ids: list[int], query: str, top_k: int = 5) -> list[TranscriptChunk]:
    """简单关键词匹配检索"""
    keywords = query.split()
    results = []

    for pid in part_ids:
        chunks = db.query(TranscriptChunk).filter(TranscriptChunk.video_part_id == pid).all()
        for ch in chunks:
            score = sum(1 for kw in keywords if kw.lower() in ch.text.lower())
            if score > 0:
                results.append((ch, score))

    results.sort(key=lambda x: x[1], reverse=True)
    return [r[0] for r in results[:top_k]]


def _format_time(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


def _build_context(db: Session, part_ids: list[int], video_id: int, question: str) -> str:
    """构建 QA 上下文"""
    parts_text = []

    # 1. 全视频总结
    vs = db.query(VideoSummary).filter(VideoSummary.video_id == video_id).order_by(VideoSummary.id.desc()).first()
    if vs and vs.summary:
        parts_text.append(f"【全视频总结】\n{vs.summary}")

    # 2. 各 P 总结 + 章节
    for pid in part_ids:
        part = db.query(VideoPart).filter(VideoPart.id == pid).first()
        part_title = part.title if part else f"P{pid}"

        ps = db.query(PartSummary).filter(PartSummary.video_part_id == pid).order_by(PartSummary.id.desc()).first()
        if ps and ps.summary:
            parts_text.append(f"【{part_title} 总结】\n{ps.summary}")

        chapters = db.query(Chapter).filter(Chapter.video_part_id == pid).order_by(Chapter.sequence_no).all()
        if chapters:
            ch_text = "\n".join(f"- {_format_time(c.start_time)} {c.title}: {c.description or ''}" for c in chapters)
            parts_text.append(f"【{part_title} 章节】\n{ch_text}")

    # 3. 检索相关 chunks
    chunks = _search_chunks(db, part_ids, question, top_k=5)
    if chunks:
        chunk_lines = []
        for ch in chunks:
            part = db.query(VideoPart).filter(VideoPart.id == ch.video_part_id).first()
            pn = f"P{part.page_no}" if part else ""
            chunk_lines.append(f"[{pn} {_format_time(ch.start_time)}] {ch.text}")
        parts_text.append(f"【相关文案片段】\n" + "\n---\n".join(chunk_lines))

    return "\n\n".join(parts_text)


def _get_qa_provider(db: Session, user_id: int) -> OpenAICompatibleProvider:
    from app.services.llm_factory import create_llm_provider
    provider, _, _ = create_llm_provider(db, user_id)
    return provider


class QAService:
    def __init__(self, db: Session):
        self.db = db

    def create_session(self, user_id: int, video_id: int, scope: str = "video",
                       part_ids: list[int] | None = None, title: str | None = None) -> QASession:
        session = QASession(
            user_id=user_id,
            video_id=video_id,
            scope=scope,
            selected_part_ids=part_ids,
            title=title,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def ask(self, user_id: int, session_id: int, question: str) -> QAMessage:
        session = self.db.query(QASession).filter(QASession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="问答会话不存在")
        if session.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问此会话")

        # 确定问答范围的分 P
        part_ids = session.selected_part_ids or []
        if not part_ids:
            parts = self.db.query(VideoPart).filter(VideoPart.video_id == session.video_id).all()
            part_ids = [p.id for p in parts]

        # 构建上下文
        context = _build_context(self.db, part_ids, session.video_id, question)

        # 调用 LLM
        provider = _get_qa_provider(self.db, user_id)
        answer = provider.chat_json(
            system_prompt=QA_PROMPT.format(context=context),
            user_message=question,
            temperature=0.3,
            max_tokens=2048,
        )

        # 保存用户问题
        user_msg = QAMessage(session_id=session_id, role="user", content=question)
        self.db.add(user_msg)

        # 构建引用
        citations = self._extract_citations(answer.get("answer", ""), part_ids)

        # 保存助手回答
        assistant_msg = QAMessage(
            session_id=session_id,
            role="assistant",
            content=answer.get("answer", str(answer)),
            citations=citations,
        )
        self.db.add(assistant_msg)
        self.db.commit()
        self.db.refresh(assistant_msg)

        return assistant_msg

    def get_messages(self, user_id: int, session_id: int) -> list[QAMessage]:
        session = self.db.query(QASession).filter(QASession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="问答会话不存在")
        if session.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问此会话")

        return (
            self.db.query(QAMessage)
            .filter(QAMessage.session_id == session_id)
            .order_by(QAMessage.created_at)
            .all()
        )

    def _extract_citations(self, answer: str, part_ids: list[int]) -> list[dict]:
        """从回答中提取引用时间点"""
        import re
        citations = []
        # 匹配 [P1 03:05] 或 [03:05] 格式
        pattern = re.compile(r"\[(?:P(\d+)\s*)?(\d{1,2}:\d{2})(?:\s*-\s*(\d{1,2}:\d{2}))?\]")
        seen = set()

        for match in pattern.finditer(answer):
            page_no = match.group(1)
            start = match.group(2)
            end = match.group(3)

            # 避免重复
            key = f"{page_no}-{start}-{end}"
            if key in seen:
                continue
            seen.add(key)

            # 查找对应 part_id
            part_id = None
            if page_no:
                part = (
                    self.db.query(VideoPart)
                    .filter(VideoPart.id.in_(part_ids), VideoPart.page_no == int(page_no))
                    .first()
                )
                if part:
                    part_id = part.id

            # 解析时间
            def parse_time(t: str) -> float:
                parts = t.split(":")
                return int(parts[0]) * 60 + int(parts[1])

            citations.append({
                "part_id": part_id,
                "page_no": int(page_no) if page_no else None,
                "start_time": parse_time(start),
                "end_time": parse_time(end) if end else parse_time(start) + 10,
                "text": answer[max(0, match.start() - 50):match.end() + 50],
            })

        return citations
