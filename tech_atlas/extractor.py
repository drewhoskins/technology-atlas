"""High-level LLM operations for the ingestion pipeline.

Three operations:
  - discover_sources_for_component: given a component, propose Wikipedia URLs
  - reconcile_components:           given a parent entry + its raw text,
                                    propose missing enabling_components
  - extract_entry_fields:           given raw text, produce a populated Entry

Each LLM call goes through llm.LLMClient, which caches by content hash.
"""

from __future__ import annotations

from typing import Literal

from tech_atlas.fetcher import wikipedia_url_for_title
from tech_atlas.llm import LLMClient, extract_tool_use

_IMPORTANCE_DESC = (
    "How important this is to the parent technology's existence/function. "
    "'critical' = without it the parent wouldn't work or wouldn't have scaled "
    "(e.g., the internal combustion engine for a motorbus). 'important' = "
    "real contribution but the parent could exist with substitutes. "
    "'incidental' = present but not load-bearing."
)

# ---------------------------------------------------------------------------
# Source discovery
# ---------------------------------------------------------------------------

_DISCOVER_TOOL = {
    "name": "propose_sources",
    "description": (
        "Propose 1-3 ranked candidate English Wikipedia article titles that "
        "would serve as the primary source for this component's atlas entry. "
        "Prefer specific articles over umbrella ones."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "candidates": {
                "type": "array",
                "minItems": 0,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {
                        "wikipedia_title": {
                            "type": "string",
                            "description": "The article title as it appears in the URL (e.g. 'Macadam', 'Pneumatic_tire'). Underscores ok; will be URL-encoded.",
                        },
                        "justification": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    },
                    "required": ["wikipedia_title", "justification", "confidence"],
                },
            },
        },
        "required": ["candidates"],
    },
}


def discover_sources_for_component(
    *,
    client: LLMClient,
    name: str,
    component_type: str,
    role: str,
    parent_name: str,
    parent_description: str,
) -> list[dict]:
    """Returns list of {wikipedia_title, url, justification, confidence}, possibly empty."""
    system = (
        "You help curate an empirical atlas of how technologies came to be. "
        "Your job is to identify the best Wikipedia source for an 'enabling "
        "component' of a larger technology — a parallel infrastructure, "
        "practice, or sub-technology that the parent required to function or "
        "scale. Prefer specific articles (e.g. 'Macadam' over 'Road surface') "
        "but accept that some components don't have a dedicated article."
    )
    user = (
        f"Parent technology: {parent_name}\n"
        f"Parent description: {parent_description}\n\n"
        f"Component name: {name}\n"
        f"Component type: {component_type}\n"
        f"Component role: {role}\n\n"
        "Call propose_sources with 1-3 ranked candidates. Empty list is "
        "acceptable if no good Wikipedia article exists."
    )
    resp = client.call(
        system=system,
        messages=[{"role": "user", "content": user}],
        tools=[_DISCOVER_TOOL],
        tool_choice={"type": "tool", "name": "propose_sources"},
        purpose="discover",
    )
    payload = extract_tool_use(resp, "propose_sources")
    out = []
    for c in payload.get("candidates", []):
        title = c.get("wikipedia_title", "").strip()
        if not title:
            continue
        out.append(
            {
                "wikipedia_title": title,
                "url": wikipedia_url_for_title(title),
                "justification": c.get("justification", ""),
                "confidence": float(c.get("confidence", 0.0)),
            }
        )
    return out


# ---------------------------------------------------------------------------
# Component reconciliation
# ---------------------------------------------------------------------------

_RECONCILE_TOOL = {
    "name": "propose_components",
    "description": (
        "Given the parent technology's existing enabling_components and its "
        "raw source text, propose additional components that the existing "
        "list is missing. Do NOT propose anything already in the existing "
        "list (match by name, normalized)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "additions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "type": {
                            "type": "string",
                            "enum": [
                                "technology",
                                "infrastructure",
                                "practice",
                                "process",
                                "standard",
                            ],
                        },
                        "role": {
                            "type": "string",
                            "description": "One-paragraph explanation of why this component was necessary for the parent technology.",
                        },
                        "brief": {"type": "string"},
                        "importance": {
                            "type": "string",
                            "enum": ["critical", "important", "incidental"],
                            "description": _IMPORTANCE_DESC,
                        },
                        "justification_quote": {
                            "type": "string",
                            "description": "Verbatim excerpt from the source text supporting this addition.",
                        },
                    },
                    "required": [
                        "name",
                        "type",
                        "role",
                        "importance",
                        "justification_quote",
                    ],
                },
            }
        },
        "required": ["additions"],
    },
}


def reconcile_components(
    *,
    client: LLMClient,
    parent_name: str,
    parent_description: str,
    existing_components: list[dict],
    raw_text: str,
) -> list[dict]:
    """Returns list of proposed *additions* (not the full reconciled list)."""
    system = (
        "You help curate an empirical atlas of frontier technology. Your job "
        "is to spot enabling components a curator's existing list is missing. "
        "An 'enabling component' is a parallel infrastructure, sub-technology, "
        "practice, or standard that the parent technology required to function "
        "or scale — NOT a predecessor and NOT a vague societal precondition. "
        "Be conservative: only propose additions that the source text directly "
        "supports. Empty list is the right answer when nothing is clearly "
        "missing."
    )
    existing_summary = "\n".join(
        f"  - {c['name']} ({c.get('type', '?')}): {c.get('role', '')[:140]}"
        for c in existing_components
    ) or "  (none)"
    user = (
        f"Parent technology: {parent_name}\n"
        f"Parent description: {parent_description}\n\n"
        f"Existing enabling_components (do NOT re-propose these):\n"
        f"{existing_summary}\n\n"
        f"Raw source text (concatenated from the parent's primary sources):\n"
        f"-----\n{raw_text[:30000]}\n-----\n\n"
        "Call propose_components with any additions clearly supported by the text."
    )
    resp = client.call(
        system=system,
        messages=[{"role": "user", "content": user}],
        tools=[_RECONCILE_TOOL],
        tool_choice={"type": "tool", "name": "propose_components"},
        purpose="reconcile",
    )
    payload = extract_tool_use(resp, "propose_components")
    return list(payload.get("additions", []))


# ---------------------------------------------------------------------------
# Entry extraction
# ---------------------------------------------------------------------------

_SOURCE_OBJ_SCHEMA = {
    "type": "object",
    "properties": {
        "raw_id": {"type": "string"},
        "url": {"type": "string"},
        "quoted_text": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    },
    "required": ["raw_id", "url", "quoted_text", "confidence"],
}

_INNOVATOR_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "role": {"type": "string"},
        "country": {"type": "string"},
        "year": {"type": "integer"},
        "contribution": {"type": "string"},
        "importance": {
            "type": "string",
            "enum": ["critical", "important", "incidental"],
            "description": _IMPORTANCE_DESC,
        },
        "sources": {"type": "array", "items": _SOURCE_OBJ_SCHEMA},
    },
    "required": ["name", "role"],
}

_KEYDATE_SCHEMA = {
    "type": "object",
    "properties": {
        "year": {"type": "integer"},
        "event": {"type": "string"},
        "event_type": {
            "type": "string",
            "enum": ["invention", "patent", "scaling", "regulatory", "adoption"],
        },
        "significance": {"type": "string"},
        "sources": {"type": "array", "items": _SOURCE_OBJ_SCHEMA},
    },
    "required": ["year", "event", "event_type"],
}

_STUB_TOOL = {
    "name": "populate_stub_entry",
    "description": (
        "Populate a stub entry. Stubs are light: just description, 1-2 key "
        "innovators, and 1-3 key dates. Everything must trace to a "
        "quoted excerpt from the provided raw sources."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
                "description": "A dense, narrative description (2-4 paragraphs). Specific dates and names; no hedging.",
            },
            "description_sources": {"type": "array", "items": _SOURCE_OBJ_SCHEMA},
            "innovators": {
                "type": "array",
                "maxItems": 3,
                "items": _INNOVATOR_SCHEMA,
            },
            "key_dates": {
                "type": "array",
                "maxItems": 5,
                "items": _KEYDATE_SCHEMA,
            },
        },
        "required": ["description", "description_sources"],
    },
}

_PREDECESSOR_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "relationship": {
            "type": "string",
            "enum": ["evolved_from", "competing_predecessor", "inspiration"],
        },
        "year": {"type": "integer"},
        "brief": {"type": "string"},
        "linked_entry_id": {"type": "string"},
        "sources": {"type": "array", "items": _SOURCE_OBJ_SCHEMA},
    },
    "required": ["name", "relationship"],
}

_ENABLING_COMP_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "type": {
            "type": "string",
            "enum": ["technology", "infrastructure", "practice", "process", "standard"],
        },
        "role": {"type": "string"},
        "brief": {"type": "string"},
        "importance": {
            "type": "string",
            "enum": ["critical", "important", "incidental"],
            "description": _IMPORTANCE_DESC,
        },
        "linked_entry_id": {"type": "string"},
        "sources": {"type": "array", "items": _SOURCE_OBJ_SCHEMA},
    },
    "required": ["name", "type", "role", "importance"],
}

_FULL_TOOL = {
    "name": "populate_full_entry",
    "description": (
        "Populate a full entry with the complete set of structured fields. "
        "Every fact must trace to a quoted excerpt from the provided raw "
        "sources. Empty arrays are fine when a dimension isn't supported by "
        "the sources — don't fabricate."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "description": {"type": "string"},
            "description_sources": {"type": "array", "items": _SOURCE_OBJ_SCHEMA},
            "innovators": {"type": "array", "items": _INNOVATOR_SCHEMA},
            "predecessors": {"type": "array", "items": _PREDECESSOR_SCHEMA},
            "enabling_components": {"type": "array", "items": _ENABLING_COMP_SCHEMA},
            "key_dates": {"type": "array", "items": _KEYDATE_SCHEMA},
        },
        "required": ["description", "description_sources"],
    },
}


def extract_entry_fields(
    *,
    client: LLMClient,
    entry_name: str,
    entry_kind: Literal["stub", "full"],
    sources: list[dict],
) -> dict:
    """Run the extraction LLM call.

    `sources` is a list of {raw_id, url, text} dicts — the model will quote
    from these and tag claims with the matching raw_id.
    """
    system = (
        "You populate entries in an empirical atlas of technology history. "
        "Every fact you assert must trace to a verbatim quoted excerpt from "
        "the provided source text(s). Use the raw_id and url given for each "
        "source. Do not invent dates, people, or events. Prefer specific "
        "claims (with years and names) over generic ones. When a source "
        "doesn't support a claim, omit the claim."
    )
    source_blocks = []
    for s in sources:
        source_blocks.append(
            f"<source raw_id=\"{s['raw_id']}\" url=\"{s['url']}\">\n"
            f"{s['text']}\n"
            f"</source>"
        )
    user = (
        f"Target entry name: {entry_name}\n"
        f"Target kind: {entry_kind}\n\n"
        f"Sources:\n\n"
        f"{'\n\n'.join(source_blocks)}\n\n"
        f"Call {'populate_stub_entry' if entry_kind == 'stub' else 'populate_full_entry'} "
        "with fields populated from the sources."
    )
    tool = _STUB_TOOL if entry_kind == "stub" else _FULL_TOOL
    resp = client.call(
        system=system,
        messages=[{"role": "user", "content": user}],
        tools=[tool],
        tool_choice={"type": "tool", "name": tool["name"]},
        purpose=f"extract_{entry_kind}",
    )
    return extract_tool_use(resp, tool["name"])
