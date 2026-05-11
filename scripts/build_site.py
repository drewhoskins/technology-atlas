#!/usr/bin/env python3
"""Build the static tech-atlas web site under web/.

Reads data/seeds/*.json (the source of truth) and generates:
  web/index.html               — landing page, entries grouped by entry_type
  web/styles.css               — all styling
  web/entries/<id>.html        — one page per entry (id colons replaced with __)

Pure Python stdlib only. Uses string templates and html.escape() throughout.
Idempotent: running twice produces byte-identical output.

After generation, validates:
  * Each generated HTML file parses cleanly with html.parser
  * Every seed produces exactly one entry HTML file
  * Every internal href resolves to a real file
"""

from __future__ import annotations

import html
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SEEDS_DIR = REPO_ROOT / "data" / "seeds"
WEB_DIR = REPO_ROOT / "web"
ENTRIES_DIR = WEB_DIR / "entries"
IMAGES_DIR = WEB_DIR / "images"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def slug(entry_id: str) -> str:
    """Convert an entry id like 'bus:horse_omnibus' into a filesystem-safe slug.

    Entry pages live at web/entries/<slug>.html.
    """
    return entry_id.replace(":", "__")


def esc(value: Any) -> str:
    """HTML-escape a value (None becomes empty string)."""
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def load_seeds() -> list[dict]:
    """Load every JSON seed under data/seeds/ recursively."""
    seeds: list[dict] = []
    for path in sorted(SEEDS_DIR.rglob("*.json")):
        with open(path) as f:
            seeds.append(json.load(f))
    return seeds


def find_image(entry_id: str, manifest: dict | None = None) -> tuple[str, str] | None:
    """Return (image_url, alt_or_caption_hint) if an image is available for this entry.

    Resolution order:
      1. Manifest external URL — if manifest[entry_id]["url"] is set AND status is "external"
         or "verified", embed the URL directly (no local download). This is the preferred
         path: hot-link to Wikimedia Commons / other CC sources, no copyright re-distribution.
      2. Local file at web/images/<slug>.{jpg,png,gif,svg,webp} — fallback if image was
         downloaded locally (legacy path; no longer the recommended workflow).
      3. None — caller renders a placeholder.

    The first element of the returned tuple is either an external https URL or a path
    relative to the entry page (which lives in entries/).
    """
    # Manifest-driven external URL (preferred)
    if manifest is not None:
        entry = manifest.get(entry_id, {})
        status = entry.get("status", "")
        url = entry.get("url", "")
        if url and status in ("external", "verified"):
            return url, f"{entry_id}-external"

    # Local file fallback
    s = slug(entry_id)
    for ext in ("jpg", "jpeg", "png", "gif", "svg", "webp"):
        candidate = IMAGES_DIR / f"{s}.{ext}"
        if candidate.exists():
            return f"../images/{s}.{ext}", f"{entry_id}.{ext}"
    return None


def load_image_manifest() -> dict[str, dict]:
    """Load web/images/manifest.json mapping entry_id -> attribution dict.

    Returns {} if the manifest doesn't yet exist.
    """
    manifest_path = IMAGES_DIR / "manifest.json"
    if not manifest_path.exists():
        return {}
    with open(manifest_path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# source dedup + footnote numbering
# ---------------------------------------------------------------------------

class SourceCollector:
    """Collects all sources cited on a page, deduplicates, assigns footnote numbers.

    Two source dicts are considered the same if their (url, quoted_text) pair matches.
    A source can support many claims; we count uses to display a 'cited N times' note.
    """

    def __init__(self) -> None:
        # key -> {index, source_dict, count, claim_anchors}
        self._by_key: dict[tuple[str, str], dict] = {}
        self._order: list[tuple[str, str]] = []

    def cite(self, source: dict, claim_anchor: str) -> int:
        """Register a citation; return the footnote number (1-indexed)."""
        key = (source.get("url", ""), source.get("quoted_text", ""))
        if key not in self._by_key:
            self._by_key[key] = {
                "index": len(self._order) + 1,
                "source": source,
                "count": 0,
                "claim_anchors": [],
            }
            self._order.append(key)
        self._by_key[key]["count"] += 1
        self._by_key[key]["claim_anchors"].append(claim_anchor)
        return self._by_key[key]["index"]

    def all_sources(self) -> list[dict]:
        """Return the deduplicated source records in citation order."""
        return [self._by_key[k] for k in self._order]


def render_citations(sources: list[dict], collector: SourceCollector, claim_anchor: str) -> str:
    """Render a list of sources as superscript footnote refs like ⁽¹,²⁾.

    Each ref links down to #src-N in the Sources section, and the source's
    back-reference list points to the claim_anchor.
    """
    if not sources:
        return ""
    nums = [collector.cite(s, claim_anchor) for s in sources]
    parts = []
    for n in nums:
        parts.append(
            f'<a href="#src-{n}" class="cite" id="cite-{claim_anchor}-{n}" '
            f'title="Source {n}">{n}</a>'
        )
    return f'<sup class="cites">[{",".join(parts)}]</sup>'


# ---------------------------------------------------------------------------
# section renderers
# ---------------------------------------------------------------------------

DIVIDER = '<div class="divider" aria-hidden="true">&#10086;</div>'


def render_image_block(entry: dict, manifest: dict[str, dict]) -> str:
    """Hero image block (or styled placeholder if no image)."""
    img = find_image(entry["id"], manifest)
    attribution = manifest.get(entry["id"], {})
    if img:
        rel_url, _ = img
        caption_parts = []
        title = attribution.get("title") or attribution.get("description") or ""
        credit = attribution.get("credit") or ""
        license_ = attribution.get("license") or ""
        source_url = attribution.get("source_url") or ""
        note = attribution.get("note") or ""
        if title:
            caption_parts.append(f'<span class="caption-title">{esc(title)}</span>')
        if credit:
            caption_parts.append(f'Credit: {esc(credit)}.')
        if license_:
            caption_parts.append(f'License: {esc(license_)}.')
        if source_url:
            caption_parts.append(
                f'<a href="{esc(source_url)}" rel="noopener" target="_blank">Source</a>.'
            )
        if note:
            caption_parts.append(f'<em>{esc(note)}</em>')
        caption = " ".join(caption_parts) or "No attribution recorded."
        return (
            '<figure class="hero">\n'
            f'  <img src="{esc(rel_url)}" alt="{esc(entry["name"])}" loading="lazy" />\n'
            f'  <figcaption>{caption}</figcaption>\n'
            '</figure>'
        )
    # Placeholder: a stylised text card.
    return (
        '<figure class="hero placeholder">\n'
        '  <div class="placeholder-card">\n'
        f'    <div class="placeholder-name">{esc(entry["name"])}</div>\n'
        '    <div class="placeholder-mark">&#8258;</div>\n'
        '  </div>\n'
        '  <figcaption><em>No CC-licensed image available for this entry.</em></figcaption>\n'
        '</figure>'
    )


def render_description(entry: dict, collector: SourceCollector) -> str:
    desc = entry.get("description", "")
    if not desc:
        return ""
    cites = render_citations(entry.get("description_sources", []) or [], collector, "desc")
    return (
        '<section class="description" id="description">\n'
        '  <h2>Description</h2>\n'
        f'  <p>{esc(desc)}{cites}</p>\n'
        '</section>'
    )


def _link_for_linked_entry(linked_id: str | None, all_ids: set[str]) -> str | None:
    if linked_id and linked_id in all_ids:
        return f"./{slug(linked_id)}.html"
    return None


def compute_backlinks(by_id: dict[str, dict]) -> dict[str, dict[str, list[str]]]:
    """For each entry id, find which other entries reference it and how.

    Returns: {target_id: {"used_by_components": [referrer_id, ...],
                           "succeeded_by":      [referrer_id, ...]}}

    'Used as a component of' is the inverse of `enabling_components.linked_entry_id`.
    'Succeeded by' is the inverse of `predecessors.linked_entry_id`.
    Variant->category linkage is handled separately by render_variant_links.
    """
    bl: dict[str, dict[str, list[str]]] = {
        eid: {"used_by_components": [], "succeeded_by": []} for eid in by_id
    }
    for entry in by_id.values():
        for comp in entry.get("enabling_components", []) or []:
            target = comp.get("linked_entry_id")
            if target and target in bl and target != entry["id"]:
                bl[target]["used_by_components"].append(entry["id"])
        for pred in entry.get("predecessors", []) or []:
            target = pred.get("linked_entry_id")
            if target and target in bl and target != entry["id"]:
                bl[target]["succeeded_by"].append(entry["id"])
    # Dedup + stable order by referrer name.
    for target_id, groups in bl.items():
        for k, refs in groups.items():
            unique = sorted(set(refs), key=lambda r: by_id[r]["name"])
            groups[k] = unique
    return bl


def render_backlinks(entry: dict, backlinks: dict, by_id: dict) -> str:
    """Render the 'Referenced by' section for an entry, if any backlinks exist."""
    bl = backlinks.get(entry["id"], {})
    used_by = bl.get("used_by_components", [])
    succeeded_by = bl.get("succeeded_by", [])
    # Also surface child variants here for category entries — though they're already
    # listed in the Variants section, this groups all incoming references in one place.
    children = sorted(
        [e for e in by_id.values() if e.get("parent_id") == entry["id"]],
        key=lambda e: e["name"],
    )
    if not (used_by or succeeded_by or children):
        return ""
    parts = []
    if children:
        items = "".join(
            f'<li><a href="./{esc(slug(c["id"]))}.html">{esc(c["name"])}</a>'
            f' <span class="mono backlink-id">{esc(c["id"])}</span></li>'
            for c in children
        )
        parts.append(
            '<div class="backlink-group">'
            '<h3>Variants of this category</h3>'
            f'<ul class="backlink-list">{items}</ul></div>'
        )
    if used_by:
        items = "".join(
            f'<li><a href="./{esc(slug(rid))}.html">{esc(by_id[rid]["name"])}</a>'
            f' <span class="mono backlink-id">{esc(rid)}</span></li>'
            for rid in used_by
        )
        parts.append(
            '<div class="backlink-group">'
            '<h3>Used as a component of</h3>'
            f'<ul class="backlink-list">{items}</ul></div>'
        )
    if succeeded_by:
        items = "".join(
            f'<li><a href="./{esc(slug(rid))}.html">{esc(by_id[rid]["name"])}</a>'
            f' <span class="mono backlink-id">{esc(rid)}</span></li>'
            for rid in succeeded_by
        )
        parts.append(
            '<div class="backlink-group">'
            '<h3>Succeeded by</h3>'
            f'<ul class="backlink-list">{items}</ul></div>'
        )
    return f"""
<section class="backlinks" id="referenced-by">
  <h2>Referenced by</h2>
  <p class="backlinks-note">Inverse view of the tech tree — other atlas entries that point at this one.</p>
  {"".join(parts)}
</section>"""


def render_innovators(entry: dict, collector: SourceCollector, all_ids: set[str]) -> str:
    items = entry.get("innovators", []) or []
    if not items:
        return ""
    rows = []
    for i, person in enumerate(items):
        anchor = f"innov-{i}"
        cites = render_citations(person.get("sources", []) or [], collector, anchor)
        recog = person.get("recognition_status") or ""
        recog_html = (
            f'<span class="badge recog recog-{esc(recog)}">{esc(recog.replace("_", " "))}</span>'
            if recog else ""
        )
        year = person.get("year")
        country = person.get("country") or ""
        contribution = person.get("contribution") or ""
        rows.append(f"""
    <article class="innovator-card" id="{anchor}">
      <header>
        <h3 class="innovator-name">{esc(person.get("name", ""))}{cites}</h3>
        <div class="innovator-meta">
          {f'<span class="mono year">{esc(year)}</span>' if year else ''}
          {f'<span class="country">{esc(country)}</span>' if country else ''}
          {recog_html}
        </div>
      </header>
      <p class="innovator-role"><strong>Role.</strong> {esc(person.get("role", ""))}</p>
      {f'<p class="innovator-contribution"><strong>Contribution.</strong> {esc(contribution)}</p>' if contribution else ''}
    </article>""".rstrip())
    return f"""
<section class="innovators" id="innovators">
  <h2>Innovators</h2>
  <div class="innovator-grid">{"".join(rows)}
  </div>
</section>"""


def render_predecessors(entry: dict, collector: SourceCollector, all_ids: set[str]) -> str:
    items = entry.get("predecessors", []) or []
    if not items:
        return ""
    li = []
    for i, p in enumerate(items):
        anchor = f"pred-{i}"
        cites = render_citations(p.get("sources", []) or [], collector, anchor)
        link = _link_for_linked_entry(p.get("linked_entry_id"), all_ids)
        name_html = esc(p.get("name", ""))
        if link:
            name_html = f'<a href="{esc(link)}">{name_html}</a>'
        rel = p.get("relationship") or ""
        year = p.get("year")
        brief = p.get("brief") or ""
        li.append(f"""
    <li id="{anchor}">
      <div class="pred-head">
        <span class="pred-name">{name_html}</span>
        <span class="badge rel rel-{esc(rel)}">{esc(rel.replace("_", " "))}</span>
        {f'<span class="mono year">{esc(year)}</span>' if year else ''}
        {cites}
      </div>
      {f'<p class="brief">{esc(brief)}</p>' if brief else ''}
    </li>""".rstrip())
    return f"""
<section class="predecessors" id="predecessors">
  <h2>Predecessors</h2>
  <ul class="dim-list">{"".join(li)}
  </ul>
</section>"""


def render_enabling_components(entry: dict, collector: SourceCollector, all_ids: set[str]) -> str:
    items = entry.get("enabling_components", []) or []
    if not items:
        return ""
    li = []
    for i, c in enumerate(items):
        anchor = f"comp-{i}"
        cites = render_citations(c.get("sources", []) or [], collector, anchor)
        link = _link_for_linked_entry(c.get("linked_entry_id"), all_ids)
        name_html = esc(c.get("name", ""))
        if link:
            name_html = f'<a href="{esc(link)}">{name_html}</a>'
        type_ = c.get("type") or ""
        role = c.get("role") or ""
        brief = c.get("brief") or ""
        li.append(f"""
    <li id="{anchor}">
      <div class="comp-head">
        <span class="comp-name">{name_html}</span>
        <span class="badge type type-{esc(type_)}">{esc(type_)}</span>
        {cites}
      </div>
      {f'<p class="role"><strong>Role.</strong> {esc(role)}</p>' if role else ''}
      {f'<p class="brief">{esc(brief)}</p>' if brief else ''}
    </li>""".rstrip())
    return f"""
<section class="enabling-components" id="enabling-components">
  <h2>Enabling components</h2>
  <ul class="dim-list">{"".join(li)}
  </ul>
</section>"""


def render_failed_alternatives(entry: dict, collector: SourceCollector) -> str:
    items = entry.get("failed_alternatives", []) or []
    if not items:
        return ""
    li = []
    for i, f in enumerate(items):
        anchor = f"failed-{i}"
        cites = render_citations(f.get("sources", []) or [], collector, anchor)
        period = f.get("period") or ""
        li.append(f"""
    <li id="{anchor}">
      <div class="failed-head">
        <span class="failed-name">{esc(f.get("name", ""))}</span>
        {f'<span class="mono period">{esc(period)}</span>' if period else ''}
        {cites}
      </div>
      <p class="why-failed"><strong>Why it failed.</strong> {esc(f.get("why_failed", ""))}</p>
    </li>""".rstrip())
    return f"""
<section class="failed-alternatives" id="failed-alternatives">
  <h2>Failed alternatives</h2>
  <ul class="dim-list">{"".join(li)}
  </ul>
</section>"""


def render_funders(entry: dict, collector: SourceCollector) -> str:
    items = entry.get("funders", []) or []
    if not items:
        return ""
    li = []
    for i, f in enumerate(items):
        anchor = f"fund-{i}"
        cites = render_citations(f.get("sources", []) or [], collector, anchor)
        ftype = f.get("type") or ""
        period = f.get("period") or ""
        brief = f.get("brief") or ""
        li.append(f"""
    <li id="{anchor}">
      <div class="fund-head">
        <span class="fund-name">{esc(f.get("entity", ""))}</span>
        <span class="badge ftype ftype-{esc(ftype)}">{esc(ftype.replace("_", " "))}</span>
        {f'<span class="mono period">{esc(period)}</span>' if period else ''}
        {cites}
      </div>
      {f'<p class="brief">{esc(brief)}</p>' if brief else ''}
    </li>""".rstrip())
    return f"""
<section class="funders" id="funders">
  <h2>Funders</h2>
  <ul class="dim-list">{"".join(li)}
  </ul>
</section>"""


def render_table(
    title: str,
    section_id: str,
    rows: list[dict],
    columns: list[tuple[str, str]],
    collector: SourceCollector,
    anchor_prefix: str,
    sort_by: str | None = "year",
) -> str:
    """Generic chronological table renderer.

    columns: list of (key, header) pairs. Each row dict supplies `sources` for cites.
    sort_by: key to sort rows by (chronological by default).
    """
    if not rows:
        return ""
    sorted_rows = list(rows)
    if sort_by:
        sorted_rows.sort(key=lambda r: (r.get(sort_by) is None, r.get(sort_by)))
    body = []
    for i, r in enumerate(sorted_rows):
        anchor = f"{anchor_prefix}-{i}"
        cites = render_citations(r.get("sources", []) or [], collector, anchor)
        cells = []
        for j, (key, _) in enumerate(columns):
            val = r.get(key)
            if val is None:
                cell = ""
            elif key == "year":
                cell = f'<span class="mono">{esc(val)}</span>'
            elif key in ("effect", "milestone", "event_type"):
                cell = f'<span class="badge {esc(key)} {esc(key)}-{esc(val)}">{esc(str(val).replace("_", " "))}</span>'
            else:
                cell = esc(val)
            # Append citations to the LAST visible cell so they stay near the row.
            if j == len(columns) - 1:
                cell = f'{cell}{cites}'
            cells.append(f"<td>{cell}</td>")
        body.append(f'    <tr id="{anchor}">{"".join(cells)}</tr>')
    headers = "".join(f"<th>{esc(h)}</th>" for _, h in columns)
    return f"""
<section class="{section_id}" id="{section_id}">
  <h2>{esc(title)}</h2>
  <table class="dim-table">
    <thead><tr>{headers}</tr></thead>
    <tbody>
{chr(10).join(body)}
    </tbody>
  </table>
</section>"""


def render_sources_section(collector: SourceCollector) -> str:
    """Render the deduplicated Sources block at the bottom of the page."""
    sources = collector.all_sources()
    if not sources:
        return ""
    items = []
    for entry in sources:
        n = entry["index"]
        s = entry["source"]
        count = entry["count"]
        url = s.get("url", "")
        fetched = s.get("fetched_at", "")
        ai_or_human = s.get("ai_or_human", "")
        confidence = s.get("confidence")
        quoted = s.get("quoted_text", "")
        # Extract domain for a clean label.
        domain_match = re.match(r"https?://([^/]+)", url)
        host = domain_match.group(1) if domain_match else url
        # Simple licensing/redistributable note: we don't have it on the source itself,
        # so we record the available metadata transparently.
        meta_bits = []
        meta_bits.append(f'<span class="src-host mono">{esc(host)}</span>')
        if fetched:
            meta_bits.append(f'<span class="src-fetched mono">fetched {esc(fetched[:10])}</span>')
        if ai_or_human:
            meta_bits.append(f'<span class="src-origin">{esc(ai_or_human)}-extracted</span>')
        if confidence is not None:
            meta_bits.append(f'<span class="src-confidence">conf {esc(confidence)}</span>')
        meta_bits.append(
            f'<span class="src-count">cited {count} time{"s" if count != 1 else ""} on this page</span>'
        )
        items.append(f"""
    <li class="source-item" id="src-{n}">
      <div class="src-num mono">[{n}]</div>
      <div class="src-body">
        <div class="src-meta">{" &middot; ".join(meta_bits)}</div>
        <a class="src-url" href="{esc(url)}" rel="noopener" target="_blank">{esc(url)}</a>
        <blockquote class="src-quote">{esc(quoted)}</blockquote>
      </div>
    </li>""".rstrip())
    return f"""
<section class="sources" id="sources">
  <h2>Sources</h2>
  <p class="sources-note">
    Every claim above is backed by a verbatim excerpt from the source listed here.
    Click any citation number to jump to its source. Sources are deduplicated:
    a single source may support several claims on this page.
  </p>
  <ol class="source-list">{"".join(items)}
  </ol>
</section>"""


# ---------------------------------------------------------------------------
# page templates
# ---------------------------------------------------------------------------

HEAD = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title} &middot; Tech Atlas</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;700&family=Lora:ital,wght@0,400;0,500;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap" />
  <link rel="stylesheet" href="{css_href}" />
</head>
<body>
"""

FOOTER_TEMPLATE = """\
<footer class="atlas-footer">
  <div class="divider" aria-hidden="true">&#10086;</div>
  <p class="footer-meta">
    <span class="mono">Atlas entry: {entry_id}</span>
    {last_updated_block}
  </p>
  <p class="footer-nav"><a href="{index_href}">&larr; back to the index</a></p>
</footer>
</body>
</html>
"""


def page_head(title: str, css_href: str) -> str:
    return HEAD.format(title=esc(title), css_href=esc(css_href))


def page_footer(entry_id: str, index_href: str, last_updated: str | None = None) -> str:
    lu = (
        f'<span class="footer-sep">&middot;</span>'
        f'<span class="mono">Last updated: {esc(last_updated)}</span>'
        if last_updated else ""
    )
    return FOOTER_TEMPLATE.format(
        entry_id=esc(entry_id),
        index_href=esc(index_href),
        last_updated_block=lu,
    )


# ---------------------------------------------------------------------------
# entry page generation
# ---------------------------------------------------------------------------

def render_breadcrumb(entry: dict, by_id: dict[str, dict]) -> str:
    parent_id = entry.get("parent_id")
    if parent_id and parent_id in by_id:
        parent = by_id[parent_id]
        return (
            '<nav class="breadcrumb">'
            '<a href="../index.html">Atlas</a> &rsaquo; '
            f'<a href="./{esc(slug(parent["id"]))}.html">{esc(parent["name"])}</a> '
            f'&rsaquo; <span>{esc(entry["name"])}</span>'
            '</nav>'
        )
    return (
        '<nav class="breadcrumb">'
        '<a href="../index.html">Atlas</a> &rsaquo; '
        f'<span>{esc(entry["name"])}</span>'
        '</nav>'
    )


def render_entry_header(entry: dict, by_id: dict[str, dict]) -> str:
    breadcrumb = render_breadcrumb(entry, by_id)
    return f"""
<header class="entry-header">
  {breadcrumb}
  <h1 class="entry-name">{esc(entry["name"])}</h1>
  <div class="entry-meta">
    <span class="badge etype etype-{esc(entry.get("entry_type"))}">{esc(entry.get("entry_type", ""))}</span>
    <span class="badge domain">{esc(entry.get("domain", ""))}</span>
    <span class="mono entry-id">{esc(entry["id"])}</span>
  </div>
</header>"""


def find_latest_fetched_at(entry: dict) -> str | None:
    """Return the latest fetched_at timestamp across all sources on the entry."""
    latest: str | None = None
    for sources_list in _all_source_lists(entry):
        for s in sources_list or []:
            f = s.get("fetched_at")
            if f and (latest is None or f > latest):
                latest = f
    return latest[:10] if latest else None


def _all_source_lists(entry: dict):
    yield entry.get("description_sources")
    for k in (
        "innovators", "predecessors", "enabling_components", "failed_alternatives",
        "funders", "regulatory_moments", "geographic_diffusion", "key_dates",
    ):
        for item in entry.get(k, []) or []:
            yield item.get("sources")


def render_variant_links(category: dict, by_id: dict[str, dict]) -> str:
    """For category pages: list child variants with brief descriptions."""
    children = [e for e in by_id.values() if e.get("parent_id") == category["id"]]
    if not children:
        return ""
    children.sort(key=lambda e: e["name"])
    li = []
    for child in children:
        # First-sentence preview of the child description.
        desc = (child.get("description") or "").strip()
        preview = desc.split(". ")[0][:240] + "."
        # Category pages live at web/entries/<slug>.html, so variant links are
        # sibling-relative.
        li.append(f"""
    <li>
      <a class="variant-link" href="./{esc(slug(child["id"]))}.html">
        <div class="variant-name">{esc(child["name"])}</div>
        <div class="variant-preview">{esc(preview)}</div>
      </a>
    </li>""".rstrip())
    return f"""
<section class="variants" id="variants">
  <h2>Variants</h2>
  <ul class="variant-list">{"".join(li)}
  </ul>
</section>"""


def render_related_topics(category: dict, by_id: dict[str, dict]) -> str:
    """Topics in the same domain, not under this category."""
    related = [
        e for e in by_id.values()
        if e.get("entry_type") == "topic"
        and e.get("domain") == category.get("domain")
        and e.get("parent_id") != category["id"]
    ]
    if not related:
        return ""
    related.sort(key=lambda e: e["name"])
    li = []
    for s in related:
        desc = (s.get("description") or "").strip()
        preview = desc.split(". ")[0][:240] + "."
        # Category pages live at web/entries/<slug>.html, so links to other
        # entry pages are sibling-relative.
        li.append(f"""
    <li>
      <a class="variant-link" href="./{esc(slug(s["id"]))}.html">
        <div class="variant-name">{esc(s["name"])}</div>
        <div class="variant-preview">{esc(preview)}</div>
      </a>
    </li>""".rstrip())
    return f"""
<section class="related-topics" id="related-topics">
  <h2>Related topics</h2>
  <ul class="variant-list">{"".join(li)}
  </ul>
</section>"""


def build_category_page(
    entry: dict,
    by_id: dict[str, dict],
    manifest: dict[str, dict],
    backlinks: dict,
) -> str:
    """Light layout for a category entry."""
    collector = SourceCollector()
    # Image lives in web/images relative to this entry page (which is in entries/),
    # but category pages are not in entries/. We render an image block that uses
    # relative paths from the index level.
    image_block = render_category_image(entry, manifest)
    desc_html = render_description_for_category(entry, collector)
    variants_html = render_variant_links(entry, by_id)
    topics_html = render_related_topics(entry, by_id)
    # Categories can also be linked-to (e.g. BRT lists `bus` as a component).
    # Render only the "used as component of" / "succeeded by" parts; skip variants
    # since they have their own dedicated section above.
    cat_backlinks = backlinks.get(entry["id"], {})
    backlinks_html = ""
    if cat_backlinks.get("used_by_components") or cat_backlinks.get("succeeded_by"):
        # Build a lightweight wrapper that omits the variants list.
        synthetic = {"id": entry["id"]}
        synthetic_bl = {
            entry["id"]: {
                "used_by_components": cat_backlinks.get("used_by_components", []),
                "succeeded_by": cat_backlinks.get("succeeded_by", []),
            }
        }
        # by_id_no_children prevents render_backlinks from re-listing variants.
        by_id_no_children = {
            k: v for k, v in by_id.items() if v.get("parent_id") != entry["id"]
        }
        # Include the entry itself so that lookups work.
        by_id_no_children[entry["id"]] = entry
        backlinks_html = render_backlinks(synthetic, synthetic_bl, by_id_no_children)
    keydates_html = render_table(
        "Key dates", "key-dates", entry.get("key_dates", []) or [],
        [("year", "Year"), ("event", "Event"), ("event_type", "Type"), ("significance", "Significance")],
        collector, "kd", sort_by="year",
    )
    sources_html = render_sources_section(collector)
    body = f"""
<main class="entry category-entry">
  {render_category_header(entry)}
  {image_block}
  <section class="defining-innovation" id="defining-innovation">
    <h2>Defining innovation</h2>
    {desc_html}
  </section>
  {variants_html}
  {topics_html}
  {backlinks_html}
  {keydates_html}
  {sources_html}
</main>
"""
    last_updated = find_latest_fetched_at(entry)
    head = page_head(entry["name"], "../styles.css")
    foot = page_footer(entry["id"], "../index.html", last_updated)
    return head + body + foot


def render_category_header(entry: dict) -> str:
    return f"""
<header class="entry-header category-header">
  <nav class="breadcrumb"><a href="../index.html">Atlas</a> &rsaquo; <span>{esc(entry["name"])}</span></nav>
  <h1 class="entry-name">{esc(entry["name"])}</h1>
  <div class="entry-meta">
    <span class="badge etype etype-category">category</span>
    <span class="badge domain">{esc(entry.get("domain", ""))}</span>
    <span class="mono entry-id">{esc(entry["id"])}</span>
  </div>
</header>"""


def render_category_image(entry: dict, manifest: dict[str, dict]) -> str:
    img = find_image(entry["id"], manifest)
    attribution = manifest.get(entry["id"], {})
    if img:
        rel_url, _ = img
        title = attribution.get("title") or ""
        credit = attribution.get("credit") or ""
        license_ = attribution.get("license") or ""
        source_url = attribution.get("source_url") or ""
        note = attribution.get("note") or ""
        caption_parts = []
        if title:
            caption_parts.append(f'<span class="caption-title">{esc(title)}</span>')
        if credit:
            caption_parts.append(f'Credit: {esc(credit)}.')
        if license_:
            caption_parts.append(f'License: {esc(license_)}.')
        if source_url:
            caption_parts.append(
                f'<a href="{esc(source_url)}" rel="noopener" target="_blank">Source</a>.'
            )
        if note:
            caption_parts.append(f'<em>{esc(note)}</em>')
        caption = " ".join(caption_parts) or "No attribution recorded."
        return (
            '<figure class="hero">\n'
            f'  <img src="{esc(rel_url)}" alt="{esc(entry["name"])}" loading="lazy" />\n'
            f'  <figcaption>{caption}</figcaption>\n'
            '</figure>'
        )
    return (
        '<figure class="hero placeholder">\n'
        '  <div class="placeholder-card">\n'
        f'    <div class="placeholder-name">{esc(entry["name"])}</div>\n'
        '    <div class="placeholder-mark">&#8258;</div>\n'
        '  </div>\n'
        '  <figcaption><em>No CC-licensed image available for this entry.</em></figcaption>\n'
        '</figure>'
    )


def render_description_for_category(entry: dict, collector: SourceCollector) -> str:
    """Categories lead with the description; render without an extra h2 wrapper here."""
    desc = entry.get("description", "")
    if not desc:
        return ""
    cites = render_citations(entry.get("description_sources", []) or [], collector, "desc")
    return f'<p class="lead">{esc(desc)}{cites}</p>'


# Image-block path adjustment for category pages -----------------------------
# (category pages live in web/images path "../images/..." since they will be
#  written to web/entries/<slug>.html). We standardise: ALL pages live in
#  entries/, including categories, so all image refs are "../images/...".
# ---------------------------------------------------------------------------

def build_rich_page(
    entry: dict,
    by_id: dict[str, dict],
    manifest: dict[str, dict],
    backlinks: dict,
) -> str:
    """Variant / topic / stub page — full data layout."""
    collector = SourceCollector()
    all_ids = set(by_id.keys())

    image_block = render_image_block(entry, manifest)
    desc_html = render_description(entry, collector)
    backlinks_html = render_backlinks(entry, backlinks, by_id)
    innov = render_innovators(entry, collector, all_ids)
    pred = render_predecessors(entry, collector, all_ids)
    comp = render_enabling_components(entry, collector, all_ids)
    failed = render_failed_alternatives(entry, collector)
    funders = render_funders(entry, collector)

    regulatory = render_table(
        "Regulatory moments", "regulatory-moments",
        entry.get("regulatory_moments", []) or [],
        [("year", "Year"), ("jurisdiction", "Jurisdiction"),
         ("description", "Description"), ("effect", "Effect")],
        collector, "reg", sort_by="year",
    )
    geo = render_table(
        "Geographic diffusion", "geographic-diffusion",
        entry.get("geographic_diffusion", []) or [],
        [("year", "Year"), ("place", "Place"),
         ("milestone", "Milestone"), ("brief", "Brief")],
        collector, "geo", sort_by="year",
    )
    keydates = render_table(
        "Key dates", "key-dates",
        entry.get("key_dates", []) or [],
        [("year", "Year"), ("event", "Event"),
         ("event_type", "Type"), ("significance", "Significance")],
        collector, "kd", sort_by="year",
    )
    sources_section = render_sources_section(collector)

    body = f"""
<main class="entry rich-entry">
  {render_entry_header(entry, by_id)}
  {image_block}
  {desc_html}
  {backlinks_html}
  {DIVIDER if (innov or pred or comp) else ""}
  {innov}
  {pred}
  {comp}
  {DIVIDER if (failed or funders) else ""}
  {failed}
  {funders}
  {DIVIDER if (regulatory or geo or keydates) else ""}
  {regulatory}
  {geo}
  {keydates}
  {DIVIDER if sources_section else ""}
  {sources_section}
</main>
"""
    last_updated = find_latest_fetched_at(entry)
    head = page_head(entry["name"], "../styles.css")
    foot = page_footer(entry["id"], "../index.html", last_updated)
    return head + body + foot


# ---------------------------------------------------------------------------
# index page
# ---------------------------------------------------------------------------

ENTRY_TYPE_ORDER = ["category", "variant", "topic", "stub"]
ENTRY_TYPE_LABELS = {
    "category": "Categories",
    "variant": "Variants",
    "topic": "Topics",
    "stub": "Brief topics",
}
ENTRY_TYPE_BLURBS = {
    "category": "Umbrella concepts that group their variants. Lead with the defining innovation.",
    "variant": "A specific kind within a category — e.g. a particular propulsion class of bus.",
    "topic": "A technology or phenomenon that isn't a variant of a category in the atlas.",
    "stub": "Lightly-described entries that other technologies reference. Stub means thin, not less real.",
}


def build_index(entries: list[dict], by_id: dict[str, dict]) -> str:
    body = f"""
<main class="index">
  <header class="atlas-header">
    <p class="kicker">An empirical atlas of frontier technology and its innovators</p>
    <h1>Technology Atlas</h1>
    <p class="lede">
      A curated graph of technologies, traced through their predecessors,
      enabling components, funders, regulatory moments, geographic diffusion,
      and key dates. Every fact carries an inline citation back to a verbatim
      source excerpt.
    </p>
    <div class="divider" aria-hidden="true">&#8258;</div>
  </header>

  <section class="doors">
    <article class="door">
      <h2>Browse the atlas</h2>
      <p>
        The atlas currently covers one technology in depth: the bus. Every
        variant, component, predecessor, innovator, and regulatory moment is
        reachable from there.
      </p>
      <p class="door-cta">
        <a class="door-link" href="./entries/bus.html">Bus &rsaquo;</a>
      </p>
    </article>

    <article class="door">
      <h2>For LLMs &amp; developers</h2>
      <p>
        The atlas ships as a SQLite database with a documented schema. Clone
        the repo and query it locally; a hosted API and MCP endpoint are
        planned.
      </p>
      <p class="door-cta">
        <a class="door-link" href="https://github.com/drewhoskins/technology-atlas">GitHub repo &rsaquo;</a>
      </p>
    </article>
  </section>

  <footer class="index-footer">
    <p class="collab-invite">
      This is an early prototype, growing one technology at a time. If you have
      sources, corrections, or want to help build it out, get in touch via
      <a href="https://drewhoskins.carrd.co/" target="_blank" rel="noopener">drewhoskins.carrd.co</a>.
    </p>
  </footer>
</main>
"""
    head = page_head("Technology Atlas", "./styles.css")
    return head + body + "</body></html>\n"


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

CSS = """\
/* Tech Atlas — steampunk / 1900-print reference book aesthetic.
 * Limited palette, transitional serifs, monospace for technical detail.
 * No flat-design sterility, no gears, no goggles — restrained.
 */

:root {
  --brass: #B5895A;
  --brass-dark: #8C6438;
  --copper: #3F6B5E;
  --parchment: #F4EBD0;
  --parchment-light: #FBF6E4;
  --parchment-dark: #E8DBB8;
  --sepia: #3A2E1F;
  --sepia-soft: #5A4A35;
  --crimson: #8B2E2A;
  --rule: #C9B384;
  --shadow: rgba(58, 46, 31, 0.18);

  --serif-head: "Playfair Display", Georgia, "Times New Roman", serif;
  --serif-body: "Lora", Georgia, "Iowan Old Style", serif;
  --mono: "IBM Plex Mono", "Courier New", Courier, monospace;
}

* { box-sizing: border-box; }

html, body {
  margin: 0;
  padding: 0;
  background: var(--parchment);
  color: var(--sepia);
  font-family: var(--serif-body);
  font-size: 17px;
  line-height: 1.6;
}

body {
  background-image:
    radial-gradient(ellipse at 20% 0%, rgba(181, 137, 90, 0.08), transparent 60%),
    radial-gradient(ellipse at 80% 100%, rgba(63, 107, 94, 0.05), transparent 60%);
  min-height: 100vh;
}

main {
  max-width: 980px;
  margin: 0 auto;
  padding: 3rem 2rem 6rem 2rem;
}

a { color: var(--copper); text-decoration: underline; text-underline-offset: 2px; }
a:hover { color: var(--crimson); }

h1, h2, h3 {
  font-family: var(--serif-head);
  color: var(--sepia);
  font-weight: 700;
  letter-spacing: 0.01em;
}

h1 {
  font-size: 2.7rem;
  line-height: 1.15;
  margin: 0.4rem 0 0.6rem 0;
}

h2 {
  font-size: 1.55rem;
  margin: 2.6rem 0 0.9rem 0;
  border-bottom: 1px solid var(--rule);
  padding-bottom: 0.4rem;
  color: var(--brass-dark);
}

h3 { font-size: 1.15rem; margin: 1.2rem 0 0.4rem 0; }

p { margin: 0 0 1rem 0; }

.mono { font-family: var(--mono); font-size: 0.92em; color: var(--sepia-soft); }

/* ---- Atlas header (index) ---- */
.atlas-header {
  text-align: center;
  padding: 2rem 0 1rem 0;
  border-bottom: 1px double var(--rule);
  margin-bottom: 2.5rem;
}
.kicker {
  font-family: var(--mono);
  text-transform: uppercase;
  letter-spacing: 0.18em;
  font-size: 0.78rem;
  color: var(--brass-dark);
  margin: 0 0 0.6rem 0;
}
.atlas-header h1 {
  font-size: 3.4rem;
  margin: 0.2rem 0 0.5rem 0;
  font-style: normal;
}
.lede {
  max-width: 640px;
  margin: 1rem auto 1.4rem auto;
  font-size: 1.05rem;
  font-style: italic;
  color: var(--sepia-soft);
}

/* ---- Divider glyph ---- */
.divider {
  text-align: center;
  margin: 2.4rem 0;
  color: var(--brass);
  font-size: 1.6rem;
  letter-spacing: 0.4em;
  user-select: none;
}

/* ---- Index entry grid ---- */
.type-section { margin-bottom: 3rem; }
.type-blurb {
  font-style: italic;
  color: var(--sepia-soft);
  margin-top: -0.4rem;
}
.entry-grid {
  list-style: none;
  padding: 0;
  margin: 1.5rem 0 0 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
  gap: 1.2rem;
}
.entry-card {
  background: var(--parchment-light);
  border: 1px solid var(--rule);
  border-top: 3px solid var(--brass);
  box-shadow: 0 2px 0 var(--shadow);
  padding: 0;
  transition: transform 0.12s ease, box-shadow 0.12s ease;
}
.entry-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 0 var(--shadow);
}
.entry-card a {
  display: block;
  padding: 1rem 1.1rem 1.1rem 1.1rem;
  text-decoration: none;
  color: var(--sepia);
}
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 0.6rem;
  margin-bottom: 0.4rem;
}
.card-name {
  font-family: var(--serif-head);
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--sepia);
}
.card-meta {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 0.5rem;
}
.entry-id-small { font-size: 0.82rem; }
.card-preview {
  margin: 0;
  font-size: 0.94rem;
  color: var(--sepia-soft);
}

/* ---- Entry pages ---- */
.entry-header {
  margin-bottom: 1.8rem;
  padding-bottom: 1rem;
  border-bottom: 1px double var(--rule);
}
.breadcrumb {
  font-family: var(--mono);
  font-size: 0.85rem;
  color: var(--sepia-soft);
  margin-bottom: 0.6rem;
}
.breadcrumb a { color: var(--copper); }
.entry-meta {
  margin-top: 0.6rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}
.entry-id { font-size: 0.85rem; }

/* ---- Badges ---- */
.badge {
  display: inline-block;
  padding: 0.18rem 0.55rem;
  font-family: var(--mono);
  font-size: 0.78rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  border: 1px solid var(--brass);
  background: var(--parchment-light);
  color: var(--brass-dark);
  border-radius: 2px;
}
.badge.domain { color: var(--copper); border-color: var(--copper); }
.badge.etype-category { background: var(--brass); color: var(--parchment); border-color: var(--brass-dark); }
.badge.etype-variant  { background: var(--copper); color: var(--parchment); border-color: var(--copper); }
.badge.etype-topic { background: var(--crimson); color: var(--parchment); border-color: var(--crimson); }
.badge.etype-stub { background: var(--parchment-dark); color: var(--sepia); }

.badge.recog-headline { background: var(--brass); color: var(--parchment); border-color: var(--brass-dark); }
.badge.recog-well_known { color: var(--brass-dark); }
.badge.recog-underrecognized { color: var(--crimson); border-color: var(--crimson); }
.badge.recog-obscure { color: var(--sepia-soft); border-color: var(--sepia-soft); border-style: dashed; }

.badge.rel-evolved_from { color: var(--copper); border-color: var(--copper); }
.badge.rel-competing_predecessor { color: var(--crimson); border-color: var(--crimson); }
.badge.rel-inspiration { color: var(--brass-dark); border-color: var(--brass-dark); border-style: dashed; }

.badge.type-technology { color: var(--copper); border-color: var(--copper); }
.badge.type-infrastructure { color: var(--brass-dark); border-color: var(--brass-dark); }
.badge.type-practice { color: var(--sepia); border-style: dashed; }
.badge.type-process { color: var(--sepia); border-style: dashed; }
.badge.type-standard { color: var(--copper); border-color: var(--copper); }

.badge.ftype-government { background: var(--copper); color: var(--parchment); border-color: var(--copper); }
.badge.ftype-private { color: var(--brass-dark); border-color: var(--brass-dark); }
.badge.ftype-philanthropic { color: var(--copper); border-color: var(--copper); }
.badge.ftype-venture { color: var(--crimson); border-color: var(--crimson); }
.badge.ftype-public_subscription { color: var(--brass-dark); border-color: var(--brass-dark); border-style: dashed; }
.badge.ftype-other { color: var(--sepia-soft); border-color: var(--sepia-soft); }

.badge.effect-enabling { background: var(--copper); color: var(--parchment); border-color: var(--copper); }
.badge.effect-restricting { background: var(--crimson); color: var(--parchment); border-color: var(--crimson); }
.badge.effect-mixed { color: var(--brass-dark); border-color: var(--brass-dark); border-style: dashed; }
.badge.effect-neutral { color: var(--sepia-soft); }

.badge.event_type-invention { background: var(--brass); color: var(--parchment); border-color: var(--brass-dark); }
.badge.event_type-patent { color: var(--brass-dark); border-color: var(--brass-dark); }
.badge.event_type-scaling { color: var(--copper); border-color: var(--copper); }
.badge.event_type-regulatory { color: var(--crimson); border-color: var(--crimson); }
.badge.event_type-adoption { background: var(--copper); color: var(--parchment); border-color: var(--copper); }

.badge.milestone-first { background: var(--brass); color: var(--parchment); border-color: var(--brass-dark); }
.badge.milestone-1pct { color: var(--brass-dark); }
.badge.milestone-10pct { color: var(--copper); border-color: var(--copper); }
.badge.milestone-saturation { background: var(--copper); color: var(--parchment); border-color: var(--copper); }

/* ---- Hero figure ---- */
.hero {
  margin: 1.5rem 0 2rem 0;
  padding: 0;
  text-align: center;
}
.hero img {
  max-width: 100%;
  max-height: 460px;
  border: 1px solid var(--rule);
  padding: 8px;
  background: var(--parchment-light);
  box-shadow: 0 2px 0 var(--shadow);
}
.hero figcaption {
  margin-top: 0.7rem;
  font-size: 0.86rem;
  color: var(--sepia-soft);
  font-style: italic;
}
.caption-title { display: block; font-style: normal; font-weight: 500; color: var(--sepia); margin-bottom: 0.25rem; }

/* Placeholder card when no CC image is available */
.hero.placeholder .placeholder-card {
  display: inline-block;
  width: min(100%, 520px);
  padding: 3rem 2rem;
  background: var(--parchment-dark);
  border: 1px solid var(--brass);
  box-shadow: 0 2px 0 var(--shadow);
  position: relative;
}
.placeholder-name {
  font-family: var(--serif-head);
  font-size: 1.4rem;
  color: var(--sepia);
  margin-bottom: 0.7rem;
}
.placeholder-mark {
  font-size: 1.6rem;
  color: var(--brass-dark);
  letter-spacing: 0.5em;
}

/* ---- Description / lead paragraph ---- */
.description p, .lead {
  font-size: 1.05rem;
  line-height: 1.7;
}
.lead {
  font-size: 1.12rem;
  line-height: 1.75;
  border-left: 3px solid var(--brass);
  padding-left: 1.2rem;
  color: var(--sepia);
}

/* ---- Innovator grid ---- */
.innovator-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
}
.innovator-card {
  background: var(--parchment-light);
  border: 1px solid var(--rule);
  border-left: 3px solid var(--copper);
  padding: 0.9rem 1rem;
}
.innovator-name {
  font-family: var(--serif-head);
  font-size: 1.1rem;
  margin: 0 0 0.3rem 0;
  color: var(--sepia);
}
.innovator-meta {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 0.5rem;
  font-size: 0.88rem;
  color: var(--sepia-soft);
  align-items: center;
}
.innovator-meta .country { font-style: italic; }
.innovator-role, .innovator-contribution {
  margin: 0.4rem 0;
  font-size: 0.95rem;
}

/* ---- Generic dimension list ---- */
.dim-list { list-style: none; padding: 0; margin: 0; }
.dim-list > li {
  border-top: 1px solid var(--rule);
  padding: 0.9rem 0;
}
.dim-list > li:first-child { border-top: none; }
.pred-head, .comp-head, .failed-head, .fund-head {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  flex-wrap: wrap;
  margin-bottom: 0.3rem;
}
.pred-name, .comp-name, .failed-name, .fund-name {
  font-family: var(--serif-head);
  font-size: 1.05rem;
  color: var(--sepia);
}
.brief, .role, .why-failed { margin: 0.3rem 0; font-size: 0.95rem; }

/* ---- Tables ---- */
.dim-table {
  width: 100%;
  border-collapse: collapse;
  margin: 0.6rem 0 0 0;
  font-size: 0.95rem;
}
.dim-table th, .dim-table td {
  padding: 0.55rem 0.7rem;
  border-bottom: 1px solid var(--rule);
  text-align: left;
  vertical-align: top;
}
.dim-table th {
  font-family: var(--serif-head);
  background: var(--parchment-dark);
  color: var(--sepia);
  font-weight: 700;
  border-bottom: 2px solid var(--brass);
  font-size: 0.9rem;
  letter-spacing: 0.02em;
}
.dim-table tr:nth-child(even) td { background: rgba(232, 219, 184, 0.35); }

/* ---- Citations ---- */
sup.cites {
  margin-left: 2px;
  font-size: 0.72em;
  vertical-align: super;
  line-height: 0;
  color: var(--copper);
}
sup.cites a.cite {
  color: var(--copper);
  text-decoration: none;
  padding: 0 1px;
  font-family: var(--mono);
}
sup.cites a.cite:hover {
  color: var(--crimson);
  text-decoration: underline;
}

/* ---- Sources section ---- */
.sources-note {
  font-style: italic;
  color: var(--sepia-soft);
  font-size: 0.95rem;
}
.source-list { list-style: none; padding: 0; margin: 1.2rem 0 0 0; }
.source-item {
  display: grid;
  grid-template-columns: 3rem 1fr;
  gap: 0.6rem;
  padding: 0.9rem 0;
  border-top: 1px solid var(--rule);
  scroll-margin-top: 1rem;
}
.source-item:first-child { border-top: none; }
.source-item:target {
  background: rgba(181, 137, 90, 0.15);
  outline: 2px solid var(--brass);
  outline-offset: 4px;
}
.src-num {
  font-size: 1rem;
  color: var(--brass-dark);
  text-align: right;
  padding-right: 0.4rem;
}
.src-meta {
  font-size: 0.84rem;
  color: var(--sepia-soft);
  margin-bottom: 0.3rem;
}
.src-host { color: var(--sepia); }
.src-url {
  display: inline-block;
  margin-bottom: 0.4rem;
  font-family: var(--mono);
  font-size: 0.85rem;
  word-break: break-all;
}
.src-quote {
  margin: 0.3rem 0 0 0;
  padding: 0.7rem 1rem;
  background: var(--parchment-light);
  border-left: 3px solid var(--brass);
  font-style: italic;
  font-size: 0.95rem;
  color: var(--sepia);
  quotes: "\\201C" "\\201D";
}

/* ---- Backlinks (Referenced by) ---- */
.backlinks {
  margin-top: 1.6rem;
}
.backlinks-note {
  font-style: italic;
  color: var(--sepia-soft);
  font-size: 0.92rem;
  margin: 0 0 0.9rem 0;
}
.backlink-group {
  margin-bottom: 1rem;
  padding: 0.7rem 1rem;
  background: var(--parchment-light);
  border-left: 3px solid var(--brass);
}
.backlink-group h3 {
  margin: 0 0 0.4rem 0;
  font-size: 0.98rem;
  color: var(--brass-dark);
  font-family: var(--serif-head);
}
.backlink-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem 1rem;
}
.backlink-list li { padding: 0; }
.backlink-list a { color: var(--copper); }
.backlink-list a:hover { color: var(--crimson); }
.backlink-id {
  font-size: 0.78rem;
  color: var(--sepia-soft);
}

/* ---- Variant link cards on category pages ---- */
.variant-list {
  list-style: none;
  padding: 0;
  margin: 1rem 0 0 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
}
.variant-link {
  display: block;
  padding: 1rem 1.1rem;
  background: var(--parchment-light);
  border: 1px solid var(--rule);
  border-left: 3px solid var(--copper);
  text-decoration: none;
  color: var(--sepia);
  transition: transform 0.12s ease;
}
.variant-link:hover { transform: translateY(-1px); }
.variant-name {
  font-family: var(--serif-head);
  font-size: 1.1rem;
  font-weight: 700;
  margin-bottom: 0.3rem;
  color: var(--sepia);
}
.variant-preview { font-size: 0.92rem; color: var(--sepia-soft); }

/* ---- Landing doors ---- */
.doors {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.6rem;
  margin: 2rem 0 3rem 0;
}
.door {
  background: var(--parchment-light);
  border: 1px solid var(--rule);
  padding: 1.6rem 1.8rem 1.4rem 1.8rem;
  box-shadow: 0 2px 8px var(--shadow);
}
.door h2 {
  margin-top: 0;
  border-bottom: none;
  padding-bottom: 0;
  color: var(--brass-dark);
  font-size: 1.35rem;
}
.door p { color: var(--sepia); }
.door-cta { margin-top: 1.2rem; margin-bottom: 0; }
.door-link {
  font-family: var(--serif-head);
  font-size: 1.2rem;
  font-weight: 700;
  text-decoration: none;
  border-bottom: 2px solid currentColor;
  padding-bottom: 2px;
}
.door-link:hover { border-bottom-color: var(--crimson); }

/* ---- Footer ---- */
.atlas-footer, .index-footer {
  margin-top: 4rem;
  padding-top: 1rem;
  border-top: 1px double var(--rule);
  text-align: center;
  color: var(--sepia-soft);
  font-size: 0.9rem;
}
.footer-meta { margin: 0.4rem 0; }
.footer-sep { margin: 0 0.5rem; color: var(--brass); }
.footer-nav { margin-top: 0.8rem; }
.footer-nav a { font-family: var(--mono); }

/* ---- Small-screen tweaks ---- */
@media (max-width: 640px) {
  main { padding: 1.5rem 1rem 4rem 1rem; }
  h1 { font-size: 2rem; }
  .atlas-header h1 { font-size: 2.4rem; }
  h2 { font-size: 1.3rem; }
  .source-item { grid-template-columns: 2.4rem 1fr; }
}
"""


# ---------------------------------------------------------------------------
# validation
# ---------------------------------------------------------------------------

class StrictHTMLChecker(HTMLParser):
    """Lightweight HTML wellformedness check."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.errors: list[str] = []

    def error(self, message: str) -> None:  # pragma: no cover - never raised by html.parser
        self.errors.append(message)


def validate_html(path: Path) -> list[str]:
    parser = StrictHTMLChecker()
    try:
        parser.feed(path.read_text(encoding="utf-8"))
        parser.close()
    except Exception as exc:
        return [f"parse error: {exc}"]
    return parser.errors


_HREF_RE = re.compile(r'href="([^"#]+)(#[^"]*)?"')


def collect_internal_links(path: Path) -> list[str]:
    """Return relative internal hrefs (skip http(s):// and pure-anchor links)."""
    text = path.read_text(encoding="utf-8")
    out: list[str] = []
    for m in _HREF_RE.finditer(text):
        href = m.group(1)
        if href.startswith("http://") or href.startswith("https://"):
            continue
        if href.startswith("mailto:"):
            continue
        if not href:
            continue
        out.append(href)
    return out


def validate_css(path: Path) -> list[str]:
    """Crude CSS check: balanced braces, no obvious syntax catastrophe."""
    text = path.read_text(encoding="utf-8")
    opens = text.count("{")
    closes = text.count("}")
    if opens != closes:
        return [f"unbalanced braces: {opens} '{{' vs {closes} '}}'"]
    return []


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    seeds = load_seeds()
    if not seeds:
        print(f"No seed JSON files found under {SEEDS_DIR}")
        return 1

    by_id: dict[str, dict] = {e["id"]: e for e in seeds}
    manifest = load_image_manifest()
    backlinks = compute_backlinks(by_id)

    # Ensure output directories exist.
    WEB_DIR.mkdir(parents=True, exist_ok=True)
    ENTRIES_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    # Write CSS.
    css_path = WEB_DIR / "styles.css"
    css_path.write_text(CSS, encoding="utf-8")
    print(f"  wrote {css_path.relative_to(REPO_ROOT)}")

    # Write each entry page.
    written: list[Path] = []
    for entry in seeds:
        if entry.get("entry_type") == "category":
            html_doc = build_category_page(entry, by_id, manifest, backlinks)
        else:
            html_doc = build_rich_page(entry, by_id, manifest, backlinks)
        out = ENTRIES_DIR / f"{slug(entry['id'])}.html"
        out.write_text(html_doc, encoding="utf-8")
        written.append(out)
        rel = out.relative_to(REPO_ROOT)
        print(f"  wrote {rel}")

    # Write the index.
    index_path = WEB_DIR / "index.html"
    index_html = build_index(seeds, by_id)
    index_path.write_text(index_html, encoding="utf-8")
    written.append(index_path)
    print(f"  wrote {index_path.relative_to(REPO_ROOT)}")

    # ---- Validation ----
    print("\nvalidating...")
    fail = 0

    # 1. Every seed -> one HTML file.
    for entry in seeds:
        target = ENTRIES_DIR / f"{slug(entry['id'])}.html"
        if not target.exists():
            print(f"  MISSING entry page for {entry['id']} -> {target}")
            fail += 1

    # 2. HTML well-formedness.
    for path in written:
        errs = validate_html(path)
        if errs:
            for e in errs:
                print(f"  HTML parse warn {path.relative_to(REPO_ROOT)}: {e}")
            fail += len(errs)

    # 3. CSS well-formedness.
    css_errs = validate_css(css_path)
    if css_errs:
        for e in css_errs:
            print(f"  CSS warn: {e}")
        fail += len(css_errs)

    # 4. Internal link resolution.
    bad_links = 0
    for path in written:
        for href in collect_internal_links(path):
            target = (path.parent / href).resolve()
            if not target.exists():
                print(f"  BROKEN LINK in {path.relative_to(REPO_ROOT)}: {href} -> {target}")
                bad_links += 1
    fail += bad_links

    # 5. Every entry page is reachable from the index by following internal links.
    visited: set[Path] = set()
    queue: list[Path] = [index_path.resolve()]
    while queue:
        path = queue.pop(0)
        if path in visited or not path.exists():
            continue
        visited.add(path)
        for href in collect_internal_links(path):
            target = (path.parent / href).resolve()
            if target.suffix == ".html" and target not in visited:
                queue.append(target)
    expected_pages = {(ENTRIES_DIR / f"{slug(e['id'])}.html").resolve() for e in seeds}
    unreachable = expected_pages - visited
    if unreachable:
        for p in sorted(unreachable):
            print(f"  UNREACHABLE from index: {p.relative_to(REPO_ROOT)}")
        fail += len(unreachable)

    if fail:
        print(f"\n{fail} validation issue(s) detected.")
        return 1

    print(f"\nbuild OK — {len(seeds)} entries, {len(written)} HTML files, CSS clean, links resolve.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
