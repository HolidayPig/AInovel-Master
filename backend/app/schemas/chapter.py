from datetime import datetime
from pydantic import BaseModel


class ChapterCreate(BaseModel):
    novel_id: int
    title: str = "未命名章节"
    content: str = ""
    summary: str | None = None
    target_words: int | None = None
    sort_order: int = 0


class ChapterUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    summary: str | None = None
    target_words: int | None = None
    sort_order: int | None = None


class ChapterResponse(BaseModel):
    id: int
    novel_id: int
    title: str
    content: str
    summary: str | None
    target_words: int | None
    sort_order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GenerateChaptersBriefRequest(BaseModel):
    novel_id: int
    settings_id: int
    """True：删除本小说现有全部章节后按大纲新建；False：在现有章节之后追加。"""
    replace_existing: bool = False
    synopsis: str = ""
    main_line: str = ""
    opening: str = ""
    early: str = ""
    middle: str = ""
    late: str = ""
    genre: str = ""
    tone: str = ""
    extra: str = ""
    total_chapters: int = 10
    target_words_per_chapter: int = 0


class GenerateChaptersBriefResponse(BaseModel):
    outline: str = ""
    chapters: list[ChapterResponse]
