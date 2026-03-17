"""Card engine: inject cards into prompts and optionally auto-update from generated text."""
import json
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Card, Settings
from . import ai_service


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
    if not auto_cards:
        return
    set_result = await db.execute(select(Settings).where(Settings.id == settings_id))
    settings = set_result.scalar_one_or_none()
    if not settings or not (settings.api_key_encrypted or "").strip():
        return
    prompt = (
        "以下是一段小说正文。请从中提取与以下卡片相关的信息，仅输出一个 JSON 数组，每个元素形如 {\"card_id\": <id>, \"updates\": {\"字段名\": \"新值\"}}。只更新有变化的字段。\n\n"
        "【正文】\n" + full_text[-4000:] + "\n\n【当前卡片】\n"
    )
    for c in auto_cards:
        prompt += f"- id={c.id} name={c.name} type={c.card_type} content={c.content_json}\n"
    try:
        raw = await ai_service.complete(
            provider=settings.provider,
            api_key=(settings.api_key_encrypted or "").strip(),
            model=settings.model_name or "gpt-4o-mini",
            system_prompt="你只输出一个 JSON 数组，不要其他文字。",
            user_content=prompt,
            proxy_url=settings.proxy_url,
            extra_config_json=settings.extra_config_json or "{}",
        )
        if not raw:
            return
        raw_clean = re.sub(r"^[^\[]*", "", raw)
        raw_clean = re.sub(r"[^\]]*$", "", raw_clean)
        updates_list = json.loads(raw_clean)
        for item in updates_list:
            cid = item.get("card_id")
            updates = item.get("updates") or {}
            if not isinstance(updates, dict):
                continue
            card = next((c for c in auto_cards if c.id == cid), None)
            if not card:
                continue
            try:
                content = json.loads(card.content_json or "{}")
                if not isinstance(content, dict):
                    content = {}
                content.update(updates)
                card.content_json = json.dumps(content, ensure_ascii=False)
            except Exception:
                continue
        await db.commit()
    except Exception:
        pass


def build_system_prompt(cards: list[Card]) -> str:
    """Build system prompt with novel context from cards."""
    parts = [
        "你是一位小说写作助手。请根据用户提供的上文与续写提示，用流畅的中文续写小说内容。",
        "只输出续写正文，不要解释或元评论。",
    ]
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
    if card_type == "character":
        return "\n".join(
            f"- {k}: {v}" for k, v in content.items() if v and k in ("name", "appearance", "personality", "backstory", "其他")
        ) or "（无内容）"
    if card_type == "worldview":
        return content.get("description") or content.get("rules") or json.dumps(content, ensure_ascii=False)
    if card_type in ("setting", "plot", "custom"):
        return content.get("description") or content.get("summary") or content.get("text") or json.dumps(content, ensure_ascii=False)
    return json.dumps(content, ensure_ascii=False)
