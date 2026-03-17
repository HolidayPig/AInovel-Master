from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json

from ..database import get_db
from ..models import Settings, Card, Author
from ..schemas.ai import GenerateRequest, SuggestTitleRequest
from ..services import ai_service, card_engine

router = APIRouter(prefix="/ai", tags=["ai"])


def _sse_line(data: str) -> bytes:
    return f"data: {data}\n\n".encode("utf-8")


@router.post("/generate")
async def generate_stream(
    body: GenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Settings).where(Settings.id == body.settings_id))
    settings = result.scalar_one_or_none()
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    api_key = (settings.api_key_encrypted or "").strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="API Key not configured")

    cards_result = await db.execute(select(Card).where(Card.novel_id == body.novel_id))
    cards = list(cards_result.scalars().all())
    author = None
    if body.author_id:
        author_result = await db.execute(select(Author).where(Author.id == body.author_id))
        a = author_result.scalar_one_or_none()
        if a:
            author = {"name": a.name, "style": a.style or "", "format_rules": a.format_rules or ""}
    relevant = card_engine.select_relevant_cards(cards, (body.context or "") + "\n" + (body.prompt or ""))
    system_prompt = card_engine.build_system_prompt(relevant, author=author)

    user_content = ""
    if body.context.strip():
        user_content += "【上文】\n" + body.context.strip() + "\n\n"
    user_content += "【续写提示】\n" + (body.prompt or "请继续写下去。")

    async def event_stream():
        try:
            async for chunk in ai_service.stream_generate(
                provider=settings.provider,
                api_key=api_key,
                model=settings.model_name or "gpt-4o-mini",
                system_prompt=system_prompt,
                user_content=user_content,
                proxy_url=settings.proxy_url,
                web_search_enabled=(
                    body.web_search_enabled
                    if body.web_search_enabled is not None
                    else settings.web_search_enabled
                ),
                extra_config_json=settings.extra_config_json or "{}",
            ):
                yield _sse_line(json.dumps({"type": "delta", "text": chunk}, ensure_ascii=False))
        except Exception as e:
            yield _sse_line(json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False))
        yield _sse_line(json.dumps({"type": "done"}, ensure_ascii=False))

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/suggest-chapter-title")
async def suggest_chapter_title(
    body: SuggestTitleRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate a short chapter title from summary using AI."""
    result = await db.execute(select(Settings).where(Settings.id == body.settings_id))
    settings = result.scalar_one_or_none()
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    api_key = (settings.api_key_encrypted or "").strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="API Key not configured")
    prompt = f"根据以下章节内容梗概，生成一个简短的中文章节标题（不超过20字），只输出标题，不要其他内容。\n\n梗概：\n{body.summary or '无'}"
    try:
        title = await ai_service.complete(
            provider=settings.provider,
            api_key=api_key,
            model=settings.model_name or "gpt-4o-mini",
            system_prompt="你只输出章节标题，不要引号或解释。",
            user_content=prompt,
            proxy_url=settings.proxy_url,
            extra_config_json=settings.extra_config_json or "{}",
        )
        title = (title or "未命名章节").strip()[:100]
        return {"title": title or "未命名章节"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
