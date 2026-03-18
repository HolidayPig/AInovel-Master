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


def _is_xai_base_url(base_url: str) -> bool:
    u = (base_url or "").rstrip("/").lower()
    return u.startswith("https://api.x.ai/v1") or u.startswith("http://api.x.ai/v1")


async def stream_xai_responses(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict],
    proxy_url: str | None = None,
    web_search_enabled: bool = False,
) -> AsyncIterator[str]:
    """
    Stream from xAI Responses API (/v1/responses), which is required for built-in tools
    like web_search (chat/completions live_search is deprecated).
    """
    url = f"{base_url.rstrip('/')}/responses"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body: dict = {
        "model": model,
        "stream": True,
        "input": messages,
    }
    if web_search_enabled:
        body["tools"] = [{"type": "web_search"}]
    timeout = httpx.Timeout(180.0)
    async with httpx.AsyncClient(proxy=proxy_url, timeout=timeout) as client:
        async with client.stream("POST", url, json=body, headers=headers) as resp:
            if resp.status_code != 200:
                err_text = await resp.aread()
                raise RuntimeError(f"API error {resp.status_code}: {err_text.decode()}")
            async for line in resp.aiter_lines():
                if not line:
                    continue
                # SSE format: "data: {...}"
                if line.startswith("data: "):
                    data = line[6:].strip()
                    if not data or data == "[DONE]":
                        continue
                    try:
                        ev = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    # OpenAI-style Responses streaming events
                    if isinstance(ev, dict):
                        if ev.get("type") == "response.output_text.delta" and isinstance(ev.get("delta"), str):
                            yield ev["delta"]
                            continue
                        # Some SDKs surface a nested delta object
                        delta = ev.get("delta")
                        if isinstance(delta, dict) and isinstance(delta.get("content"), str):
                            yield delta["content"]
                            continue


async def complete_xai_responses(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict],
    proxy_url: str | None = None,
    web_search_enabled: bool = False,
    read_timeout: float = 180.0,
) -> str:
    """One-shot completion via xAI Responses API (/v1/responses)."""
    url = f"{base_url.rstrip('/')}/responses"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body: dict = {"model": model, "input": messages}
    if web_search_enabled:
        body["tools"] = [{"type": "web_search"}]
    async with httpx.AsyncClient(
        proxy=proxy_url, timeout=_http_timeout(read_seconds=max(float(read_timeout), 180.0))
    ) as client:
        r = await client.post(url, json=body, headers=headers)
        if r.status_code != 200:
            raise RuntimeError(f"API error {r.status_code}: {r.text}")
        data = r.json()
        # Try common fields for Responses API
        if isinstance(data, dict):
            # Some implementations provide a convenience field
            ot = data.get("output_text")
            if isinstance(ot, str) and ot.strip():
                return ot.strip()
            # Otherwise, walk output blocks
            out = data.get("output")
            if isinstance(out, list):
                parts: list[str] = []
                for item in out:
                    if not isinstance(item, dict):
                        continue
                    content = item.get("content")
                    if isinstance(content, list):
                        for c in content:
                            if isinstance(c, dict) and c.get("type") == "output_text" and isinstance(c.get("text"), str):
                                parts.append(c["text"])
                if parts:
                    return "".join(parts).strip()
        return ""


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
    # xAI: live_search on chat/completions is deprecated (410). Use Responses API tools instead.
    if web_search_enabled and _is_xai_base_url(base_url):
        async for chunk in stream_xai_responses(
            base_url=base_url,
            api_key=api_key,
            model=model,
            messages=messages,
            proxy_url=proxy_url,
            web_search_enabled=True,
        ):
            yield chunk
        return

    tools_variants: list[list[dict]] = [
        [{"type": "live_search", "sources": ["web"]}],
        [{"type": "live_search", "sources": [{"type": "web"}]}],
        [{"type": "live_search", "sources": ["internet"]}],
    ]
    if web_search_enabled:
        body["tools"] = tools_variants[0]
    timeout = httpx.Timeout(120.0)
    async with httpx.AsyncClient(proxy=proxy_url, timeout=timeout) as client:
        for i in range(len(tools_variants) if web_search_enabled else 1):
            if web_search_enabled:
                body["tools"] = tools_variants[i]
            async with client.stream("POST", url, json=body, headers=headers) as resp:
                if resp.status_code == 422 and web_search_enabled and i < len(tools_variants) - 1:
                    # try next tools schema variant
                    continue
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
                break


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


def _http_timeout(*, read_seconds: float) -> httpx.Timeout:
    """连接/写池适度超时，读取单独放宽（长文本生成易超 30s～90s）。"""
    return httpx.Timeout(connect=60.0, read=read_seconds, write=120.0, pool=120.0)


async def complete(
    *,
    provider: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_content: str,
    proxy_url: str | None = None,
    extra_config_json: str = "{}",
    web_search_enabled: bool = False,
    max_tokens: int | None = None,
    read_timeout: float | None = None,
) -> str:
    """One-shot completion。read_timeout 为等待模型完整响应的最长时间（秒），大纲生成建议 300～600。"""
    base_url = _get_base_url(provider, extra_config_json) or "https://api.openai.com/v1"
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_content})

    read_s = float(read_timeout) if read_timeout is not None else 180.0

    if provider == "anthropic":
        url = "https://api.anthropic.com/v1/messages"
        headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
        mt = min(max(max_tokens or 4096, 256), 8192)
        body = {
            "model": model,
            "max_tokens": mt,
            "system": system_prompt or "You are a helpful assistant.",
            "messages": [{"role": "user", "content": user_content}],
        }
        async with httpx.AsyncClient(proxy=proxy_url, timeout=_http_timeout(read_seconds=max(read_s, 180.0))) as client:
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
        body: dict = {"model": model, "messages": messages}
        if max_tokens is not None:
            body["max_tokens"] = min(max(max_tokens, 256), 16384)
        # xAI: live_search on chat/completions is deprecated (410). Use Responses API tools instead.
        if web_search_enabled and _is_xai_base_url(base_url):
            return await complete_xai_responses(
                base_url=base_url,
                api_key=api_key,
                model=model,
                messages=messages,
                proxy_url=proxy_url,
                web_search_enabled=True,
                read_timeout=read_s,
            )

        tools_variants: list[list[dict]] = [
            [{"type": "live_search", "sources": ["web"]}],
            [{"type": "live_search", "sources": [{"type": "web"}]}],
            [{"type": "live_search", "sources": ["internet"]}],
        ]
        async with httpx.AsyncClient(
            proxy=proxy_url, timeout=_http_timeout(read_seconds=max(read_s, 180.0))
        ) as client:
            last_err: Exception | None = None
            tries = len(tools_variants) if web_search_enabled else 1
            for i in range(tries):
                if web_search_enabled:
                    body["tools"] = tools_variants[i]
                try:
                    r = await client.post(url, json=body, headers=headers)
                    if r.status_code == 422 and web_search_enabled and i < tries - 1:
                        continue
                    r.raise_for_status()
                    data = r.json()
                    choice = (data.get("choices") or [{}])[0]
                    return (choice.get("message", {}).get("content") or "").strip()
                except Exception as e:
                    last_err = e
                    if web_search_enabled and i < tries - 1:
                        continue
                    raise
            if last_err:
                raise last_err
            return ""


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
