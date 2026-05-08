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


def _write_netscape_cookie_file(cookies: dict[str, str]) -> str:
    """将 Cookie dict 写入临时 Netscape 格式文件，供 yt-dlp --cookies 使用"""
    fd, path = tempfile.mkstemp(prefix="bilihelper_cookies_", suffix=".txt")
    with os.fdopen(fd, "w") as f:
        f.write("# Netscape HTTP Cookie File\n")
        # 过期时间设置为 30 天后
        for name, value in cookies.items():
            f.write(f".bilibili.com\tTRUE\t/\tFALSE\t9999999999\t{name}\t{value}\n")
    return path


def extract_audio(bvid: str, cid: int, page_no: int = 1, cookies: dict[str, str] | None = None) -> str:
    """
    提取指定分 P 的音频为 mono 16kHz wav 文件

    Args:
        bvid: BV 号
        cid: 分 P 的 cid
        page_no: 分 P 序号
        cookies: 可选的 B 站 Cookie dict，用于海外访问

    Returns:
        临时音频文件路径

    Raises:
        RuntimeError: 提取失败
    """
    _ensure_temp_dir()

    video_url = f"https://www.bilibili.com/video/{bvid}?p={page_no}"
    output_path = str(TEMP_DIR / f"{bvid}_p{page_no}_{uuid.uuid4().hex[:8]}.wav")
    cookie_file = None
    tmp_audio = str(TEMP_DIR / f"{bvid}_p{page_no}_{uuid.uuid4().hex[:8]}.tmp")

    ytdlp_cmd = [
        "yt-dlp",
        "-f", "bestaudio[filesize<100M]",
        "--max-filesize", "100M",
        "--max-duration", "1800",
        "-o", tmp_audio,
        "--no-playlist",
    ]
    if cookies:
        cookie_file = _write_netscape_cookie_file(cookies)
        ytdlp_cmd.extend(["--cookies", cookie_file])
    ytdlp_cmd.append(video_url)

    try:
        # Step 1: yt-dlp 下载音频到临时文件
        ytdlp_result = subprocess.run(ytdlp_cmd, capture_output=True, timeout=600)
        if ytdlp_result.returncode != 0:
            stderr = ytdlp_result.stderr.decode("utf-8", errors="replace")[-800:]
            raise RuntimeError(f"yt-dlp 下载失败 (exit={ytdlp_result.returncode}): {stderr}")

        if not os.path.exists(tmp_audio) or os.path.getsize(tmp_audio) == 0:
            stderr = ytdlp_result.stderr.decode("utf-8", errors="replace")[-500:]
            raise RuntimeError(f"yt-dlp 输出文件为空: {stderr}")

        # Step 2: ffmpeg 转换为 mono 16kHz wav
        subprocess.run([
            "ffmpeg",
            "-i", tmp_audio,
            "-ac", "1",
            "-ar", "16000",
            "-f", "wav",
            "-y",
            output_path,
        ], check=True, timeout=300, capture_output=True)

    except subprocess.TimeoutExpired:
        raise RuntimeError("音频提取超时")
    finally:
        if cookie_file and os.path.exists(cookie_file):
            os.remove(cookie_file)
        if os.path.exists(tmp_audio):
            os.remove(tmp_audio)

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
