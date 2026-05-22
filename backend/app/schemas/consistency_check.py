from datetime import datetime
from pydantic import BaseModel


class ConsistencyCheckResponse(BaseModel):
    id: int
    novel_id: int
    chapter_id: int | None
    check_type: str
    severity: str
    message: str
    suggestion: str
    resolved: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ConsistencyCheckUpdate(BaseModel):
    resolved: bool | None = None
