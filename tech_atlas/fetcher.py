"""Wikipedia article fetching with local caching.

Layer 1 of the pipeline: pull raw source text and stash it under data/raw/ so
re-derivation against a new schema doesn't require hitting the network again.

Uses MediaWiki's `action=query&prop=extracts&explaintext` endpoint, which
returns clean plain text (no HTML markup, no template noise).
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw"
WIKIPEDIA_DIR = RAW_DIR / "wikipedia"
MANIFEST_PATH = RAW_DIR / "manifest.json"

WIKI_API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "technology-atlas/0.1 (https://technologyatlas.org; contact via drewhoskins.carrd.co)"


def title_from_url(url: str) -> str | None:
    """Extract the Wikipedia article title from a /wiki/<Title> URL."""
    parsed = urlparse(url)
    if "wikipedia.org" not in parsed.netloc:
        return None
    if not parsed.path.startswith("/wiki/"):
        return None
    return unquote(parsed.path[len("/wiki/"):])


def _slug(title: str) -> str:
    """File-safe slug for an article title, mirroring existing filenames in data/raw/wikipedia/."""
    return re.sub(r"[^A-Za-z0-9_\-]", "_", title)


def cache_path_for(url: str) -> Path | None:
    title = title_from_url(url)
    if not title:
        return None
    return WIKIPEDIA_DIR / f"{_slug(title)}.txt"


def is_cached(url: str) -> bool:
    p = cache_path_for(url)
    return p is not None and p.exists()


def load_cached(url: str) -> str:
    p = cache_path_for(url)
    if p is None or not p.exists():
        raise FileNotFoundError(f"not cached: {url}")
    return p.read_text(encoding="utf-8")


def fetch_wikipedia(url: str, *, force: bool = False) -> tuple[str, dict]:
    """Fetch a Wikipedia article's plain text. Returns (text, manifest_entry).

    Cached on disk under data/raw/wikipedia/<slug>.txt. Re-running is free
    unless force=True. Updates data/raw/manifest.json with provenance.
    """
    title = title_from_url(url)
    if not title:
        raise ValueError(f"not a Wikipedia URL: {url}")

    cache = cache_path_for(url)
    assert cache is not None

    if cache.exists() and not force:
        text = cache.read_text(encoding="utf-8")
        entry = _manifest_entry_for(url) or _build_manifest_entry(url, title, cache, text)
        return text, entry

    params = {
        "action": "query",
        "format": "json",
        "titles": title.replace("_", " "),
        "prop": "extracts|info",
        "explaintext": "1",
        "redirects": "1",
        "inprop": "url",
    }
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30.0) as client:
        resp = client.get(WIKI_API, params=params)
        resp.raise_for_status()
        data = resp.json()

    pages = data.get("query", {}).get("pages", {})
    if not pages:
        raise RuntimeError(f"no pages returned for {url}")
    page = next(iter(pages.values()))
    if "missing" in page:
        raise RuntimeError(f"Wikipedia article missing: {title}")
    text = page.get("extract", "")
    if not text.strip():
        raise RuntimeError(f"empty extract for {title}")

    canonical_url = page.get("fullurl", url)
    WIKIPEDIA_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_text(text, encoding="utf-8")

    entry = _build_manifest_entry(canonical_url, title, cache, text)
    _upsert_manifest(entry)
    return text, entry


def _build_manifest_entry(url: str, title: str, cache_path: Path, text: str) -> dict:
    return {
        "id": f"wikipedia:{_slug(title)}@{_now_iso()}",
        "url": url,
        "type": "wikipedia",
        "fetched_at": _now_iso(),
        "artifact_path": str(cache_path.relative_to(REPO_ROOT)),
        "license": "CC-BY-SA-4.0",
        "redistributable": True,
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {"_meta": {}, "artifacts": []}
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _manifest_entry_for(url: str) -> dict | None:
    manifest = _load_manifest()
    for art in manifest.get("artifacts", []):
        if art.get("url") == url:
            return art
    return None


def _upsert_manifest(entry: dict) -> None:
    manifest = _load_manifest()
    artifacts = manifest.setdefault("artifacts", [])
    for i, existing in enumerate(artifacts):
        if existing.get("url") == entry["url"]:
            artifacts[i] = entry
            break
    else:
        artifacts.append(entry)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def wikipedia_url_for_title(title: str) -> str:
    """Canonical en.wikipedia URL for an article title."""
    return f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"
