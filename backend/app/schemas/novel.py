from datetime import datetime
from pydantic import BaseModel


class NovelCreate(BaseModel):
    title: str = "未命名小说"
    description: str | None = None
    outline: str = ""


class NovelUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    outline: str | None = None


class NovelResponse(BaseModel):
    id: int
    title: str
    description: str | None
    outline: str = ""
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChapterStats(BaseModel):
    id: int
    title: str
    status: str
    word_count: int
    target_words: int | None = None
    completion_rate: float


class NovelStatsResponse(BaseModel):
    novel_id: int
    total_words: int
    chapter_count: int
    done_chapter_count: int
    target_words_total: int
    completion_rate: float
    updated_at: datetime | None = None
    chapters: list[ChapterStats]


class ConsistencyCheckRequest(BaseModel):
    settings_id: int
    scope: str = "recent"
    chapter_id: int | None = None


class WorkspaceResponse(BaseModel):
    novel: NovelResponse
    stats: NovelStatsResponse
    chapters: list[dict]
    recent_timeline_events: list[dict]
    unresolved_checks: list[dict]
