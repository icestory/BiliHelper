from pydantic import BaseModel


class AnalysisTaskCreate(BaseModel):
    video_id: int
    part_ids: list[int] | None = None  # None 表示全部分 P
    force_reanalyze: bool = False


class PartAnalysisStatus(BaseModel):
    id: int
    video_part_id: int
    page_no: int | None = None
    part_title: str | None = None
    status: str
    transcript_source: str | None = None
    progress: int
    error_message: str | None = None


class AnalysisTaskResponse(BaseModel):
    id: int
    video_id: int
    status: str  # waiting / running / completed / failed / partial_failed
    progress: int  # 0-100
    error_message: str | None = None
    parts: list[PartAnalysisStatus]
    started_at: str | None = None
    finished_at: str | None = None
    created_at: str


class PartAnalysisDetail(BaseModel):
    id: int
    video_part_id: int
    status: str
    transcript_source: str | None = None
    transcript_segments: list[dict] | None = None  # [{start_time, end_time, text, source}]
    summary: dict | None = None  # {summary, detailed_summary, key_points}
    chapters: list[dict] | None = None  # [{start_time, end_time, title, description, keywords}]
    error_message: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
