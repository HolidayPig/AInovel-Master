"""Prompt budgeting helpers for generation requests.

The limits here are character based. They are intentionally conservative for
Chinese prose and keep the final model input predictable even when users paste a
large outline, chapter, author style, or card description.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


CONTEXT_LIMIT = 12000
USER_PROMPT_LIMIT = 1800
NOVEL_DESCRIPTION_LIMIT = 800
NOVEL_OUTLINE_LIMIT = 1200
CHAPTER_SUMMARY_LIMIT = 900
AUTHOR_STYLE_LIMIT = 700
AUTHOR_FORMAT_LIMIT = 400
CARD_TEXT_LIMIT = 650
CARD_TOTAL_LIMIT = 5200
MAX_RELEVANT_CARDS = 8
FALLBACK_CARD_LIMIT = 5
MIN_GENERATION_TOKENS = 2048
MAX_GENERATION_TOKENS = 24000


@dataclass
class PromptBudgetReport:
    context_original: int = 0
    context_final: int = 0
    prompt_original: int = 0
    prompt_final: int = 0
    system_final: int = 0
    cards_used: int = 0
    target_words: int = 0
    max_output_tokens: int = 4096


def normalize_space(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def compact_lines(text: str | None) -> str:
    text = (text or "").strip()
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def limit_text(text: str | None, limit: int, *, keep_tail: bool = False) -> str:
    text = compact_lines(text)
    if limit <= 0 or len(text) <= limit:
        return text
    if keep_tail:
        return "……（已省略更早内容）\n" + text[-limit:]
    return text[:limit] + "\n……（后文已省略）"


def build_story_context(novel: Any = None, chapter: Any = None, *, include_outline: bool = True) -> str:
    """Small, stable story metadata block for generation."""
    parts: list[str] = []
    if novel:
        title = normalize_space(getattr(novel, "title", "") or "")
        if title:
            parts.append(f"小说名：{title[:120]}")
        desc = limit_text(getattr(novel, "description", "") or "", NOVEL_DESCRIPTION_LIMIT)
        if desc:
            parts.append("小说简介：\n" + desc)
        outline = limit_text(getattr(novel, "outline", "") or "", NOVEL_OUTLINE_LIMIT)
        if include_outline and outline:
            parts.append("全书大纲摘录：\n" + outline)
    if chapter:
        title = normalize_space(getattr(chapter, "title", "") or "")
        if title:
            parts.append(f"当前章节：{title[:120]}")
        summary = limit_text(getattr(chapter, "summary", "") or "", CHAPTER_SUMMARY_LIMIT)
        if summary:
            parts.append("本章梗概：\n" + summary)
        target = getattr(chapter, "target_words", None)
        if target and target > 0:
            parts.append(f"本章目标字数：约 {int(target)} 字")
    return "\n\n".join(parts)


def clamp_target_words(value: int | None) -> int:
    try:
        target = int(value or 0)
    except Exception:
        return 0
    return max(0, min(target, 50000))


def output_tokens_for_target(target_words: int | None) -> int:
    target = clamp_target_words(target_words)
    if target <= 0:
        return 4096
    # Chinese prose is usually close to one token per character on many APIs,
    # with punctuation and formatting overhead. Add slack so the target is not
    # cut off by the provider before the chapter naturally closes.
    return max(MIN_GENERATION_TOKENS, min(int(target * 1.8) + 1200, MAX_GENERATION_TOKENS))


def build_target_instruction(target_words: int | None) -> str:
    target = clamp_target_words(target_words)
    if target <= 0:
        return ""
    lower = max(1, int(target * 0.85))
    upper = int(target * 1.15)
    return (
        f"【篇幅硬要求】本次生成目标约 {target} 字，请尽量写到 {lower}-{upper} 字。"
        "不要只写概述或短片段；请充分展开场景、动作、对话和心理变化。"
        "可以参考全书大纲把握主线方向、人物动机与伏笔，但只写当前章节范围内的内容；"
        "不要推进到全书主线后续章节，不要提前写完整本书。"
        "除非剧情已经完整闭合，否则不要在一千字左右提前收束。"
        "只输出可直接放入正文的小说内容，禁止输出括号说明、写作计划、下一章/下一段描写说明、作者备注或提纲。"
    )


def build_user_content(
    context: str,
    prompt: str,
    story_context: str = "",
    target_words: int | None = None,
) -> tuple[str, PromptBudgetReport]:
    report = PromptBudgetReport(context_original=len(context or ""), prompt_original=len(prompt or ""))
    context_limited = limit_text(context, CONTEXT_LIMIT, keep_tail=True)
    prompt_limited = limit_text(prompt or "请继续写下去。", USER_PROMPT_LIMIT)
    report.context_final = len(context_limited)
    report.prompt_final = len(prompt_limited)
    report.target_words = clamp_target_words(target_words)
    report.max_output_tokens = output_tokens_for_target(report.target_words)

    parts: list[str] = []
    if story_context:
        parts.append("【创作背景】\n" + story_context)
    target_instruction = build_target_instruction(report.target_words)
    if target_instruction:
        parts.append(target_instruction)
    if context_limited:
        parts.append("【最近正文上文】\n" + context_limited)
    parts.append("【本次续写要求】\n" + (prompt_limited or "请继续写下去。"))
    return "\n\n".join(parts), report
