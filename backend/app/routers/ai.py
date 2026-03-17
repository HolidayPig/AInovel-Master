from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json

from ..database import get_db, AsyncSessionLocal
from ..models import Settings, Card
from ..schemas.ai import GenerateRequest
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
    system_prompt = card_engine.build_system_prompt(cards)

    user_content = ""
    if body.context.strip():
        user_content += "【上文】\n" + body.context.strip() + "\n\n"
    user_content += "【续写提示】\n" + (body.prompt or "请继续写下去。")

    full_text: list[str] = []

    async def event_stream():
        nonlocal full_text
        try:
            async for chunk in ai_service.stream_generate(
                provider=settings.provider,
                api_key=api_key,
                model=settings.model_name or "gpt-4o-mini",
                system_prompt=system_prompt,
                user_content=user_content,
                proxy_url=settings.proxy_url,
                web_search_enabled=settings.web_search_enabled,
                extra_config_json=settings.extra_config_json or "{}",
            ):
                full_text.append(chunk)
                yield _sse_line(json.dumps({"type": "delta", "text": chunk}, ensure_ascii=False))
        except Exception as e:
            yield _sse_line(json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False))
        else:
            try:
                async with AsyncSessionLocal() as session:
                    await card_engine.extract_and_update_cards(
                        "".join(full_text), body.novel_id, body.settings_id, session
                    )
            except Exception:
                pass
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
