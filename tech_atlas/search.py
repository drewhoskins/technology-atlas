"""Web search fallback for source discovery.

When the LLM can't suggest a Wikipedia URL for a component, this module
queries DuckDuckGo's HTML endpoint (no API key required) and returns the
first wikipedia.org result.
"""

from __future__ import annotations

import re
from urllib.parse import unquote

import httpx

DDG_HTML = "https://duckduckgo.com/html/"
USER_AGENT = "technology-atlas/0.1"

# DDG wraps result URLs in a /l/?uddg=<encoded-url>&... redirect.
_DDG_REDIRECT_RE = re.compile(r'uddg=([^&"]+)')
_HREF_RE = re.compile(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"')


def find_wikipedia_url(query: str) -> str | None:
    """Return the first English Wikipedia result for `query`, or None."""
    try:
        with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=15.0) as client:
            resp = client.post(
                DDG_HTML,
                data={"q": f"{query} site:en.wikipedia.org"},
            )
            resp.raise_for_status()
            html = resp.text
    except httpx.HTTPError:
        return None

    for m in _HREF_RE.finditer(html):
        href = m.group(1)
        redirect = _DDG_REDIRECT_RE.search(href)
        target = unquote(redirect.group(1)) if redirect else href
        if "en.wikipedia.org/wiki/" in target:
            if target.startswith("//"):
                target = "https:" + target
            return target
    return None
