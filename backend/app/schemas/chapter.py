from datetime import datetime
from pydantic import BaseModel


class ChapterCreate(BaseModel):
    novel_id: int
    title: str = "未命名章节"
    content: str = ""
    sort_order: int = 0


class ChapterUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    sort_order: int | None = None


class ChapterResponse(BaseModel):
    id: int
    novel_id: int
    title: str
    content: str
    sort_order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
