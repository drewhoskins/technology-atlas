# Atlas Schema

This document describes the atlas data model. The authoritative source is `tech_atlas/schema.py` (pydantic models); this doc tracks the same shape in human-readable form.

## Storage

* **SQLite** at `data/atlas.db`. Single table `entries`; the rich payload lives in a `data` JSON column.
* **Source-of-truth seeds** at `data/seeds/*.json` — one file per entry. The DB is rebuilt from seeds via `scripts/build_db.py`.
* **Raw source cache** at `data/raw/` (gitignored, dev-only) — preserves Layer 1 content so schema changes re-derive seeds without re-fetching the web.

## Tables

```sql
CREATE TABLE entries (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    domain      TEXT,
    entry_type  TEXT NOT NULL,    -- category | variant | standalone | stub
    parent_id   TEXT REFERENCES entries(id),
    data        TEXT NOT NULL     -- JSON; full Entry object
);
```

Indexes: `parent_id`, `domain`, `name`, `entry_type`.

## Entry types

| Type | Purpose | Population depth |
|---|---|---|
| `category` | Umbrella concept (e.g., "Bus") that groups variants | Light: description + child links via `parent_id` |
| `variant` | A specific kind within a category (e.g., "Trolleybus") | Full schema |
| `standalone` | An innovation that isn't part of a larger category | Full schema |
| `stub` | An enabling component referenced by other entries (e.g., "Pneumatic tire") | Light: name, description, key invention dates, 1-2 innovators |

## Tree relationships

* `parent_id` is **taxonomic** ("X is a kind of Y"). A trolleybus's `parent_id` is the `bus` category.
* `predecessors[]` is **temporal/evolutionary** ("X came before Y"). A motorized gasoline bus's predecessors include the horse-drawn omnibus. Usually within a category but allowed to cross.
* `enabling_components[]` is **value-chain** ("X needed Y to function"). Distinct from predecessors. The motorized bus needed the internal combustion engine.

Successors are **not stored** — they're derived: "successors of X" = "entries that list X in their predecessors."

## Entry fields

Every entry:
* `id`, `name`, `domain`, `description`, `entry_type`, `parent_id` (nullable)
* `description_sources[]` — sources for the entry's narrative description

Array dimensions (each element carries inline `sources[]` for provenance):

| Field | Element shape | Used for |
|---|---|---|
| `innovators[]` | `{name, role, country, year, contribution, importance, sources}` | People queries; weighting contributions by criticality |
| `predecessors[]` | `{name, relationship, year, brief, linked_entry_id, sources}` | Lineage; "what came before" |
| `enabling_components[]` | `{name, type, role, brief, importance, linked_entry_id, sources}` | Value-chain; "what made it work / scale" |
| `failed_alternatives[]` | `{name, why_failed, period, sources}` | Counterfactuals; "what almost won" |
| `funders[]` | `{entity, type, period, brief, sources}` | Money trail |
| `regulatory_moments[]` | `{year, jurisdiction, description, effect, sources}` | Policy and law shaping the trajectory |
| `geographic_diffusion[]` | `{place, year, milestone, brief, sources}` | Cross-country adoption timing |
| `key_dates[]` | `{year, event, event_type, significance, sources}` | Timeline events |

### Enums

* `entry_type`: `category | variant | standalone | stub`
* `Predecessor.relationship`: `evolved_from | competing_predecessor | inspiration`
* `EnablingComponent.type`: `technology | infrastructure | practice | process | standard`
* `Funder.type`: `private | government | philanthropic | venture | public_subscription | other`
* `RegulatoryMoment.effect`: `enabling | restricting | neutral | mixed`
* `GeographicDiffusion.milestone`: `first | 1pct | 10pct | saturation`
* `KeyDate.event_type`: `invention | patent | scaling | regulatory | adoption`
* `Importance` (used by `Innovator` and `EnablingComponent`): `critical | important | incidental` — how load-bearing this contribution/edge is to the parent's existence or scaling. Edge-level weight; the same component can be `critical` to one parent and `incidental` to another.

## Source object

```python
class Source:
    raw_id: str             # pointer into data/raw/manifest.json (dev-only)
    url: str                # original source URL (always preserved for citation)
    fetched_at: datetime    # when the raw artifact was captured
    quoted_text: str        # verbatim excerpt that supports the claim
    ai_or_human: "ai" | "human"
    confidence: float       # 0.0-1.0 alignment between quote and assertion
```

`quoted_text` is the audit trail. Anyone can verify a fact by checking the quote against its `url`. The `raw_id` enables re-derivation against cached sources when the schema evolves.

## Schema-change workflow

1. Update `tech_atlas/schema.py` (add/change fields).
2. Re-run `scripts/extract.py` against `data/raw/` (cached locally) to regenerate `data/seeds/*`.
3. Re-run `scripts/build_db.py` to rebuild `data/atlas.db`.
4. No web re-fetch required.
