"""
B 站字幕获取器
获取并标准化 B 站字幕（UP 主上传 > 自动字幕 > AI 字幕）
"""
import httpx
from dataclasses import dataclass

BILIBILI_PLAYER_API = "https://api.bilibili.com/x/player/v2"

_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.bilibili.com/",
}

# 字幕来源优先级
_SUBTITLE_LAN_PRIORITY = [
    "zh-CN", "zh-Hans",  # 简体中文
    "zh-TW", "zh-Hant",  # 繁体中文
    "zh",                # 中文
    "en", "eng",         # 英文
]


@dataclass
class SubtitleSegment:
    start_time: float
    end_time: float
    text: str


def fetch_subtitle_list(bvid: str, cid: int) -> list[dict]:
    """获取视频某 P 的字幕列表"""
    url = f"{BILIBILI_PLAYER_API}?bvid={bvid}&cid={cid}"
    resp = httpx.get(url, headers=_DEFAULT_HEADERS, timeout=15)
    resp.raise_for_status()

    body = resp.json()
    if body.get("code") != 0:
        return []

    subtitle_data = body.get("data", {}).get("subtitle", {})
    return subtitle_data.get("subtitles", [])


def pick_best_subtitle(subtitles: list[dict]) -> dict | None:
    """从字幕列表中按优先级选择最佳字幕"""
    if not subtitles:
        return None

    # 按语言优先级排序，同时优先 UP 主上传字幕
    for lang in _SUBTITLE_LAN_PRIORITY:
        for sub in subtitles:
            sub_lan = sub.get("lan", "")
            if sub_lan == lang:
                return sub

    # 兜底：返回第一个
    return subtitles[0]


def download_and_parse(subtitle_url: str) -> list[SubtitleSegment]:
    """下载并解析 B 站字幕 JSON"""
    if subtitle_url.startswith("//"):
        subtitle_url = "https:" + subtitle_url

    resp = httpx.get(subtitle_url, headers=_DEFAULT_HEADERS, timeout=15)
    resp.raise_for_status()

    data = resp.json()
    segments = []

    for item in data.get("body", []):
        start = item.get("from", 0.0)
        end = item.get("to", 0.0)
        content = item.get("content", "").strip()

        if not content:
            continue

        segments.append(SubtitleSegment(
            start_time=start,
            end_time=end,
            text=content,
        ))

    return segments


def get_subtitles(bvid: str, cid: int) -> tuple[list[SubtitleSegment], str | None]:
    """
    获取视频分 P 的标准化学幕

    Returns:
        (segments, source) — source 为 "bili_subtitle" 或 None（无可用字幕）
    """
    try:
        subtitle_list = fetch_subtitle_list(bvid, cid)
    except Exception:
        return [], None

    best = pick_best_subtitle(subtitle_list)
    if not best:
        return [], None

    subtitle_url = best.get("subtitle_url", "")
    if not subtitle_url:
        return [], None

    try:
        segments = download_and_parse(subtitle_url)
    except Exception:
        return [], None

    # 校验字幕内容质量
    if len(segments) < 3:
        return [], None

    total_text = "".join(s.text for s in segments)
    if len(total_text) < 30:  # 字幕内容过短
        return [], None

    return segments, "bili_subtitle"


def check_subtitle_available(bvid: str, cid: int) -> bool:
    """快速检查是否有可用字幕（不下载内容）"""
    try:
        subtitle_list = fetch_subtitle_list(bvid, cid)
        return pick_best_subtitle(subtitle_list) is not None
    except Exception:
        return False
