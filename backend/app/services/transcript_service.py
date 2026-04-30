"""
文案 Chunk 服务
将细粒度 transcript_segments 聚合为 transcript_chunks，用于问答检索
"""

from sqlalchemy.orm import Session

from app.models.transcript import TranscriptSegment, TranscriptChunk

# 每个 chunk 目标 token 数（中文约 1.5 字符/token，取 ~500 tokens → ~3000 字符）
CHUNK_TARGET_CHARS = 3000
CHUNK_OVERLAP_CHARS = 200  # 相邻 chunk 之间的重叠字符数


def estimate_tokens(text: str) -> int:
    """粗略估算 token 数：英文 ~4 chars/token，中文 ~1.5 chars/token"""
    return max(1, len(text) // 3)


def build_chunks(db: Session, part_id: int) -> int:
    """
    为指定分 P 构建 transcript_chunks
    先删旧数据再重建（幂等操作）

    Returns:
        创建的 chunk 数量
    """
    # 清除旧 chunk
    db.query(TranscriptChunk).filter(TranscriptChunk.video_part_id == part_id).delete()

    # 获取所有 segments
    segments = (
        db.query(TranscriptSegment)
        .filter(TranscriptSegment.video_part_id == part_id)
        .order_by(TranscriptSegment.sequence_no)
        .all()
    )

    if not segments:
        return 0

    chunks = []
    current_texts: list[str] = []
    current_len = 0
    current_start = segments[0].start_time
    overlap_buffer = ""

    for seg in segments:
        seg_text = seg.text.strip()
        if not seg_text:
            continue

        if current_len + len(seg_text) > CHUNK_TARGET_CHARS and current_texts:
            # 完成当前 chunk
            full_text = " ".join(current_texts)
            chunks.append({
                "text": full_text,
                "start_time": current_start,
                "end_time": seg.start_time,
                "token_count": estimate_tokens(full_text),
            })

            # 重叠：保留最后 CHUNK_OVERLAP_CHARS 作为下一个 chunk 的上下文
            overlap = ""
            if len(full_text) > CHUNK_OVERLAP_CHARS:
                overlap = full_text[-CHUNK_OVERLAP_CHARS:]
            current_texts = [overlap] if overlap else []
            current_len = len(overlap)
            current_start = seg.start_time

        current_texts.append(seg_text)
        current_len += len(seg_text)

    # 最后一个 chunk
    if current_texts:
        full_text = " ".join(current_texts)
        chunks.append({
            "text": full_text,
            "start_time": current_start,
            "end_time": segments[-1].end_time,
            "token_count": estimate_tokens(full_text),
        })

    # 写入数据库
    for i, ch in enumerate(chunks):
        tc = TranscriptChunk(
            video_part_id=part_id,
            start_time=ch["start_time"],
            end_time=ch["end_time"],
            text=ch["text"],
            token_count=ch["token_count"],
            meta={"sequence": i + 1, "source": "auto_chunk"},
        )
        db.add(tc)

    db.commit()
    return len(chunks)
