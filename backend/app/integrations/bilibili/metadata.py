"""
B 站视频元信息获取器
通过 B 站公开 API 获取视频信息和分 P 列表
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

BILIBILI_VIDEO_INFO_API = "https://api.bilibili.com/x/web-interface/view"
# 常用请求头，降低被风控概率
_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.bilibili.com/",
}


@dataclass
class VideoMeta:
    bvid: str
    aid: int | None
    title: str
    owner_name: str
    owner_mid: int | None
    cover_url: str | None
    duration: int | None  # 秒
    description: str | None
    published_at: datetime | None
    part_count: int


@dataclass
class PartMeta:
    page_no: int
    cid: int
    title: str
    duration: int | None  # 秒
    source_url: str | None


@dataclass
class VideoInfo:
    video: VideoMeta
    parts: list[PartMeta]


def _build_url(ref) -> str:
    """根据 bvid 或 aid 构造请求 URL"""
    if ref.bvid:
        return f"{BILIBILI_VIDEO_INFO_API}?bvid={ref.bvid}"
    if ref.aid:
        return f"{BILIBILI_VIDEO_INFO_API}?aid={ref.aid}"
    raise ValueError("bvid 或 aid 至少需要一个")


def _parse_response(data: dict[str, Any]) -> VideoInfo:
    """将 B 站 API 返回的 JSON 转换为内部结构"""
    video = VideoMeta(
        bvid=data.get("bvid", ""),
        aid=data.get("aid"),
        title=data.get("title", ""),
        owner_name=(data.get("owner") or {}).get("name", ""),
        owner_mid=(data.get("owner") or {}).get("mid"),
        cover_url=data.get("pic"),
        duration=data.get("duration"),
        description=data.get("desc"),
        published_at=None,  # pubdate 是时间戳，后续处理
        part_count=len(data.get("pages", [])),
    )

    # 处理发布时间
    pubdate = data.get("pubdate")
    if pubdate is not None:
        try:
            video.published_at = datetime.fromtimestamp(float(pubdate), tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            pass  # 无法解析的时间戳保持为 None

    parts = []
    for page in data.get("pages", []):
        parts.append(PartMeta(
            page_no=page.get("page", 1),
            cid=page.get("cid", 0),
            title=page.get("part", video.title),
            duration=page.get("duration"),
            source_url=f"https://www.bilibili.com/video/{video.bvid}?p={page.get('page', 1)}",
        ))

    return VideoInfo(video=video, parts=parts)


def _build_headers(cookies: dict[str, str] | None = None) -> dict[str, str]:
    """构造请求头，可选注入 B 站登录 Cookie"""
    headers = dict(_DEFAULT_HEADERS)
    if cookies:
        cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
        headers["Cookie"] = cookie_str
    return headers


def fetch(video_ref, cookies: dict[str, str] | None = None) -> VideoInfo:
    """
    根据 VideoRef 获取视频元信息和分 P 列表

    Args:
        cookies: 可选的 B 站 Cookie dict（SESSDATA, bili_jct, buvid3），用于海外访问或风控绕过

    Raises:
        httpx.HTTPError: 网络请求失败
        ValueError: 响应数据无效
    """
    url = _build_url(video_ref)
    resp = httpx.get(url, headers=_build_headers(cookies), timeout=15)
    resp.raise_for_status()

    body = resp.json()
    if body.get("code") != 0:
        raise ValueError(f"B 站 API 返回错误: code={body.get('code')} message={body.get('message', 'unknown')}")

    data = body.get("data")
    if not data:
        raise ValueError("B 站 API 返回数据为空")

    return _parse_response(data)
