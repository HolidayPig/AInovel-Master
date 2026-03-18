"""Generate novel outline and per-chapter titles/summaries via LLM."""
import json
from typing import Any

from . import ai_service


def _strip_code_fence(text: str) -> str:
    t = (text or "").strip()
    if not t.startswith("```"):
        return t
    lines = t.split("\n")
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _parse_outline_json(raw: str) -> tuple[str, list[dict[str, str]]]:
    cleaned = _strip_code_fence(raw)
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("模型返回格式错误：应为 JSON 对象")
    outline = ""
    if isinstance(data.get("outline"), str):
        outline = data["outline"].strip()
    chapters = data.get("chapters")
    if not isinstance(chapters, list) or not chapters:
        raise ValueError("模型未返回 chapters 数组")
    out: list[dict[str, str]] = []
    for i, item in enumerate(chapters):
        if not isinstance(item, dict):
            continue
        title = (item.get("title") or "").strip() or f"第{i + 1}章"
        summary = (item.get("summary") or item.get("梗概") or "").strip()
        if not summary:
            summary = "（待补充梗概）"
        out.append({"title": title[:256], "summary": summary[:4000]})
    if not out:
        raise ValueError("chapters 为空")
    return outline, out


def build_user_prompt(brief: dict[str, Any]) -> str:
    n = int(brief.get("total_chapters") or 10)
    tw = int(brief.get("target_words_per_chapter") or 0)
    parts = [
        f"请根据以下信息，为长篇小说生成**全书大纲**（字符串）以及**恰好 {n} 个章节**的分章规划。",
        "",
        "【总体梗概】",
        str(brief.get("synopsis") or "").strip() or "（未填写）",
        "",
        "【主线】",
        str(brief.get("main_line") or "").strip() or "（未填写）",
        "",
        "【开头主要情节】",
        str(brief.get("opening") or "").strip() or "（未填写）",
        "",
        "【前期主要情节】",
        str(brief.get("early") or "").strip() or "（未填写）",
        "",
        "【中期主要情节】",
        str(brief.get("middle") or "").strip() or "（未填写）",
        "",
        "【后期主要情节】",
        str(brief.get("late") or "").strip() or "（未填写）",
        "",
        "【类型/题材】",
        str(brief.get("genre") or "").strip() or "（未指定）",
        "",
        "【基调与文风】",
        str(brief.get("tone") or "").strip() or "（未指定）",
        "",
        "【其他写作要求】",
        str(brief.get("extra") or "").strip() or "无",
        "",
        f"【硬性要求】共 {n} 章；每章目标字数约 {tw if tw > 0 else '由你根据节奏估计'} 字。",
        "章节标题要有辨识度，梗概写清本章关键事件与情绪走向，便于作者按梗概扩写成正文。",
        "",
        "只输出一个 JSON 对象，不要 markdown、不要解释。结构如下：",
        '{"outline":"全书大纲若干段文字","chapters":[{"title":"第1章 标题","summary":"本章梗概2-6句"},...]}',
        f"chapters 数组长度必须严格等于 {n}。",
    ]
    return "\n".join(parts)


SYSTEM = (
    "你是资深网文策划编辑。只输出合法 JSON，键为 outline（字符串）与 chapters（数组）。"
    "每个章节含 title、summary。不要使用中文引号包裹整个 JSON。"
)


async def generate_outline_chapters(
    *,
    provider: str,
    api_key: str,
    model: str,
    proxy_url: str | None,
    extra_config_json: str,
    brief: dict[str, Any],
) -> tuple[str, list[dict[str, str]]]:
    expected = int(brief.get("total_chapters") or 10)
    expected = max(1, min(expected, 120))
    brief = {**brief, "total_chapters": expected}
    user = build_user_prompt(brief)
    raw = await ai_service.complete(
        provider=provider,
        api_key=api_key,
        model=model or "gpt-4o-mini",
        system_prompt=SYSTEM,
        user_content=user,
        proxy_url=proxy_url,
        extra_config_json=extra_config_json or "{}",
        max_tokens=12000,
        read_timeout=600.0,
    )
    if not (raw or "").strip():
        raise RuntimeError("模型未返回内容")
    outline, chapters = _parse_outline_json(raw)
    if len(chapters) > expected:
        chapters = chapters[:expected]
    if len(chapters) < expected:
        raise RuntimeError(
            f"模型仅生成 {len(chapters)} 章，需要 {expected} 章。请减少「预计总章数」或稍后重试。"
        )
    return outline, chapters
