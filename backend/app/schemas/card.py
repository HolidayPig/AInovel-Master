from datetime import datetime
from pydantic import BaseModel


class CardCreate(BaseModel):
    novel_id: int
    card_type: str
    name: str = ""
    content_json: str = "{}"
    auto_update: bool = False


class CardUpdate(BaseModel):
    card_type: str | None = None
    name: str | None = None
    content_json: str | None = None
    auto_update: bool | None = None


class CardResponse(BaseModel):
    id: int
    novel_id: int
    card_type: str
    name: str
    content_json: str
    auto_update: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
