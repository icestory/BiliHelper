"""ASR Provider 抽象接口"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ASRSegment:
    start_time: float
    end_time: float
    text: str
    confidence: float | None = None


class ASRProvider(ABC):
    """语音识别抽象接口"""

    @abstractmethod
    def transcribe(self, audio_path: str) -> list[ASRSegment]:
        """
        对音频文件执行语音识别

        Args:
            audio_path: 音频文件路径（wav/mp3，mono）

        Returns:
            带时间戳的识别结果列表

        Raises:
            RuntimeError: 识别失败
        """
        ...
