"""Card engine: inject cards into prompts and optionally auto-update from generated text."""
import json
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Card, Settings, Novel, Chapter
from . import ai_service


def _strip_html(html: str) -> str:
    """Remove HTML tags and decode entities for plain text."""
    if not html or not isinstance(html, str):
        return ""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _normalize_text(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").strip())


def _hide_reference_links(text: str) -> str:
    """
    Hide/strip reference URLs and citation blocks from tool-assisted answers.
    This is best-effort cleaning for UI; does not affect model behavior.
    """
    if not text or not isinstance(text, str):
        return ""
    t = text
    # Remove markdown links but keep label: [label](url) -> label
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1", t, flags=re.IGNORECASE)
    # Remove raw URLs
    t = re.sub(r"https?://\S+", "", t, flags=re.IGNORECASE)
    # Drop common citation headers/sections
    t = re.sub(r"(?im)^\s*(sources?|references?|citations?)\s*[:：].*$", "", t)
    # Collapse whitespace
    t = re.sub(r"\n{3,}", "\n\n", t).strip()
    return t


def _extract_card_text(card: Card) -> str:
    """v0.2.3: prefer unified text field; fallback to legacy structured fields."""
    try:
        content = json.loads(card.content_json or "{}")
    except Exception:
        return (card.content_json or "").strip()
    if isinstance(content, dict):
        text = (
            (content.get("text") or "")
            or (content.get("description") or "")
            or (content.get("rules") or "")
            or (content.get("summary") or "")
        )
        if isinstance(text, str) and text.strip():
            return text.strip()
        # legacy character fields
        legacy_parts = []
        for k in ("name", "appearance", "personality", "backstory", "其他"):
            v = content.get(k)
            if isinstance(v, str) and v.strip():
                legacy_parts.append(f"{k}:{v.strip()}")
        if legacy_parts:
            return "\n".join(legacy_parts)
        return json.dumps(content, ensure_ascii=False)
    return str(content).strip()


def select_relevant_cards(cards: list[Card], text: str) -> list[Card]:
    """Select cards by keyword match (card name + optional keywords in content_json)."""
    hay = _normalize_text(text)
    if not hay:
        return cards
    selected: list[Card] = []
    for c in cards:
        name_kw = _normalize_text(c.name or "")
        kws: list[str] = []
        if name_kw:
            kws.append(name_kw)
        try:
            o = json.loads(c.content_json or "{}")
            if isinstance(o, dict):
                extra = o.get("keywords")
                if isinstance(extra, str):
                    kws.extend([_normalize_text(x) for x in re.split(r"[,\n，；;]+", extra) if _normalize_text(x)])
        except Exception:
            pass
        if not kws:
            continue
        if any(k and k in hay for k in kws):
            selected.append(c)
    # If nothing matched, keep worldview/setting to prevent losing global constraints
    if not selected:
        selected = [c for c in cards if c.card_type in ("worldview", "setting")]
    return selected


async def extract_and_update_cards(
    full_text: str, novel_id: int, settings_id: int, db: AsyncSession
) -> None:
    """(Legacy) Auto-apply card updates. Kept for compatibility; prefer extract_card_update_suggestions + user confirm."""
    payload = await extract_card_update_suggestions(full_text, novel_id, settings_id, db)
    if not payload:
        return
    try:
        updates_list = payload.get("updates") or []
        new_cards = payload.get("new_cards") or []
        result = await db.execute(
            select(Card).where(Card.novel_id == novel_id, Card.auto_update == True)
        )
        auto_cards = list(result.scalars().all())

        if isinstance(updates_list, list):
            for item in updates_list:
                try:
                    cid = int(item.get("card_id"))
                except Exception:
                    continue
                text_val = item.get("text")
                if not isinstance(text_val, str) or not text_val.strip():
                    continue
                card = next((c for c in auto_cards if c.id == cid), None)
                if not card:
                    continue
                card.content_json = json.dumps({"text": text_val.strip()}, ensure_ascii=False)

        if isinstance(new_cards, list) and new_cards:
            all_result = await db.execute(select(Card).where(Card.novel_id == novel_id))
            existing = list(all_result.scalars().all())
            existing_keys = {(c.card_type, (c.name or "").strip()) for c in existing}
            for item in new_cards:
                ctype = item.get("card_type")
                name = (item.get("name") or "").strip()
                text_val = item.get("text")
                auto = item.get("auto_update")
                if ctype not in ("character", "worldview", "setting", "plot", "custom"):
                    continue
                if not name or not isinstance(text_val, str) or not text_val.strip():
                    continue
                key = (ctype, name)
                if key in existing_keys:
                    continue
                card = Card(
                    novel_id=novel_id,
                    card_type=ctype,
                    name=name,
                    content_json=json.dumps({"text": text_val.strip()}, ensure_ascii=False),
                    auto_update=bool(auto) if auto is not None else True,
                )
                db.add(card)
                existing_keys.add(key)
        await db.commit()
    except Exception:
        pass


async def extract_card_update_suggestions(
    full_text: str, novel_id: int, settings_id: int, db: AsyncSession
) -> dict[str, Any] | None:
    """Return proposed card updates/new cards (do NOT apply). Used by frontend confirmation flow."""
    if not full_text.strip():
        return None
    result = await db.execute(
        select(Card).where(Card.novel_id == novel_id, Card.auto_update == True)
    )
    auto_cards = list(result.scalars().all())
    set_result = await db.execute(select(Settings).where(Settings.id == settings_id))
    settings = set_result.scalar_one_or_none()
    if not settings or not (settings.api_key_encrypted or "").strip():
        return None

    prompt = (
        "以下是一段小说正文。请根据正文，给出需要更新的卡片【详细描述】候选文本，并在有必要时给出应创建的新文本卡片。\n"
        "你只输出一个 JSON 对象：\n"
        "{\n"
        "  \"updates\": [ {\"card_id\": 1, \"text\": \"...\"}, ... ],\n"
        "  \"new_cards\": [ {\"card_type\": \"character|worldview|setting|plot|custom\", \"name\": \"...\", \"text\": \"...\", \"auto_update\": true}, ... ]\n"
        "}\n"
        "规则：\n"
        "- updates 只包含正文推进后有变化的卡片；text 为更新后的完整描述。\n"
        "- new_cards 仅在正文出现新的重要角色/设定/世界观信息时创建；避免与现有卡片同名同类型重复。\n"
        "- 除 JSON 外不要输出任何文字。\n\n"
        "【正文】\n" + full_text[-4500:] + "\n\n【可更新卡片】\n"
    )
    for c in auto_cards:
        prompt += f"- id={c.id} name={c.name} type={c.card_type} text={_extract_card_text(c)}\n"
    if not auto_cards:
        all_result = await db.execute(select(Card).where(Card.novel_id == novel_id))
        all_cards = list(all_result.scalars().all())
        for c in all_cards:
            prompt += f"- existing name={c.name} type={c.card_type}\n"
    try:
        raw = await ai_service.complete(
            provider=settings.provider,
            api_key=(settings.api_key_encrypted or "").strip(),
            model=settings.model_name or "gpt-4o-mini",
            system_prompt="你只输出 JSON，不要其他文字。",
            user_content=prompt,
            proxy_url=settings.proxy_url,
            extra_config_json=settings.extra_config_json or "{}",
        )
        if not raw:
            return None
        raw_clean = re.sub(r"^[^{]*", "", raw)
        raw_clean = re.sub(r"[^}]*$", "", raw_clean)
        payload = json.loads(raw_clean)
        if not isinstance(payload, dict):
            return None
        updates_list = payload.get("updates") or []
        new_cards = payload.get("new_cards") or []
        out_updates: list[dict[str, Any]] = []
        if isinstance(updates_list, list):
            for item in updates_list:
                try:
                    cid = int(item.get("card_id"))
                except Exception:
                    continue
                text_val = item.get("text")
                if not isinstance(text_val, str) or not text_val.strip():
                    continue
                if not any(c.id == cid for c in auto_cards):
                    continue
                out_updates.append({"card_id": cid, "text": text_val.strip()})
        out_new: list[dict[str, Any]] = []
        if isinstance(new_cards, list) and new_cards:
            all_result = await db.execute(select(Card).where(Card.novel_id == novel_id))
            existing = list(all_result.scalars().all())
            existing_keys = {(c.card_type, (c.name or "").strip()) for c in existing}
            for item in new_cards:
                ctype = item.get("card_type")
                name = (item.get("name") or "").strip()
                text_val = item.get("text")
                auto = item.get("auto_update")
                if ctype not in ("character", "worldview", "setting", "plot", "custom"):
                    continue
                if not name or not isinstance(text_val, str) or not text_val.strip():
                    continue
                if (ctype, name) in existing_keys:
                    continue
                out_new.append(
                    {
                        "card_type": ctype,
                        "name": name,
                        "text": text_val.strip(),
                        "auto_update": bool(auto) if auto is not None else True,
                    }
                )
        if not out_updates and not out_new:
            return None
        return {"updates": out_updates, "new_cards": out_new}
    except Exception:
        return None


async def get_novel_full_text(db: AsyncSession, novel_id: int) -> str:
    """Get novel description + all chapters content as plain text (HTML stripped)."""
    novel_result = await db.execute(select(Novel).where(Novel.id == novel_id))
    novel = novel_result.scalar_one_or_none()
    if not novel:
        return ""
    parts = []
    if novel.description and novel.description.strip():
        parts.append(novel.description.strip())
    ch_result = await db.execute(
        select(Chapter).where(Chapter.novel_id == novel_id).order_by(Chapter.sort_order, Chapter.id)
    )
    for ch in ch_result.scalars().all():
        if ch.content:
            parts.append(_strip_html(ch.content))
    return "\n\n".join(parts)


async def refresh_all_cards(novel_id: int, settings_id: int, db: AsyncSession) -> int:
    """Read latest novel content and re-extract all cards; apply directly. Returns count updated."""
    full_text = await get_novel_full_text(db, novel_id)
    if not full_text.strip():
        return 0
    result = await db.execute(select(Card).where(Card.novel_id == novel_id))
    cards = list(result.scalars().all())
    if not cards:
        return 0
    set_result = await db.execute(select(Settings).where(Settings.id == settings_id))
    settings = set_result.scalar_one_or_none()
    if not settings or not (settings.api_key_encrypted or "").strip():
        return 0
    prompt = (
        "以下是一部小说的最新正文与设定信息。请根据正文，为下面列出的每个卡片重新提炼并输出更新后的【详细描述】文本。\n"
        "你只输出一个 JSON 对象：\n"
        "{\n"
        '  "updates": [ {"card_id": 1, "text": "..."}, ... ]\n'
        "}\n"
        "规则：为每个 card_id 输出一条更新；text 为根据小说内容提炼后的完整描述，不要解释。除 JSON 外不要输出任何文字。\n\n"
        "【小说正文】\n" + full_text[-12000:] + "\n\n【待更新卡片】\n"
    )
    for c in cards:
        prompt += f"- card_id={c.id} name={c.name} type={c.card_type} 当前内容：{_extract_card_text(c)[:500]}\n"
    try:
        raw = await ai_service.complete(
            provider=settings.provider,
            api_key=(settings.api_key_encrypted or "").strip(),
            model=settings.model_name or "gpt-4o-mini",
            system_prompt="你只输出 JSON，不要其他文字。",
            user_content=prompt,
            proxy_url=settings.proxy_url,
            extra_config_json=settings.extra_config_json or "{}",
        )
        if not raw:
            return 0
        raw_clean = re.sub(r"^[^{]*", "", raw)
        raw_clean = re.sub(r"[^}]*$", "", raw_clean)
        payload = json.loads(raw_clean)
        updates_list = payload.get("updates") or []
        if not isinstance(updates_list, list):
            return 0
        card_by_id = {c.id: c for c in cards}
        updated = 0
        for item in updates_list:
            try:
                cid = int(item.get("card_id"))
            except Exception:
                continue
            text_val = item.get("text")
            if not isinstance(text_val, str) or not text_val.strip():
                continue
            card = card_by_id.get(cid)
            if not card:
                continue
            card.content_json = json.dumps({"text": text_val.strip()}, ensure_ascii=False)
            updated += 1
        return updated
    except Exception:
        return 0


async def refresh_one_card_suggestion(
    card_id: int, novel_id: int, settings_id: int, db: AsyncSession
) -> dict[str, str] | None:
    """Re-extract one card from latest novel content; return { old_text, new_text } for user confirm."""
    result = await db.execute(select(Card).where(Card.id == card_id, Card.novel_id == novel_id))
    card = result.scalar_one_or_none()
    if not card:
        return None
    full_text = await get_novel_full_text(db, novel_id)
    set_result = await db.execute(select(Settings).where(Settings.id == settings_id))
    settings = set_result.scalar_one_or_none()
    if not settings or not (settings.api_key_encrypted or "").strip():
        return None
    old_text = _extract_card_text(card)
    prompt = (
        "以下是一部小说的最新正文。请根据正文，仅针对下面这一张卡片，重新提炼并输出更新后的【详细描述】文本。\n"
        "只输出一段完整描述正文，不要 JSON、不要解释、不要卡片名称。\n\n"
        "【小说正文】\n" + full_text[-8000:] + "\n\n"
        f"【当前卡片】name={card.name} type={card.card_type}\n当前内容：\n{old_text}\n\n请输出更新后的描述："
    )
    try:
        new_text = await ai_service.complete(
            provider=settings.provider,
            api_key=(settings.api_key_encrypted or "").strip(),
            model=settings.model_name or "gpt-4o-mini",
            system_prompt="你只输出一段描述正文，不要其他内容。",
            user_content=prompt,
            proxy_url=settings.proxy_url,
            extra_config_json=settings.extra_config_json or "{}",
        )
        if not new_text or not isinstance(new_text, str):
            return None
        return {"old_text": old_text, "new_text": new_text.strip()}
    except Exception:
        return None


async def search_online_and_refine_card(card_id: int, settings_id: int, db: AsyncSession) -> str | None:
    """Use AI with web search to find related info by card name/description and refine into card content. Returns new text."""
    result = await db.execute(select(Card).where(Card.id == card_id))
    card = result.scalar_one_or_none()
    if not card:
        return None
    set_result = await db.execute(select(Settings).where(Settings.id == settings_id))
    settings = set_result.scalar_one_or_none()
    if not settings or not (settings.api_key_encrypted or "").strip():
        return None
    desc = _extract_card_text(card)
    name = (card.name or "").strip() or "未命名"
    prompt = (
        f"请根据以下卡片名称和描述，在互联网上搜索相关资料，提炼成一段完整的卡片描述内容。\n"
        f"卡片名称：{name}\n"
        f"卡片类型：{card.card_type}\n"
    )
    if desc:
        prompt += f"当前描述（可作参考）：\n{desc}\n\n"
    prompt += "请只输出提炼后的完整描述正文，不要解释、不要标题。"
    raw = await ai_service.complete(
        provider=settings.provider,
        api_key=(settings.api_key_encrypted or "").strip(),
        model=settings.model_name or "gpt-4o-mini",
        system_prompt="你是一名写作助手。根据用户给的卡片信息，联网搜索并提炼成一段可用于小说设定的描述。只输出描述正文。",
        user_content=prompt,
        proxy_url=settings.proxy_url,
        extra_config_json=settings.extra_config_json or "{}",
        web_search_enabled=True,
    )
    if not raw or not isinstance(raw, str):
        return None
    cleaned = _hide_reference_links(raw.strip())
    return cleaned.strip() if cleaned.strip() else None


def build_system_prompt(cards: list[Card], author: Any = None) -> str:
    """Build system prompt with novel context from cards and optional author style."""
    parts = [
        "你是一位小说写作助手。请根据用户提供的上文与续写提示，用流畅的中文续写小说内容。",
        "只输出续写正文，不要解释或元评论。",
    ]
    if author:
        parts.append("\n【你当前扮演的小说家风格（请严格遵循）】")
        if author.get("name"):
            parts.append(f"- 小说家类型：{author['name']}")
        if author.get("style"):
            parts.append(f"- 编写风格：{author['style']}")
        if author.get("format_rules"):
            parts.append(f"- 排版方式：{author['format_rules']}")
        parts.append("")
    if cards:
        parts.append("\n【当前小说的设定与角色（写作时请严格参照）】")
        for c in cards:
            name = c.name or f"未命名({c.card_type})"
            try:
                content = json.loads(c.content_json or "{}")
                if isinstance(content, dict):
                    text = _format_card_content(c.card_type, content)
                else:
                    text = str(content)
            except Exception:
                text = (c.content_json or "").strip() or "（无内容）"
            parts.append(f"\n## {name}\n{text}")
        parts.append("\n写作时请与以上设定保持一致。")
    return "\n".join(parts)


def _format_card_content(card_type: str, content: dict[str, Any]) -> str:
    # v0.2.3: unified text field across most types; keep backward compatibility
    text = content.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()
    if card_type == "character":
        return "\n".join(
            f"- {k}: {v}" for k, v in content.items() if v and k in ("name", "appearance", "personality", "backstory", "其他")
        ) or "（无内容）"
    if card_type == "worldview":
        return (content.get("description") or content.get("rules") or json.dumps(content, ensure_ascii=False)).strip()
    if card_type in ("setting", "plot", "custom"):
        v = content.get("description") or content.get("summary") or content.get("text")
        if isinstance(v, str) and v.strip():
            return v.strip()
        return json.dumps(content, ensure_ascii=False)
    return json.dumps(content, ensure_ascii=False)
