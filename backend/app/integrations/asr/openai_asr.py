"""OpenAI Speech-to-Text (Whisper) Provider"""
import os
import subprocess
import tempfile
import math
from pathlib import Path

import httpx

from app.integrations.asr.base import ASRProvider, ASRSegment


# OpenAI STT 文件大小限制: 25MB
_MAX_FILE_SIZE = 25 * 1024 * 1024


class OpenAIASRProvider(ASRProvider):
    def __init__(self, api_key: str, base_url: str | None = None, model: str = "whisper-1"):
        self.api_key = api_key
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.model = model

    def transcribe(self, audio_path: str) -> list[ASRSegment]:
        # 检查文件大小
        file_size = os.path.getsize(audio_path)

        if file_size <= _MAX_FILE_SIZE:
            return self._transcribe_single(audio_path)

        # 大文件切片处理
        slices = self._split_audio(audio_path, _MAX_FILE_SIZE * 0.9)
        all_segments = []
        time_offset = 0.0

        for i, slice_path in enumerate(slices):
            slice_duration = self._get_audio_duration(slice_path)

            try:
                segs = self._transcribe_single(slice_path, time_offset)
                all_segments.extend(segs)
            except Exception:
                # 单个切片失败不中断整体
                pass

            time_offset += slice_duration

        # 清理切片文件
        for sp in slices:
            try:
                os.remove(sp)
            except OSError:
                pass

        return all_segments

    def _transcribe_single(self, audio_path: str, time_offset: float = 0.0) -> list[ASRSegment]:
        url = f"{self.base_url}/audio/transcriptions"

        with open(audio_path, "rb") as f:
            resp = httpx.post(
                url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                files={"file": ("audio.wav", f, "audio/wav")},
                data={"model": self.model, "response_format": "verbose_json"},
                timeout=300,
            )

        resp.raise_for_status()
        data = resp.json()

        segments = []
        for seg in data.get("segments", []):
            segments.append(ASRSegment(
                start_time=time_offset + seg.get("start", 0.0),
                end_time=time_offset + seg.get("end", 0.0),
                text=seg.get("text", "").strip(),
                confidence=seg.get("confidence"),
            ))

        return segments

    def _split_audio(self, audio_path: str, max_size: int) -> list[str]:
        """按文件大小将音频切片（使用 FFmpeg segment）"""
        total_duration = self._get_audio_duration(audio_path)
        if total_duration <= 0:
            return [audio_path]

        file_size = os.path.getsize(audio_path)
        # 估算切片数（按文件大小比例）
        num_slices = max(1, math.ceil(file_size / max_size))
        slice_duration = total_duration / num_slices

        output_dir = tempfile.mkdtemp(prefix="asr_slices_")
        slices = []

        for i in range(num_slices):
            start = i * slice_duration
            output_path = os.path.join(output_dir, f"slice_{i:03d}.wav")
            subprocess.run([
                "ffmpeg", "-i", audio_path,
                "-ss", str(start),
                "-t", str(slice_duration + 2),  # 略微多取 2 秒避免切在句子中间
                "-ac", "1", "-ar", "16000",
                "-f", "wav", "-y",
                output_path,
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            slices.append(output_path)

        return slices

    def _get_audio_duration(self, audio_path: str) -> float:
        """获取音频时长（秒）"""
        import json
        try:
            result = subprocess.run([
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                audio_path,
            ], capture_output=True, text=True, check=True)
            info = json.loads(result.stdout)
            return float(info.get("format", {}).get("duration", 0))
        except Exception:
            return 0
