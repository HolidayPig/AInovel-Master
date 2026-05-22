from datetime import datetime
from pydantic import BaseModel


class TimelineEventCreate(BaseModel):
    novel_id: int
    chapter_id: int | None = None
    title: str = ""
    event_time: str = ""
    summary: str = ""
    characters: str = ""
    sort_order: int = 0


class TimelineEventUpdate(BaseModel):
    chapter_id: int | None = None
    title: str | None = None
    event_time: str | None = None
    summary: str | None = None
    characters: str | None = None
    sort_order: int | None = None


class TimelineEventResponse(BaseModel):
    id: int
    novel_id: int
    chapter_id: int | None
    title: str
    event_time: str
    summary: str
    characters: str
    sort_order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExtractTimelineRequest(BaseModel):
    novel_id: int
    chapter_id: int
    settings_id: int


class TimelineEventCandidate(BaseModel):
    title: str
    event_time: str = ""
    summary: str = ""
    characters: str = ""
    sort_order: int = 0
