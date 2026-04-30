"""
临时音频提取器
通过 yt-dlp + FFmpeg 从 B 站视频提取音频，仅用于无字幕时的 ASR
"""
import os
import subprocess
import tempfile
import uuid
from pathlib import Path


# 临时音频存放目录
TEMP_DIR = Path(os.getenv("AUDIO_TEMP_DIR", "/tmp/bilihelper/audio"))


def _ensure_temp_dir():
    TEMP_DIR.mkdir(parents=True, exist_ok=True)


def extract_audio(bvid: str, cid: int, page_no: int = 1) -> str:
    """
    提取指定分 P 的音频为 mono 16kHz wav 文件

    Args:
        bvid: BV 号
        cid: 分 P 的 cid
        page_no: 分 P 序号

    Returns:
        临时音频文件路径

    Raises:
        RuntimeError: 提取失败
    """
    _ensure_temp_dir()

    video_url = f"https://www.bilibili.com/video/{bvid}?p={page_no}"
    output_path = str(TEMP_DIR / f"{bvid}_p{page_no}_{uuid.uuid4().hex[:8]}.wav")

    # yt-dlp 提取音频 → FFmpeg 转换为 mono 16kHz wav
    # 限制最长 30 分钟避免无限下载
    ytdlp_cmd = [
        "yt-dlp",
        "-f", "bestaudio[filesize<100M]",  # 只取音频流，<100MB
        "--max-filesize", "100M",
        "--max-duration", "1800",
        "-o", "-",                          # 输出到 stdout
        video_url,
    ]

    ffmpeg_cmd = [
        "ffmpeg",
        "-i", "pipe:0",                     # 从 stdin 读取
        "-ac", "1",                         # mono
        "-ar", "16000",                     # 16kHz sample rate
        "-f", "wav",                        # wav 格式
        "-y",                               # 覆盖已有文件
        output_path,
    ]

    try:
        ytdlp_proc = subprocess.Popen(
            ytdlp_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        subprocess.run(ffmpeg_cmd, stdin=ytdlp_proc.stdout, check=True, timeout=900)
        # 等待 yt-dlp 进程退出，允许 60 秒清理
        ytdlp_proc.wait(timeout=60)
    except subprocess.TimeoutExpired:
        ytdlp_proc.kill()
        ytdlp_proc.wait(timeout=5)
        raise RuntimeError("音频提取超时（超过 15 分钟）")
    except Exception as e:
        raise RuntimeError(f"音频提取失败: {str(e)}")

    # 验证文件存在且非空
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError("音频提取失败：输出文件为空")

    return output_path


def cleanup_audio(file_path: str) -> None:
    """删除临时音频文件"""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except OSError:
        pass


def cleanup_temp_dir() -> None:
    """清理临时目录中的过期文件"""
    import time
    from app.core.config import settings
    _ensure_temp_dir()
    ttl = settings.TEMP_FILE_TTL_HOURS
    now = time.time()
    for f in TEMP_DIR.glob("*"):
        if f.is_file() and now - f.stat().st_mtime > ttl * 3600:
            try:
                f.unlink()
            except OSError:
                pass
