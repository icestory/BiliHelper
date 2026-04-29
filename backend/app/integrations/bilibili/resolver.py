"""
B 站链接解析器
负责：链接归一化、BV/AV 提取、短链展开、分 P 参数提取
"""
import re
from dataclasses import dataclass

import httpx

# 支持的链接格式
_BV_PATTERN = re.compile(r"(?:bilibili\.com/video/|b23\.tv/)?(BV[a-zA-Z0-9]{10})")
_AV_PATTERN = re.compile(r"(?:bilibili\.com/video/)?av(\d+)", re.IGNORECASE)
_SHORT_LINK_PATTERN = re.compile(r"https?://b23\.tv/([a-zA-Z0-9]+)")
_P_PARAM = re.compile(r"[?&]p=(\d+)")


@dataclass
class VideoRef:
    """解析后的视频引用"""
    bvid: str | None = None
    aid: int | None = None
    page_no: int = 1  # 分 P 序号，从 1 开始
    source_url: str | None = None  # 规范化的长链接

    @property
    def is_valid(self) -> bool:
        return self.bvid is not None or self.aid is not None


def _extract_url(text: str) -> str | None:
    """从文本中提取 B 站 URL"""
    patterns = [
        r"https?://www\.bilibili\.com/video/[^\s]+",
        r"https?://b23\.tv/[^\s]+",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(0)
    return None


def _expand_short_link(short_url: str) -> str | None:
    """展开 b23.tv 短链接"""
    try:
        resp = httpx.head(short_url, follow_redirects=False, timeout=10)
        # b23.tv 返回 302
        location = resp.headers.get("location", "")
        if location:
            # 去掉 ?spm_id_from=... 等追踪参数
            return location.split("?")[0]
    except Exception:
        pass
    return None


def resolve(text: str) -> VideoRef:
    """
    从用户输入的文本（URL 或分享文本）中提取视频信息

    返回 VideoRef，无效时 bvid/aid 均为 None
    """
    url = _extract_url(text)
    if not url:
        return VideoRef()

    # 短链展开
    if _SHORT_LINK_PATTERN.match(url):
        expanded = _expand_short_link(url)
        if expanded:
            url = expanded

    # 提取 BV 号
    bvid = None
    bv_match = _BV_PATTERN.search(url)
    if bv_match:
        bvid = bv_match.group(1)

    # 提取 AV 号
    aid = None
    av_match = _AV_PATTERN.search(url)
    if av_match:
        aid = int(av_match.group(1))

    # 提取分 P 参数
    page_no = 1
    p_match = _P_PARAM.search(url) or _P_PARAM.search(text)
    if p_match:
        page_no = int(p_match.group(1))

    return VideoRef(bvid=bvid, aid=aid, page_no=page_no, source_url=url)
