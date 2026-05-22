import json
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..models import Novel, Chapter, TimelineEvent, ConsistencyCheck, Settings, Card
from ..schemas import (
    NovelCreate,
    NovelUpdate,
    NovelResponse,
    NovelStatsResponse,
    ConsistencyCheckRequest,
    ConsistencyCheckResponse,
)
from ..services import ai_service

router = APIRouter(prefix="/novels", tags=["novels"])


def _strip_html(html: str) -> str:
    text = re.sub(r"</p\s*>", "\n", html or "", flags=re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _word_count(html: str) -> int:
    text = _strip_html(html)
    chinese = re.findall(r"[\u4e00-\u9fff]", text)
    latin = re.findall(r"[A-Za-z0-9]+", re.sub(r"[\u4e00-\u9fff]", " ", text))
    return len(chinese) + len(latin)


async def _stats_payload(novel_id: int, db: AsyncSession) -> NovelStatsResponse:
    result = await db.execute(
        select(Chapter).where(Chapter.novel_id == novel_id).order_by(Chapter.sort_order, Chapter.id)
    )
    chapters = list(result.scalars().all())
    chapter_stats = []
    total_words = 0
    target_total = 0
    done_count = 0
    updated_at = None
    for ch in chapters:
        wc = _word_count(ch.content or "")
        target = ch.target_words or 0
        total_words += wc
        target_total += target
        if ch.status == "done":
            done_count += 1
        if updated_at is None or ch.updated_at > updated_at:
            updated_at = ch.updated_at
        chapter_stats.append(
            {
                "id": ch.id,
                "title": ch.title,
                "status": ch.status or "drafting",
                "word_count": wc,
                "target_words": ch.target_words,
                "completion_rate": round(min(wc / target, 1) * 100, 1) if target else 0,
            }
        )
    completion = round(min(total_words / target_total, 1) * 100, 1) if target_total else 0
    return NovelStatsResponse(
        novel_id=novel_id,
        total_words=total_words,
        chapter_count=len(chapters),
        done_chapter_count=done_count,
        target_words_total=target_total,
        completion_rate=completion,
        updated_at=updated_at,
        chapters=chapter_stats,
    )


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
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            raise
        return json.loads(m.group(0))


@router.get("", response_model=list[NovelResponse])
async def list_novels(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Novel).order_by(Novel.updated_at.desc()))
    return list(result.scalars().all())


@router.post("", response_model=NovelResponse)
async def create_novel(data: NovelCreate, db: AsyncSession = Depends(get_db)):
    novel = Novel(title=data.title, description=data.description, outline=data.outline or "")
    db.add(novel)
    await db.flush()
    await db.refresh(novel)
    return novel


@router.get("/{novel_id}", response_model=NovelResponse)
async def get_novel(novel_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Novel).where(Novel.id == novel_id))
    novel = result.scalar_one_or_none()
    if not novel:
        raise HTTPException(status_code=404, detail="Novel not found")
    return novel


@router.patch("/{novel_id}", response_model=NovelResponse)
async def update_novel(novel_id: int, data: NovelUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Novel).where(Novel.id == novel_id))
    novel = result.scalar_one_or_none()
    if not novel:
        raise HTTPException(status_code=404, detail="Novel not found")
    if data.title is not None:
        novel.title = data.title
    if data.description is not None:
        novel.description = data.description
    if data.outline is not None:
        novel.outline = data.outline
    await db.flush()
    await db.refresh(novel)
    return novel


@router.get("/{novel_id}/stats", response_model=NovelStatsResponse)
async def get_novel_stats(novel_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Novel).where(Novel.id == novel_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Novel not found")
    return await _stats_payload(novel_id, db)


@router.get("/{novel_id}/workspace")
async def get_workspace(novel_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Novel).where(Novel.id == novel_id))
    novel = result.scalar_one_or_none()
    if not novel:
        raise HTTPException(status_code=404, detail="Novel not found")
    chapters_result = await db.execute(
        select(Chapter).where(Chapter.novel_id == novel_id).order_by(Chapter.sort_order, Chapter.id)
    )
    chapters = list(chapters_result.scalars().all())
    timeline_result = await db.execute(
        select(TimelineEvent).where(TimelineEvent.novel_id == novel_id).order_by(TimelineEvent.sort_order, TimelineEvent.id).limit(8)
    )
    checks_result = await db.execute(
        select(ConsistencyCheck)
        .where(ConsistencyCheck.novel_id == novel_id, ConsistencyCheck.resolved == False)
        .order_by(ConsistencyCheck.created_at.desc())
        .limit(8)
    )
    stats = await _stats_payload(novel_id, db)
    return {
        "novel": NovelResponse.model_validate(novel),
        "stats": stats,
        "chapters": [
            {
                "id": ch.id,
                "title": ch.title,
                "summary": ch.summary,
                "target_words": ch.target_words,
                "status": ch.status or "drafting",
                "sort_order": ch.sort_order,
                "word_count": _word_count(ch.content or ""),
            }
            for ch in chapters
        ],
        "recent_timeline_events": [
            {
                "id": e.id,
                "novel_id": e.novel_id,
                "chapter_id": e.chapter_id,
                "title": e.title,
                "event_time": e.event_time,
                "summary": e.summary,
                "characters": e.characters,
                "sort_order": e.sort_order,
                "created_at": e.created_at,
                "updated_at": e.updated_at,
            }
            for e in timeline_result.scalars().all()
        ],
        "unresolved_checks": [
            {
                "id": c.id,
                "novel_id": c.novel_id,
                "chapter_id": c.chapter_id,
                "check_type": c.check_type,
                "severity": c.severity,
                "message": c.message,
                "suggestion": c.suggestion,
                "resolved": c.resolved,
                "created_at": c.created_at,
            }
            for c in checks_result.scalars().all()
        ],
    }


@router.post("/{novel_id}/consistency-check", response_model=list[ConsistencyCheckResponse])
async def run_consistency_check(
    novel_id: int,
    body: ConsistencyCheckRequest,
    db: AsyncSession = Depends(get_db),
):
    novel_result = await db.execute(select(Novel).where(Novel.id == novel_id))
    novel = novel_result.scalar_one_or_none()
    if not novel:
        raise HTTPException(status_code=404, detail="Novel not found")
    settings_result = await db.execute(select(Settings).where(Settings.id == body.settings_id))
    settings = settings_result.scalar_one_or_none()
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    api_key = (settings.api_key_encrypted or "").strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="API Key not configured")

    query = select(Chapter).where(Chapter.novel_id == novel_id).order_by(Chapter.sort_order, Chapter.id)
    chapters = list((await db.execute(query)).scalars().all())
    if body.scope == "chapter":
        if not body.chapter_id:
            raise HTTPException(status_code=400, detail="chapter_id is required")
        chapters = [c for c in chapters if c.id == body.chapter_id]
    elif body.scope == "recent":
        chapters = chapters[-5:]
    elif body.scope != "all":
        raise HTTPException(status_code=400, detail="Invalid scope")
    if not chapters:
        return []

    cards = list((await db.execute(select(Card).where(Card.novel_id == novel_id))).scalars().all())
    events = list((await db.execute(select(TimelineEvent).where(TimelineEvent.novel_id == novel_id).order_by(TimelineEvent.sort_order, TimelineEvent.id))).scalars().all())
    text_parts = [f"【小说】{novel.title}", f"【简介】{novel.description or ''}", f"【全书大纲】{novel.outline or ''}"]
    if cards:
        text_parts.append("【设定卡片】")
        for card in cards[:40]:
            text_parts.append(f"- {card.name}({card.card_type}): {(card.content_json or '')[:500]}")
    if events:
        text_parts.append("【时间线】")
        for event in events[:80]:
            text_parts.append(f"- {event.event_time} {event.title}: {event.summary}")
    text_parts.append("【待检查章节】")
    for ch in chapters:
        text_parts.append(
            f"## {ch.title}\n梗概：{ch.summary or ''}\n目标字数：{ch.target_words or '无'}\n正文：{_strip_html(ch.content or '')[-5000:]}"
        )
    prompt = (
        "请检查以下小说资料中的一致性问题。只输出 JSON 对象："
        '{"issues":[{"chapter_id":1或null,"check_type":"character|timeline|setting|outline|foreshadowing|general",'
        '"severity":"low|medium|high","message":"问题","suggestion":"修改建议"}]}。'
        "最多输出 8 条；没有问题则 issues 为空数组。\n\n" + "\n\n".join(text_parts)
    )
    raw = await ai_service.complete(
        provider=settings.provider,
        api_key=api_key,
        model=settings.model_name or "gpt-4o-mini",
        system_prompt="你是小说连续性编辑，只输出合法 JSON。",
        user_content=prompt,
        proxy_url=settings.proxy_url,
        extra_config_json=settings.extra_config_json or "{}",
        max_tokens=4000,
        read_timeout=300.0,
    )
    try:
        payload = _parse_json_object(raw)
        issues = payload.get("issues") if isinstance(payload, dict) else []
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"模型未返回合法 JSON：{e}") from e
    if not isinstance(issues, list):
        issues = []
    saved: list[ConsistencyCheck] = []
    valid_chapter_ids = {c.id for c in chapters}
    for item in issues[:8]:
        if not isinstance(item, dict):
            continue
        cid = item.get("chapter_id")
        try:
            cid = int(cid) if cid is not None else None
        except Exception:
            cid = None
        if cid is not None and cid not in valid_chapter_ids:
            cid = None
        check = ConsistencyCheck(
            novel_id=novel_id,
            chapter_id=cid,
            check_type=(item.get("check_type") or "general")[:64],
            severity=(item.get("severity") or "medium")[:24],
            message=(item.get("message") or "").strip(),
            suggestion=(item.get("suggestion") or "").strip(),
            resolved=False,
        )
        if not check.message:
            continue
        db.add(check)
        saved.append(check)
    await db.flush()
    for check in saved:
        await db.refresh(check)
    return saved


@router.delete("/{novel_id}", status_code=204)
async def delete_novel(novel_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Novel).where(Novel.id == novel_id))
    novel = result.scalar_one_or_none()
    if not novel:
        raise HTTPException(status_code=404, detail="Novel not found")
    for model in (TimelineEvent, ConsistencyCheck):
        rows = await db.execute(select(model).where(model.novel_id == novel_id))
        for row in rows.scalars().all():
            await db.delete(row)
    await db.delete(novel)
    return None
