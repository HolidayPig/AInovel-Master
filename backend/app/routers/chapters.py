import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from ..database import get_db
from ..models import Chapter, Novel, Settings
from ..schemas import (
    ChapterCreate,
    ChapterUpdate,
    ChapterResponse,
    GenerateChaptersBriefRequest,
    GenerateChaptersBriefResponse,
)
from ..services import outline_generator

router = APIRouter(prefix="/chapters", tags=["chapters"])


@router.get("", response_model=list[ChapterResponse])
async def list_chapters(novel_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Chapter).where(Chapter.novel_id == novel_id).order_by(Chapter.sort_order, Chapter.id)
    )
    return list(result.scalars().all())


@router.post("", response_model=ChapterResponse)
async def create_chapter(data: ChapterCreate, db: AsyncSession = Depends(get_db)):
    chapter = Chapter(
        novel_id=data.novel_id,
        title=data.title,
        content=data.content,
        summary=data.summary,
        target_words=data.target_words,
        sort_order=data.sort_order,
    )
    db.add(chapter)
    await db.flush()
    await db.refresh(chapter)
    return chapter


@router.get("/{chapter_id}", response_model=ChapterResponse)
async def get_chapter(chapter_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter


@router.patch("/{chapter_id}", response_model=ChapterResponse)
async def update_chapter(chapter_id: int, data: ChapterUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    if data.title is not None:
        chapter.title = data.title
    if data.content is not None:
        chapter.content = data.content
    if data.summary is not None:
        chapter.summary = data.summary
    if data.target_words is not None:
        chapter.target_words = data.target_words
    if data.sort_order is not None:
        chapter.sort_order = data.sort_order
    await db.flush()
    await db.refresh(chapter)
    return chapter


@router.post("/generate-from-brief", response_model=GenerateChaptersBriefResponse)
async def generate_chapters_from_brief(
    body: GenerateChaptersBriefRequest,
    db: AsyncSession = Depends(get_db),
):
    """根据用户梗概与分阶段要求，调用 AI 生成分章大纲并批量创建章节。"""
    nres = await db.execute(select(Novel).where(Novel.id == body.novel_id))
    novel = nres.scalar_one_or_none()
    if not novel:
        raise HTTPException(status_code=404, detail="Novel not found")
    sres = await db.execute(select(Settings).where(Settings.id == body.settings_id))
    settings = sres.scalar_one_or_none()
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    api_key = (settings.api_key_encrypted or "").strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="API Key not configured")

    total = max(1, min(int(body.total_chapters), 120))
    tw = max(0, min(int(body.target_words_per_chapter), 50000))
    brief = {
        "synopsis": body.synopsis,
        "main_line": body.main_line,
        "opening": body.opening,
        "early": body.early,
        "middle": body.middle,
        "late": body.late,
        "genre": body.genre,
        "tone": body.tone,
        "extra": body.extra,
        "total_chapters": total,
        "target_words_per_chapter": tw,
    }
    try:
        outline_text, items = await outline_generator.generate_outline_chapters(
            provider=settings.provider,
            api_key=api_key,
            model=settings.model_name or "gpt-4o-mini",
            proxy_url=settings.proxy_url,
            extra_config_json=settings.extra_config_json or "{}",
            brief=brief,
        )
    except httpx.ReadTimeout:
        raise HTTPException(
            status_code=504,
            detail="等待模型返回超时（多章大纲耗时较长）。请减小「预计总章数」后重试，或换用更快的模型；若使用自建代理请放宽网关读超时。",
        ) from None
    except Exception as e:
        err_msg = (str(e) or repr(e) or "").strip() or "生成大纲失败（模型未返回有效内容或网络异常）"
        if "ReadTimeout" in err_msg or "read timeout" in err_msg.lower():
            err_msg = (
                "等待模型返回超时。请减小「预计总章数」或换更快模型；"
                "后端已支持最长约 10 分钟，若仍失败请检查 API 线路是否限制 30 秒断连。"
            )
        raise HTTPException(status_code=500, detail=err_msg) from e

    if body.replace_existing:
        await db.execute(delete(Chapter).where(Chapter.novel_id == body.novel_id))
        await db.flush()
        base_order = 0
    else:
        crow = await db.execute(
            select(Chapter.sort_order)
            .where(Chapter.novel_id == body.novel_id)
            .order_by(Chapter.sort_order.desc(), Chapter.id.desc())
            .limit(1)
        )
        last = crow.scalar_one_or_none()
        base_order = (last + 1) if last is not None else 0

    created: list[Chapter] = []
    for i, item in enumerate(items):
        ch = Chapter(
            novel_id=body.novel_id,
            title=item["title"],
            content="",
            summary=item["summary"],
            target_words=tw if tw > 0 else None,
            sort_order=base_order + i,
        )
        db.add(ch)
        created.append(ch)
    await db.flush()
    for ch in created:
        await db.refresh(ch)

    if outline_text:
        prev = (novel.description or "").strip()
        novel.description = (prev + "\n\n【AI 生成全书大纲】\n" + outline_text).strip()[:65000]

    await db.commit()
    for ch in created:
        await db.refresh(ch)
    return GenerateChaptersBriefResponse(
        outline=outline_text,
        chapters=[ChapterResponse.model_validate(c) for c in created],
    )


@router.delete("/{chapter_id}", status_code=204)
async def delete_chapter(chapter_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    await db.delete(chapter)
    return None
