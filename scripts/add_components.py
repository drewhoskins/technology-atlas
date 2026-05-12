#!/usr/bin/env python3
"""Recursively populate enabling_components for an existing entry.

Usage:
  uv run python scripts/add_components.py <entry_id> --depth N [options]

For each enabling_component on the parent (and optionally proposed-new ones):
  1. Discover candidate Wikipedia sources via LLM, fall back to web search.
  2. Scrape the chosen source(s) into data/raw/wikipedia/ (cached).
  3. Extract a populated Entry via LLM (cached by content hash).
  4. Write data/seeds/<id>.json.
  5. Backlink: set parent.enabling_components[i].linked_entry_id.

Depth semantics:
  depth=0: create stubs only — don't recurse further.
  depth=N: fully populate the immediate components AND recurse N-1 levels.

Idempotency: components already linked are skipped. Cached fetches and
cached LLM calls make re-runs free.

Build artifacts (atlas.db, web/) are NOT regenerated automatically; the
script prints the command at the end so you can sanity-check seeds first.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tech_atlas.fetcher import (  # noqa: E402
    fetch_wikipedia,
    title_from_url,
)
from tech_atlas.extractor import (  # noqa: E402
    discover_sources_for_component,
    extract_entry_fields,
    reconcile_components,
)
from tech_atlas.llm import LLMClient, DEFAULT_MODEL, HIGH_QUALITY_MODEL  # noqa: E402
from tech_atlas.search import find_wikipedia_url  # noqa: E402

SEEDS_DIR = REPO_ROOT / "data" / "seeds"

IMPORTANCE_ORDER = {"critical": 0, "important": 1, "incidental": 2}


def prompt_yes_no(question: str, *, default: bool = False) -> bool:
    suffix = " [Y/n] " if default else " [y/N] "
    try:
        ans = input(question + suffix).strip().lower()
    except EOFError:
        return default
    if not ans:
        return default
    return ans in ("y", "yes")


# ---------------------------------------------------------------------------
# Seed loading & saving
# ---------------------------------------------------------------------------

def _seed_filename(entry_id: str) -> str:
    """data/seeds uses underscores in filenames, colons in ids."""
    return entry_id.replace(":", "_") + ".json"


def load_all_seeds() -> dict[str, dict]:
    seeds: dict[str, dict] = {}
    for p in sorted(SEEDS_DIR.glob("*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        seeds[data["id"]] = data
    return seeds


def save_seed(entry: dict) -> Path:
    SEEDS_DIR.mkdir(parents=True, exist_ok=True)
    path = SEEDS_DIR / _seed_filename(entry["id"])
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(entry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    tmp.replace(path)
    return path


# ---------------------------------------------------------------------------
# Id allocation
# ---------------------------------------------------------------------------

_TYPE_NS = {
    "technology": None,  # use the component name's natural prefix
    "infrastructure": "infrastructure",
    "practice": "practice",
    "process": "process",
    "standard": "standard",
}


def _snake(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", s.strip().lower())
    return s.strip("_")


def coin_entry_id(name: str, type_: str, existing_ids: set[str]) -> str:
    """Build a deterministic entry id. Collisions get a numeric suffix."""
    ns = _TYPE_NS.get(type_) or type_
    base = f"{ns}:{_snake(name)}"
    if base not in existing_ids:
        return base
    for i in range(2, 100):
        cand = f"{base}_{i}"
        if cand not in existing_ids:
            return cand
    raise RuntimeError(f"could not allocate id for {name}")


def find_existing_match(name: str, seeds: dict[str, dict]) -> str | None:
    """Return an existing entry id if its name normalizes to the same form."""
    target = _snake(name)
    for eid, entry in seeds.items():
        if _snake(entry["name"]) == target:
            return eid
    return None


# ---------------------------------------------------------------------------
# Source aggregation
# ---------------------------------------------------------------------------

def gather_parent_sources(parent: dict) -> list[dict]:
    """Pull the parent's primary source artifacts (description_sources + the
    sources from the highest-confidence elements) and return concatenated
    text blocks suitable for the reconciler.
    """
    seen_urls: dict[str, str] = {}
    for src in parent.get("description_sources", []) or []:
        url = src.get("url")
        if url and url not in seen_urls:
            seen_urls[url] = src.get("raw_id", "")
    # Walk a few high-signal lists for extra source URLs.
    for key in ("innovators", "enabling_components", "predecessors"):
        for item in parent.get(key, []) or []:
            for src in item.get("sources", []) or []:
                url = src.get("url")
                if url and url not in seen_urls:
                    seen_urls[url] = src.get("raw_id", "")

    sources = []
    for url in list(seen_urls)[:6]:  # cap to keep prompt size sane
        if not title_from_url(url):
            continue
        try:
            text, manifest_entry = fetch_wikipedia(url)
        except Exception as exc:
            print(f"    warn: could not fetch parent source {url}: {exc}")
            continue
        sources.append(
            {
                "raw_id": manifest_entry["id"],
                "url": manifest_entry["url"],
                "text": text,
            }
        )
    return sources


# ---------------------------------------------------------------------------
# Component → entry
# ---------------------------------------------------------------------------

def resolve_source_candidates(
    *,
    client: LLMClient,
    component: dict,
    parent: dict,
) -> list[tuple[str, str]]:
    """Return ordered list of (url, reason) candidates to try.

    LLM-proposed Wikipedia titles (confidence >= 0.5) come first, in
    confidence order. A DuckDuckGo "site:en.wikipedia.org" search appends a
    final fallback. This list is consumed by build_entry_for_component,
    which iterates and tries each fetch until one succeeds — so LLM
    hallucinations that 404 don't kill the component.
    """
    out: list[tuple[str, str]] = []
    candidates = discover_sources_for_component(
        client=client,
        name=component["name"],
        component_type=component.get("type", "technology"),
        role=component.get("role", ""),
        parent_name=parent["name"],
        parent_description=parent.get("description", "")[:1500],
    )
    for c in candidates:
        if c["confidence"] >= 0.5:
            out.append(
                (
                    c["url"],
                    f"llm_discovery({c['wikipedia_title']}, conf={c['confidence']:.2f})",
                )
            )

    fallback = find_wikipedia_url(component["name"])
    if fallback and not any(u == fallback for u, _ in out):
        out.append((fallback, "web_search_fallback"))
    return out


def build_entry_for_component(
    *,
    client: LLMClient,
    component: dict,
    parent: dict,
    entry_id: str,
    entry_kind: Literal["stub", "full"],
    domain: str,
) -> dict | None:
    """Discover → scrape → extract → return populated Entry, or None on failure."""
    candidates = resolve_source_candidates(
        client=client, component=component, parent=parent
    )
    if not candidates:
        print(f"    no source candidates for {component['name']}; skipping")
        return None

    text: str | None = None
    manifest_entry: dict | None = None
    for url, reason in candidates:
        print(f"    trying: {url}  [{reason}]")
        try:
            text, manifest_entry = fetch_wikipedia(url)
            break
        except Exception as exc:
            print(f"      fetch failed: {exc}")
            text, manifest_entry = None, None

    if text is None or manifest_entry is None:
        print(f"    all candidates failed for {component['name']}; skipping")
        return None

    fields = extract_entry_fields(
        client=client,
        entry_name=component["name"],
        entry_kind=entry_kind,
        sources=[{"raw_id": manifest_entry["id"], "url": manifest_entry["url"], "text": text}],
    )

    entry: dict = {
        "id": entry_id,
        "name": component["name"],
        "domain": domain,
        "entry_type": "stub" if entry_kind == "stub" else "standalone",
        "parent_id": None,
        **fields,
    }
    # Ensure default-empty arrays for fields the build_site renderer expects.
    for k in (
        "description_sources",
        "innovators",
        "predecessors",
        "enabling_components",
        "failed_alternatives",
        "funders",
        "regulatory_moments",
        "geographic_diffusion",
        "key_dates",
    ):
        entry.setdefault(k, [])
    # Tag AI-authored sources.
    for src_list_key in ("description_sources",):
        for src in entry.get(src_list_key, []):
            src.setdefault("fetched_at", manifest_entry["fetched_at"])
            src.setdefault("ai_or_human", "ai")
    for item_key in ("innovators", "predecessors", "enabling_components", "key_dates"):
        for item in entry.get(item_key, []):
            for src in item.get("sources", []):
                src.setdefault("fetched_at", manifest_entry["fetched_at"])
                src.setdefault("ai_or_human", "ai")
    return entry


# ---------------------------------------------------------------------------
# Recursion
# ---------------------------------------------------------------------------

class Stats:
    def __init__(self) -> None:
        self.created: list[str] = []
        self.linked: list[tuple[str, str]] = []  # (parent_id, child_id)
        self.skipped: list[tuple[str, str]] = []  # (component_name, reason)
        self.proposed_additions: list[tuple[str, str]] = []  # (parent_id, component_name)


def process_entry(
    *,
    client: LLMClient,
    parent_id: str,
    depth: int,
    seeds: dict[str, dict],
    visited: set[str],
    stats: Stats,
    reconcile: bool,
    auto_accept: bool,
    min_importance: str,
) -> None:
    if parent_id in visited:
        return
    visited.add(parent_id)

    parent = seeds.get(parent_id)
    if parent is None:
        print(f"  WARN: parent {parent_id} not in seeds; skipping")
        return
    print(f"\n== {parent_id} (depth={depth}) ==")

    if reconcile:
        parent_sources = gather_parent_sources(parent)
        if parent_sources:
            concat = "\n\n".join(s["text"][:8000] for s in parent_sources)
            additions = reconcile_components(
                client=client,
                parent_name=parent["name"],
                parent_description=parent.get("description", ""),
                existing_components=parent.get("enabling_components", []),
                raw_text=concat,
            )
            accepted = []
            for add in additions:
                print(f"  proposed component: {add['name']} ({add.get('type', '?')})")
                role = (add.get("role") or "")[:300]
                quote = (add.get("justification_quote") or "")[:300]
                if role:
                    print(f"      role:  {role}")
                if quote:
                    print(f"     quote:  “{quote}”")
                if auto_accept or prompt_yes_no("    accept?", default=True):
                    accepted.append(add)
            if accepted:
                for add in accepted:
                    add.setdefault("brief", None)
                    add["linked_entry_id"] = None
                    add["sources"] = []
                    # justification_quote is reconciler-internal metadata; drop it.
                    add.pop("justification_quote", None)
                parent.setdefault("enabling_components", []).extend(accepted)
                for add in accepted:
                    stats.proposed_additions.append((parent_id, add["name"]))
                save_seed(parent)

    components = parent.get("enabling_components", []) or []
    if not components:
        print("  (no enabling_components)")
        return

    parent_changed = False
    new_child_ids: list[str] = []

    min_rank = IMPORTANCE_ORDER[min_importance]
    for idx, comp in enumerate(components):
        cname = comp.get("name", "?")
        print(f"  - component: {cname}")

        if comp.get("linked_entry_id"):
            print(f"    already linked to {comp['linked_entry_id']}; skipping discovery")
            new_child_ids.append(comp["linked_entry_id"])
            continue

        importance = comp.get("importance")
        if importance is None:
            print(f"    importance unset; skipping (run reconciler or set manually)")
            stats.skipped.append((cname, "importance_unset"))
            continue
        if IMPORTANCE_ORDER.get(importance, 99) > min_rank:
            print(f"    importance={importance} below threshold {min_importance}; skipping")
            stats.skipped.append((cname, f"below_threshold({importance})"))
            continue

        match = find_existing_match(cname, seeds)
        if match:
            comp["linked_entry_id"] = match
            parent_changed = True
            new_child_ids.append(match)
            stats.linked.append((parent_id, match))
            print(f"    matched existing entry {match}; linking")
            continue

        existing_ids = set(seeds)
        new_id = coin_entry_id(cname, comp.get("type", "technology"), existing_ids)
        entry_kind: Literal["stub", "full"] = "full" if depth >= 1 else "stub"
        child = build_entry_for_component(
            client=client,
            component=comp,
            parent=parent,
            entry_id=new_id,
            entry_kind=entry_kind,
            domain=parent.get("domain", ""),
        )
        if child is None:
            stats.skipped.append((cname, "no_entry_built"))
            continue
        save_seed(child)
        seeds[new_id] = child
        stats.created.append(new_id)

        comp["linked_entry_id"] = new_id
        parent_changed = True
        new_child_ids.append(new_id)
        stats.linked.append((parent_id, new_id))
        print(f"    created {new_id} ({entry_kind})")

    if parent_changed:
        save_seed(parent)

    if depth >= 1:
        for child_id in new_child_ids:
            child_entry = seeds.get(child_id)
            if not child_entry:
                continue
            if child_entry.get("entry_type") == "stub":
                # Stubs don't recurse — they were created at depth-0 quota.
                continue
            process_entry(
                client=client,
                parent_id=child_id,
                depth=depth - 1,
                seeds=seeds,
                visited=visited,
                stats=stats,
                reconcile=reconcile,
                auto_accept=auto_accept,
                min_importance=min_importance,
            )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("entry_id", help="e.g. bus:horse_omnibus")
    ap.add_argument("--depth", type=int, default=0, help="recursion depth (default 0)")
    ap.add_argument(
        "--model",
        choices=["sonnet", "opus"],
        default="sonnet",
        help="LLM model (default sonnet)",
    )
    ap.add_argument(
        "--min-importance",
        choices=["critical", "important", "incidental"],
        required=True,
        help=(
            "Minimum component importance to fully process. Components below "
            "this threshold stay as in-place placeholders inside the parent's "
            "enabling_components[] without a separate entry page being created."
        ),
    )
    ap.add_argument(
        "--no-reconcile",
        action="store_true",
        help="Skip the component-reconciliation step (don't propose new components).",
    )
    ap.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Auto-accept all reconciler-proposed component additions (no prompts).",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan without making LLM calls or writing seeds.",
    )
    args = ap.parse_args()

    if args.dry_run:
        print("--dry-run: TODO not implemented; aborting.")
        return 1

    model = DEFAULT_MODEL if args.model == "sonnet" else HIGH_QUALITY_MODEL

    # Interactive prompts need a real stdin. If we're not attached to a TTY
    # (e.g. background run, piped input), require explicit --yes so additions
    # don't get silently accepted.
    reconcile_on = not args.no_reconcile
    if reconcile_on and not args.yes and not sys.stdin.isatty():
        print(
            "error: not running in a TTY but reconciler is enabled. "
            "Re-run with --yes to auto-accept proposals, or --no-reconcile "
            "to skip the reconciliation step entirely."
        )
        return 1

    client = LLMClient(model=model)
    seeds = load_all_seeds()
    if args.entry_id not in seeds:
        print(f"error: entry {args.entry_id} not found in {SEEDS_DIR}/")
        return 1

    stats = Stats()
    started_at = datetime.now(timezone.utc)
    process_entry(
        client=client,
        parent_id=args.entry_id,
        depth=args.depth,
        seeds=seeds,
        visited=set(),
        stats=stats,
        reconcile=not args.no_reconcile,
        auto_accept=args.yes,
        min_importance=args.min_importance,
    )
    elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()

    print("\n----")
    print(f"created:    {len(stats.created)}  {stats.created}")
    print(f"linked:     {len(stats.linked)}")
    print(f"additions:  {len(stats.proposed_additions)}")
    print(f"skipped:    {len(stats.skipped)}  {stats.skipped}")
    print(f"elapsed:    {elapsed:.1f}s")
    print("\nNext:  uv run python scripts/build_db.py && uv run python scripts/build_site.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
