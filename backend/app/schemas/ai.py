from pydantic import BaseModel


class SuggestTitleRequest(BaseModel):
    summary: str = ""
    settings_id: int


class GenerateRequest(BaseModel):
    settings_id: int
    novel_id: int
    chapter_id: int | None = None
    author_id: int | None = None
    context: str = ""
    prompt: str = ""
