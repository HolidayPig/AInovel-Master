from datetime import datetime
from pydantic import BaseModel


class NovelCreate(BaseModel):
    title: str = "未命名小说"
    description: str | None = None


class NovelUpdate(BaseModel):
    title: str | None = None
    description: str | None = None


class NovelResponse(BaseModel):
    id: int
    title: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
