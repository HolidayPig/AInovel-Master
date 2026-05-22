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
    target_words: int | None = None
    generation_mode: str = "continue"
    # Per-request override. If None, fall back to Settings.web_search_enabled.
    web_search_enabled: bool | None = None
