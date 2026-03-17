from datetime import datetime
from pydantic import BaseModel


class AuthorCreate(BaseModel):
    name: str
    style: str = ""
    format_rules: str = ""
    extra_json: str = "{}"


class AuthorUpdate(BaseModel):
    name: str | None = None
    style: str | None = None
    format_rules: str | None = None
    extra_json: str | None = None


class AuthorResponse(BaseModel):
    id: int
    name: str
    style: str
    format_rules: str
    extra_json: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
