"""Anthropic SDK wrapper with on-disk response caching.

Every call is keyed by (model, system, messages, tools); identical inputs
short-circuit to the cached response. Re-running the ingestion pipeline
is free aside from the initial fetch.

API key resolution: ANTHROPIC_API_KEY env var, or load it from .env if the
shell doesn't have it.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = REPO_ROOT / "data" / "cache" / "llm"

DEFAULT_MODEL = "claude-sonnet-4-6"
HIGH_QUALITY_MODEL = "claude-opus-4-7"


def _load_dotenv_if_needed() -> None:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        v = v.strip().strip('"').strip("'")
        if k.strip() == "ANTHROPIC_API_KEY" and v:
            os.environ["ANTHROPIC_API_KEY"] = v
            return


class LLMClient:
    def __init__(self, *, model: str = DEFAULT_MODEL, max_tokens: int = 8192) -> None:
        _load_dotenv_if_needed()
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "ANTHROPIC_API_KEY not set. Export it in your shell or add "
                "ANTHROPIC_API_KEY=... to .env at the repo root."
            )
        import anthropic  # lazy import so module import doesn't require the dep

        self._client = anthropic.Anthropic()
        self.model = model
        self.max_tokens = max_tokens
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def call(
        self,
        *,
        system: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: dict | None = None,
        purpose: str,
    ) -> dict:
        """Make an LLM call, caching by content hash. `purpose` is metadata
        for cache file naming and debugging only.
        """
        key = _cache_key(self.model, system, messages, tools, tool_choice)
        cache_path = CACHE_DIR / f"{purpose}_{key[:16]}.json"
        if cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8"))

        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice

        resp = self._client.messages.create(**kwargs)
        result = {
            "model": resp.model,
            "stop_reason": resp.stop_reason,
            "content": [_serialize_block(b) for b in resp.content],
            "usage": {
                "input_tokens": resp.usage.input_tokens,
                "output_tokens": resp.usage.output_tokens,
            },
        }
        cache_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return result


def _serialize_block(block) -> dict:
    if block.type == "text":
        return {"type": "text", "text": block.text}
    if block.type == "tool_use":
        return {"type": "tool_use", "name": block.name, "input": block.input, "id": block.id}
    return {"type": block.type}


def _cache_key(
    model: str,
    system: str,
    messages: list[dict],
    tools: list[dict] | None,
    tool_choice: dict | None,
) -> str:
    payload = json.dumps(
        {
            "model": model,
            "system": system,
            "messages": messages,
            "tools": tools or [],
            "tool_choice": tool_choice or {},
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def extract_tool_use(response: dict, tool_name: str) -> dict:
    """Find the named tool_use block in a response and return its `input` dict."""
    for block in response["content"]:
        if block.get("type") == "tool_use" and block.get("name") == tool_name:
            return block["input"]
    raise RuntimeError(
        f"expected tool_use '{tool_name}' in response, got: "
        f"{[b.get('type') for b in response['content']]}"
    )
