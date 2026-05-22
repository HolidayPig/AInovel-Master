import json
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Chapter, Settings, TimelineEvent
from ..schemas import (
    ExtractTimelineRequest,
    TimelineEventCandidate,
    TimelineEventCreate,
    TimelineEventResponse,
    TimelineEventUpdate,
)
from ..services import ai_service

router = APIRouter(prefix="/timeline-events", tags=["timeline-events"])


def _strip_html(html: str) -> str:
    text = re.sub(r"</p\s*>", "\n", html or "", flags=re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _parse_json_object(raw: str) -> dict:
    text = (raw or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise
        return json.loads(match.group(0))


@router.get("", response_model=list[TimelineEventResponse])
async def list_timeline_events(novel_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TimelineEvent)
        .where(TimelineEvent.novel_id == novel_id)
        .order_by(TimelineEvent.sort_order, TimelineEvent.id)
    )
    return list(result.scalars().all())


@router.post("", response_model=TimelineEventResponse)
async def create_timeline_event(data: TimelineEventCreate, db: AsyncSession = Depends(get_db)):
    event = TimelineEvent(
        novel_id=data.novel_id,
        chapter_id=data.chapter_id,
        title=data.title,
        event_time=data.event_time,
        summary=data.summary,
        characters=data.characters,
        sort_order=data.sort_order,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


@router.patch("/{event_id}", response_model=TimelineEventResponse)
async def update_timeline_event(event_id: int, data: TimelineEventUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TimelineEvent).where(TimelineEvent.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Timeline event not found")
    for key in ("chapter_id", "title", "event_time", "summary", "characters", "sort_order"):
        value = getattr(data, key)
        if value is not None:
            setattr(event, key, value)
    await db.flush()
    await db.refresh(event)
    return event


@router.delete("/{event_id}", status_code=204)
async def delete_timeline_event(event_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TimelineEvent).where(TimelineEvent.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Timeline event not found")
    await db.delete(event)
    return None


@router.post("/extract-from-chapter", response_model=list[TimelineEventCandidate])
async def extract_from_chapter(body: ExtractTimelineRequest, db: AsyncSession = Depends(get_db)):
    chapter_result = await db.execute(
        select(Chapter).where(Chapter.id == body.chapter_id, Chapter.novel_id == body.novel_id)
    )
    chapter = chapter_result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    settings_result = await db.execute(select(Settings).where(Settings.id == body.settings_id))
    settings = settings_result.scalar_one_or_none()
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    api_key = (settings.api_key_encrypted or "").strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="API Key not configured")
    plain = _strip_html(chapter.content or "")
    if not plain:
        return []
    prompt = (
        "请从当前小说章节中提取 3-8 条关键时间线事件，只输出 JSON 对象："
        '{"events":[{"title":"事件标题","event_time":"故事内时间或空","summary":"事件摘要",'
        '"characters":"相关角色，逗号分隔","sort_order":0}]}。不要解释。\n\n'
        f"章节标题：{chapter.title}\n章节梗概：{chapter.summary or ''}\n正文：\n{plain[-12000:]}"
    )
    raw = await ai_service.complete(
        provider=settings.provider,
        api_key=api_key,
        model=settings.model_name or "gpt-4o-mini",
        system_prompt="你是小说时间线整理助手，只输出合法 JSON。",
        user_content=prompt,
        proxy_url=settings.proxy_url,
        extra_config_json=settings.extra_config_json or "{}",
        max_tokens=3000,
        read_timeout=300.0,
    )
    try:
        payload = _parse_json_object(raw)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"模型未返回合法 JSON：{e}") from e
    events = payload.get("events") if isinstance(payload, dict) else []
    if not isinstance(events, list):
        return []
    out: list[TimelineEventCandidate] = []
    for i, item in enumerate(events[:8]):
        if not isinstance(item, dict):
            continue
        title = (item.get("title") or "").strip()
        summary = (item.get("summary") or "").strip()
        if not title or not summary:
            continue
        out.append(
            TimelineEventCandidate(
                title=title[:256],
                event_time=(item.get("event_time") or "").strip()[:128],
                summary=summary[:2000],
                characters=(item.get("characters") or "").strip()[:1000],
                sort_order=int(item.get("sort_order") or i),
            )
        )
    return out
