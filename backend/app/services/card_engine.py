"""Card engine: inject cards into prompts and optionally auto-update from generated text."""
import json
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Card, Settings
from . import ai_service


def _normalize_text(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").strip())


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
    """Optionally call AI to extract card updates from generated text and merge into auto_update cards."""
    if not full_text.strip():
        return
    result = await db.execute(
        select(Card).where(Card.novel_id == novel_id, Card.auto_update == True)
    )
    auto_cards = list(result.scalars().all())
    set_result = await db.execute(select(Settings).where(Settings.id == settings_id))
    settings = set_result.scalar_one_or_none()
    if not settings or not (settings.api_key_encrypted or "").strip():
        return
    # v0.2.3: unified text updates + optional new card creation
    prompt = (
        "以下是一段小说正文。请根据正文，更新已有卡片的【详细描述】文本，并在有必要时创建新的文本卡片。\n"
        "你只输出一个 JSON 对象，格式严格如下：\n"
        "{\n"
        "  \"updates\": [ {\"card_id\": 1, \"text\": \"...\"}, ... ],\n"
        "  \"new_cards\": [ {\"card_type\": \"character|worldview|setting|plot|custom\", \"name\": \"...\", \"text\": \"...\", \"auto_update\": true}, ... ]\n"
        "}\n"
        "规则：\n"
        "- updates 只包含正文推进后有变化的卡片；text 为更新后的完整描述。\n"
        "- new_cards 仅在正文出现新的重要角色/设定/世界观信息时创建；避免与现有卡片同名同类型重复。\n"
        "- 除 JSON 外不要输出任何文字。\n\n"
        "【正文】\n" + full_text[-4500:] + "\n\n【已有卡片】\n"
    )
    for c in auto_cards:
        prompt += f"- id={c.id} name={c.name} type={c.card_type} text={_extract_card_text(c)}\n"
    # Also show non-auto cards names to reduce duplicates
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
            return
        raw_clean = re.sub(r"^[^{]*", "", raw)
        raw_clean = re.sub(r"[^}]*$", "", raw_clean)
        payload = json.loads(raw_clean)
        updates_list = payload.get("updates") or []
        new_cards = payload.get("new_cards") or []

        # Apply updates
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

        # Create new cards (avoid duplicates by (type,name))
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
