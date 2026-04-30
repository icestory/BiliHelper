"""本地 faster-whisper ASR Provider（可选依赖）

使用前需安装: pip install faster-whisper
首次运行会自动下载模型文件。
"""
import os
import subprocess
import math
import tempfile

from app.integrations.asr.base import ASRProvider, ASRSegment

# 最大单段处理时长（秒），超出自动切片
_MAX_SEGMENT_DURATION = 300  # 5 分钟


class FasterWhisperProvider(ASRProvider):
    def __init__(self, model_size: str = "small", device: str = "cpu", compute_type: str = "int8"):
        """
        Args:
            model_size: 模型大小 tiny/tiny.en/base/base.en/small/small.en/medium/medium.en/large
            device: cpu / cuda
            compute_type: float16 / int8_float16 / int8
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError:
                raise RuntimeError(
                    "faster-whisper 未安装，请运行: pip install faster-whisper\n"
                    "或使用云端 ASR (OpenAI STT) 替代。"
                )
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model

    def transcribe(self, audio_path: str) -> list[ASRSegment]:
        model = self._load_model()

        # 检查时长，长音频切片处理
        duration = self._get_audio_duration(audio_path)

        if duration <= _MAX_SEGMENT_DURATION:
            return self._transcribe_single(audio_path)

        # 切片处理
        slices = self._split_audio(audio_path, duration, _MAX_SEGMENT_DURATION)
        all_segments = []
        time_offset = 0.0

        for i, slice_path in enumerate(slices):
            slice_duration = self._get_audio_duration(slice_path)
            try:
                segs = self._transcribe_single(slice_path, time_offset)
                all_segments.extend(segs)
            except Exception:
                pass
            time_offset += slice_duration

        for sp in slices:
            try:
                os.remove(sp)
            except OSError:
                pass
        try:
            os.rmdir(output_dir)
        except OSError:
            pass

        return all_segments

    def _transcribe_single(self, audio_path: str, time_offset: float = 0.0) -> list[ASRSegment]:
        model = self._load_model()
        segments_iter, _ = model.transcribe(audio_path, beam_size=5)

        segments = []
        for seg in segments_iter:
            if seg.text.strip():
                segments.append(ASRSegment(
                    start_time=time_offset + seg.start,
                    end_time=time_offset + seg.end,
                    text=seg.text.strip(),
                    confidence=seg.avg_logprob,
                ))

        return segments

    def _split_audio(self, audio_path: str, total_duration: float, max_duration: float) -> list[str]:
        num_slices = max(1, math.ceil(total_duration / max_duration))
        slice_duration = total_duration / num_slices

        output_dir = tempfile.mkdtemp(prefix="fwhisper_slices_")
        slices = []

        for i in range(num_slices):
            start = i * slice_duration
            output_path = os.path.join(output_dir, f"slice_{i:03d}.wav")
            subprocess.run([
                "ffmpeg", "-i", audio_path,
                "-ss", str(start),
                "-t", str(slice_duration + 2),
                "-ac", "1", "-ar", "16000",
                "-f", "wav", "-y",
                output_path,
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            slices.append(output_path)

        return slices

    def _get_audio_duration(self, audio_path: str) -> float:
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
