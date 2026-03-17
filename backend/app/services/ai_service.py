"""AI service: stream generation with proxy support for OpenAI, Anthropic, Grok."""
import json
import re
from typing import AsyncIterator

import httpx

PROVIDER_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "grok": "https://api.x.ai/v1",
    "xai": "https://api.x.ai/v1",
    "anthropic": "https://api.anthropic.com",
    "custom": None,
}


def _get_base_url(provider: str, extra_config_json: str) -> str | None:
    if provider == "custom" and extra_config_json:
        try:
            cfg = json.loads(extra_config_json)
            return (cfg.get("base_url") or "").rstrip("/") or None
        except Exception:
            pass
    return PROVIDER_BASE_URLS.get(provider)


async def stream_openai_compatible(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict],
    proxy_url: str | None = None,
    web_search_enabled: bool = False,
) -> AsyncIterator[str]:
    """Stream from OpenAI-compatible chat completions API (OpenAI, Grok, DeepSeek, etc.)."""
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body: dict = {
        "model": model,
        "messages": messages,
        "stream": True,
    }
    if web_search_enabled:
        body["tools"] = [{"type": "web_search"}]
    timeout = httpx.Timeout(120.0)
    async with httpx.AsyncClient(proxy=proxy_url, timeout=timeout) as client:
        async with client.stream("POST", url, json=body, headers=headers) as resp:
            if resp.status_code != 200:
                err_text = await resp.aread()
                raise RuntimeError(f"API error {resp.status_code}: {err_text.decode()}")
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data = line[6:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    delta = (chunk.get("choices") or [{}])[0].get("delta") or {}
                    content = delta.get("content")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue


async def stream_anthropic(
    *,
    api_key: str,
    model: str,
    messages: list[dict],
    proxy_url: str | None = None,
) -> AsyncIterator[str]:
    """Stream from Anthropic Messages API."""
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    system = ""
    model_messages = []
    for m in messages:
        role = (m.get("role") or "user").lower()
        content = m.get("content") or ""
        if role == "system":
            system = content
            continue
        if role == "assistant":
            model_messages.append({"role": "assistant", "content": content})
        else:
            model_messages.append({"role": "user", "content": content})
    body = {
        "model": model,
        "max_tokens": 4096,
        "system": system or "You are a helpful assistant.",
        "messages": model_messages,
        "stream": True,
    }
    timeout = httpx.Timeout(120.0)
    async with httpx.AsyncClient(proxy=proxy_url, timeout=timeout) as client:
        async with client.stream("POST", url, json=body, headers=headers) as resp:
            if resp.status_code != 200:
                err_text = await resp.aread()
                raise RuntimeError(f"API error {resp.status_code}: {err_text.decode()}")
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:].strip()
                try:
                    chunk = json.loads(data)
                    if chunk.get("type") == "content_block_delta":
                        delta = chunk.get("delta") or {}
                        if delta.get("type") == "text_delta":
                            text = delta.get("text")
                            if text:
                                yield text
                except json.JSONDecodeError:
                    continue


async def complete(
    *,
    provider: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_content: str,
    proxy_url: str | None = None,
    extra_config_json: str = "{}",
) -> str:
    """One-shot completion (no stream). Used e.g. for card extraction."""
    base_url = _get_base_url(provider, extra_config_json) or "https://api.openai.com/v1"
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_content})

    if provider == "anthropic":
        url = "https://api.anthropic.com/v1/messages"
        headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
        body = {
            "model": model,
            "max_tokens": 4096,
            "system": system_prompt or "You are a helpful assistant.",
            "messages": [{"role": "user", "content": user_content}],
        }
        async with httpx.AsyncClient(proxy=proxy_url, timeout=httpx.Timeout(60.0)) as client:
            r = await client.post(url, json=body, headers=headers)
            r.raise_for_status()
            data = r.json()
            for block in (data.get("content") or []):
                if block.get("type") == "text":
                    return (block.get("text") or "").strip()
        return ""
    else:
        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        body = {"model": model, "messages": messages}
        async with httpx.AsyncClient(proxy=proxy_url, timeout=httpx.Timeout(60.0)) as client:
            r = await client.post(url, json=body, headers=headers)
            r.raise_for_status()
            data = r.json()
            choice = (data.get("choices") or [{}])[0]
            return (choice.get("message", {}).get("content") or "").strip()


async def stream_generate(
    *,
    provider: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_content: str,
    proxy_url: str | None = None,
    web_search_enabled: bool = False,
    extra_config_json: str = "{}",
) -> AsyncIterator[str]:
    """Unified stream generation: dispatches to OpenAI-compatible or Anthropic."""
    base_url = _get_base_url(provider, extra_config_json)
    if not base_url and provider == "custom":
        raise ValueError("Custom provider requires base_url in extra_config_json")
    if not base_url:
        base_url = "https://api.openai.com/v1"

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_content})

    if provider == "anthropic":
        async for chunk in stream_anthropic(
            api_key=api_key,
            model=model,
            messages=messages,
            proxy_url=proxy_url,
        ):
            yield chunk
    else:
        async for chunk in stream_openai_compatible(
            base_url=base_url,
            api_key=api_key,
            model=model,
            messages=messages,
            proxy_url=proxy_url,
            web_search_enabled=web_search_enabled,
        ):
            yield chunk
