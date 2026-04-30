"""
视频分析 Celery 异步任务
流程：获取字幕 → 保存 transcript → LLM 总结/章节 → 保存结果
"""
from datetime import datetime, timezone
from pathlib import Path

from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.security import decrypt_api_key
from app.models.task import AnalysisTask, PartAnalysisTask
from app.models.transcript import TranscriptSegment
from app.models.summary import PartSummary, Chapter
from app.models.user import ApiCredential
from app.repositories import video_repository
from app.integrations.bilibili.subtitles import get_subtitles, check_subtitle_available
from app.integrations.bilibili.audio import extract_audio, cleanup_audio
from app.integrations.llm import OpenAICompatibleProvider
from app.integrations.asr import OpenAIASRProvider, ASRSegment


def _utcnow():
    return datetime.now(timezone.utc)


def _load_prompt(name: str) -> str:
    """加载 prompt 模板文件"""
    prompt_dir = Path(__file__).parent.parent.parent / "prompts"
    path = prompt_dir / f"{name}.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _get_llm_provider(db, user_id: int) -> tuple[OpenAICompatibleProvider, str, str]:
    """获取用户的默认 LLM provider，返回 (provider, provider_name, model_name)"""
    cred = (
        db.query(ApiCredential)
        .filter(ApiCredential.user_id == user_id, ApiCredential.is_default == True)  # noqa: E712
        .first()
    )
    if not cred:
        cred = db.query(ApiCredential).filter(ApiCredential.user_id == user_id).first()
    if not cred:
        raise ValueError("未配置大模型 API Key，请先在设置中配置")

    api_key = decrypt_api_key(cred.api_key_encrypted)
    provider = OpenAICompatibleProvider(
        api_key=api_key,
        base_url=cred.api_base_url,
        default_model=cred.default_model,
    )
    return provider, cred.provider, cred.default_model or "unknown"


def _build_transcript_text(segments: list) -> str:
    """构建给 LLM 的文案文本（带时间戳）"""
    lines = []
    for seg in segments:
        mins = int(seg.start_time // 60)
        secs = int(seg.start_time % 60)
        lines.append(f"[{mins:02d}:{secs:02d}] {seg.text}")
    return "\n".join(lines)


def _chunk_transcript(segments: list, max_chars: int = 8000) -> list[list]:
    """将长文案切分为多个 chunk，每个不超过 max_chars 字符"""
    chunks = []
    current = []
    current_len = 0

    for seg in segments:
        seg_len = len(seg.text)
        if current_len + seg_len > max_chars and current:
            chunks.append(current)
            current = []
            current_len = 0
        current.append(seg)
        current_len += seg_len

    if current:
        chunks.append(current)

    return chunks


def _save_transcript(db, part_id: int, segments: list, source: str) -> None:
    """保存字幕/ASR 段落到数据库"""
    for i, seg in enumerate(segments):
        ts = TranscriptSegment(
            video_part_id=part_id,
            source=source,
            start_time=seg.start_time,
            end_time=seg.end_time,
            text=seg.text,
            sequence_no=i + 1,
        )
        db.add(ts)
    db.commit()


def _save_summary(db, part_id: int, data: dict, provider: str, model: str, prompt_version: str) -> None:
    """保存总结到数据库"""
    ps = PartSummary(
        video_part_id=part_id,
        summary=data.get("summary", ""),
        detailed_summary=data.get("detailed_summary", ""),
        key_points=data.get("key_points", []),
        model_provider=provider,
        model_name=model,
        prompt_version=prompt_version,
    )
    db.add(ps)
    db.commit()


def _save_chapters(db, part_id: int, chapters: list[dict]) -> None:
    """保存章节到数据库"""
    for i, ch in enumerate(chapters):
        c = Chapter(
            video_part_id=part_id,
            start_time=ch.get("start_time", 0),
            end_time=ch.get("end_time"),
            title=ch.get("title", ""),
            description=ch.get("description", ""),
            keywords=ch.get("keywords", []),
            sequence_no=i + 1,
        )
        db.add(c)
    db.commit()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def start_analysis(self, task_id: int):
    """主分析任务：处理一个分析任务的所有分 P"""
    db = SessionLocal()

    try:
        task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
        if not task:
            return

        # 更新任务状态为 running
        task.status = "running"
        task.started_at = _utcnow()
        db.commit()

        # 获取子任务
        subs = db.query(PartAnalysisTask).filter(
            PartAnalysisTask.analysis_task_id == task_id
        ).all()
        total = len(subs)

        # 获取 LLM provider
        try:
            provider, llm_provider_name, llm_model = _get_llm_provider(db, task.user_id)
        except ValueError as e:
            task.status = "failed"
            task.error_message = str(e)
            db.commit()
            return

        parts = video_repository.get_parts_by_video(db, task.video_id)
        part_map = {p.id: p for p in parts}
        video = video_repository.get_video_by_id(db, task.video_id)

        completed = 0
        prompt_text = _load_prompt("summary_chapters_v1")
        if not prompt_text.strip():
            task.status = "failed"
            task.error_message = "系统提示词模板缺失或为空"
            db.commit()
            return

        for sub in subs:
            part = part_map.get(sub.video_part_id)
            if not part or not video:
                continue

            try:
                # Step 1: 获取字幕
                sub.status = "fetching_subtitle"
                sub.started_at = _utcnow()
                db.commit()

                segments, source = get_subtitles(video.bvid, part.cid or 0)

                if not segments:
                    # ASR 兜底：提取临时音频 → 语音识别
                    sub.status = "extracting_audio"
                    sub.progress = 10
                    db.commit()

                    audio_path = None
                    try:
                        audio_path = extract_audio(video.bvid, part.cid or 0, part.page_no)

                        sub.status = "transcribing"
                        sub.progress = 25
                        db.commit()

                        # 获取 ASR provider（优先用 OpenAI STT，后续可配置）
                        asr_provider = _get_asr_provider(db, task.user_id)
                        asr_segments = asr_provider.transcribe(audio_path)

                        # 转换为统一格式
                        segments = []
                        for i, seg in enumerate(asr_segments):
                            if not seg.text.strip():
                                continue
                            from app.integrations.bilibili.subtitles import SubtitleSegment
                            segments.append(SubtitleSegment(
                                start_time=seg.start_time,
                                end_time=seg.end_time,
                                text=seg.text.strip(),
                            ))

                        if len(segments) < 3:
                            sub.status = "failed"
                            sub.error_message = "ASR 识别结果过短，可能音频质量不佳"
                            db.commit()
                            continue

                        source = "asr"
                    finally:
                        if audio_path:
                            cleanup_audio(audio_path)

                # Step 2: 保存 transcript
                _save_transcript(db, sub.video_part_id, segments, source)
                sub.transcript_source = source
                sub.progress = 40
                db.commit()

                # Step 3: LLM 总结
                sub.status = "summarizing"
                db.commit()

                llm = provider
                chunks = _chunk_transcript(segments)

                if len(chunks) == 1:
                    # 短文案：直接生成总结
                    transcript_text = _build_transcript_text(segments)
                    result = llm.chat_json(
                        system_prompt=prompt_text,
                        user_message=f"以下是视频「{part.title or video.title}」的文案，请分析：\n\n{transcript_text}",
                    )
                else:
                    # 长文案：逐 chunk 局部摘要后合并
                    chunk_summaries = []
                    for i, chunk in enumerate(chunks):
                        chunk_text = _build_transcript_text(chunk)
                        partial = llm.chat_json(
                            system_prompt="请对以下视频文案片段生成摘要和关键要点，输出JSON格式：{\"summary\": \"...\", \"key_points\": [...]}",
                            user_message=f"片段 {i + 1}/{len(chunks)}：\n\n{chunk_text}",
                        )
                        chunk_summaries.append(partial)

                    # 合并各 chunk 摘要生成最终结果
                    merged = "\n\n".join(
                        f"片段 {i+1} 摘要：{cs.get('summary', '')}\n要点：{'; '.join(cs.get('key_points', []))}"
                        for i, cs in enumerate(chunk_summaries)
                    )
                    result = llm.chat_json(
                        system_prompt=prompt_text,
                        user_message=f"视频「{part.title or video.title}」各片段分析结果如下，请整合生成完整的总结和章节：\n\n{merged}",
                    )

                # Step 4: 校验并保存结果
                _validate_result(result)
                _save_summary(db, sub.video_part_id, result,
                              provider=llm_provider_name,
                              model=llm_model,
                              prompt_version="summary_chapters_v1")
                _save_chapters(db, sub.video_part_id, result.get("chapters", []))

                sub.status = "completed"
                sub.progress = 100
                sub.finished_at = _utcnow()
                completed += 1
                db.commit()

            except Exception as e:
                sub.status = "failed"
                sub.error_message = str(e)[:500]
                sub.finished_at = _utcnow()
                db.commit()

        # 全视频总结（所有分P完成且有至少一个成功时）
        if completed > 0 and total > 0:
            try:
                _generate_video_summary(db, task.video_id, task.user_id)
            except Exception:
                pass  # 视频总结失败不影响任务整体状态

        # 更新总任务状态
        if completed == total:
            task.status = "completed"
            task.progress = 100
        elif completed > 0:
            task.status = "partial_failed"
            task.progress = int(completed / total * 100) if total else 0
        else:
            task.status = "failed"
            task.error_message = "所有分 P 分析均失败"

        task.finished_at = _utcnow()
        db.commit()

    except Exception as e:
        # 整体任务异常 — 尝试记录失败状态
        try:
            task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
            if task:
                task.status = "failed"
                task.error_message = str(e)[:500]
                task.finished_at = _utcnow()
                db.commit()
        except Exception:
            db.rollback()
        raise self.retry(exc=e)

    finally:
        db.close()


def _get_cred(db, user_id: int) -> ApiCredential | None:
    return db.query(ApiCredential).filter(
        ApiCredential.user_id == user_id, ApiCredential.is_default == True  # noqa: E712
    ).first()


def _get_asr_provider(db, user_id: int):
    """获取用户的 ASR provider，默认使用 OpenAI STT"""
    cred = _get_cred(db, user_id)
    if not cred:
        raise ValueError("未配置大模型 API Key")

    api_key = decrypt_api_key(cred.api_key_encrypted)
    asr_model = cred.default_asr_model or "whisper-1"

    return OpenAIASRProvider(
        api_key=api_key,
        base_url=cred.api_base_url,
        model=asr_model,
    )


def _generate_video_summary(db, video_id: int, user_id: int):
    """生成全视频总览总结（聚合各分P总结）"""
    from app.models.summary import PartSummary, VideoSummary
    from app.models.video import VideoPart

    # 汇集已完成分 P 的总结
    parts = db.query(VideoPart).filter(VideoPart.video_id == video_id).order_by(VideoPart.page_no).all()
    part_summaries = {}
    for part in parts:
        ps = (
            db.query(PartSummary)
            .filter(PartSummary.video_part_id == part.id)
            .order_by(PartSummary.id.desc())
            .first()
        )
        if ps and ps.summary:
            part_summaries[str(part.page_no)] = ps.summary

    if not part_summaries:
        return

    provider, provider_name, model_name = _get_llm_provider(db, user_id)
    prompt = _load_prompt("video_summary_v1")
    if not prompt.strip():
        return

    parts_text = "\n".join(
        f"P{pn}: {summary}" for pn, summary in sorted(part_summaries.items(), key=lambda x: int(x[0]))
    )

    result = provider.chat_json(
        system_prompt=prompt,
        user_message=f"以下是一个视频各分P的总结，请生成全视频总览：\n\n{parts_text}",
    )

    vs = VideoSummary(
        video_id=video_id,
        summary=result.get("summary", ""),
        detailed_summary=result.get("detailed_summary", ""),
        part_overview=result.get("part_overview", {}),
        key_points=result.get("key_points", []),
        model_provider=provider_name,
        model_name=model_name,
        prompt_version="video_summary_v1",
    )
    db.add(vs)
    db.commit()


def _validate_result(result: dict) -> None:
    """校验 LLM 输出结构"""
    if not isinstance(result, dict):
        raise ValueError("LLM 输出不是有效的 JSON 对象")
    if "summary" not in result:
        raise ValueError("LLM 输出缺少 summary 字段")
    if "chapters" in result:
        chapters = result["chapters"]
        if not isinstance(chapters, list):
            raise ValueError("chapters 字段不是数组")

        prev_end = 0
        for ch in chapters:
            if not isinstance(ch, dict):
                raise ValueError("章节项不是有效的 JSON 对象")
            st = ch.get("start_time", 0)
            if st < prev_end:
                raise ValueError(f"章节时间未递增: start_time={st} < prev_end={prev_end}")
            prev_end = ch.get("end_time") or st  # 防御 LLM 返回 null
