from datetime import datetime
from pydantic import BaseModel


class CardCreate(BaseModel):
    novel_id: int
    card_type: str
    name: str = ""
    content_json: str = "{}"
    auto_update: bool = False
    tags: str = ""
    importance: int = 2


class CardUpdate(BaseModel):
    card_type: str | None = None
    name: str | None = None
    content_json: str | None = None
    auto_update: bool | None = None
    tags: str | None = None
    importance: int | None = None


class CardResponse(BaseModel):
    id: int
    novel_id: int
    card_type: str
    name: str
    content_json: str
    auto_update: bool
    tags: str = ""
    importance: int = 2
    last_referenced_chapter_id: int | None = None
    last_referenced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
