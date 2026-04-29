from pydantic import BaseModel


class VideoParseRequest(BaseModel):
    url: str


class PartResponse(BaseModel):
    id: int | None = None
    page_no: int
    cid: int | None = None
    title: str | None = None
    duration: int | None = None
    source_url: str | None = None


class VideoInfoResponse(BaseModel):
    id: int | None = None
    bvid: str
    aid: int | None = None
    title: str
    owner_name: str | None = None
    cover_url: str | None = None
    duration: int | None = None
    description: str | None = None
    published_at: str | None = None
    part_count: int
    source_url: str | None = None


class VideoParseResponse(BaseModel):
    video: VideoInfoResponse
    parts: list[PartResponse]
    already_analyzed: bool = False


class VideoHistoryItem(BaseModel):
    id: int
    bvid: str
    title: str
    owner_name: str | None = None
    cover_url: str | None = None
    part_count: int
    created_at: str


class VideoHistoryResponse(BaseModel):
    items: list[VideoHistoryItem]
    total: int
    page: int
    page_size: int


class VideoDetailResponse(BaseModel):
    id: int
    bvid: str
    aid: int | None = None
    title: str
    owner_name: str | None = None
    cover_url: str | None = None
    source_url: str
    duration: int | None = None
    description: str | None = None
    published_at: str | None = None
    part_count: int
    parts: list[PartResponse]
    created_at: str
