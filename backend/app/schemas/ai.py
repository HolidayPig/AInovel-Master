from pydantic import BaseModel


class GenerateRequest(BaseModel):
    settings_id: int
    novel_id: int
    chapter_id: int | None = None
    context: str = ""
    prompt: str = ""
