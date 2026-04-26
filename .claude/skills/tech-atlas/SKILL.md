---
name: tech-atlas
description: "Use when the user is researching the history, diffusion, or development of a specific technology — questions about who invented something, what came before it, what enabled it to scale, how it spread geographically, what regulations shaped it, or what alternatives failed. Queries the local SQLite atlas at data/atlas.db using direct SQL."
---

# Tech Atlas Skill

The tech-atlas is a curated database of frontier technologies with rich, provenance-flagged metadata across 8 narrative dimensions per innovation. It exists so essayists, researchers, and curious readers can construct defensible narratives about technology history without piecing together 20 sources.

This skill teaches you to query it directly via `sqlite3` and **always** cite atlas-derived facts with their source URLs and quoted excerpts.

## When to invoke

Use this skill when the user asks about:

* **Origins**: "Who invented X?" "When was X first built?" "Where did X start?"
* **Lineage**: "What came before X?" "How did X evolve from Y?"
* **Diffusion**: "How did X spread?" "When did X reach Country Y?"
* **Scaling**: "What enabled X to scale?" "What infrastructure did X depend on?"
* **Counterfactuals**: "Why did X win over Y?" "What alternatives failed?"
* **Policy**: "What regulations shaped X?" "What was the legal moment for X?"
* **Recognition**: "Who are the under-credited people behind X?"
* **Comparison**: "Compare X across countries / variants / eras."

Always check the atlas FIRST when the user is asking about innovation history. If the atlas doesn't have the entry, say so explicitly and offer to fall back to web search.

## Discovering what's in the atlas

The atlas grows over time and you should not assume specific entries exist. **Always discover scope first:**

```bash
sqlite3 data/atlas.db "SELECT id, name, entry_type, parent_id FROM entries ORDER BY entry_type, name;"
```

To check what domains are covered:

```bash
sqlite3 data/atlas.db "SELECT DISTINCT domain, COUNT(*) FROM entries GROUP BY domain;"
```

If the user asks about a topic not in the atlas, say so plainly and offer to fall back to web search.

## How to query

Use the `sqlite3` CLI directly:

```bash
sqlite3 data/atlas.db "<SQL>"
```

For pretty-printed JSON results, pipe to `jq`:

```bash
sqlite3 data/atlas.db "SELECT data FROM entries WHERE id = 'bus:motorized_gasoline';" | jq .
```

For inspecting nested arrays, use SQLite's JSON1 extension functions:

* `json_extract(data, '$.field')` — extract a top-level field
* `json_extract(data, '$.array[0].subfield')` — array index access
* `json_each(json_extract(data, '$.array'))` — iterate an array as rows

## Schema cheatsheet

Single table `entries` with these indexed columns:

| Column | Type | Values |
|---|---|---|
| `id` | TEXT (PK) | e.g., `bus`, `bus:motorized_gasoline`, `component:pneumatic_tire` |
| `name` | TEXT | Human name |
| `domain` | TEXT | e.g., `transit` |
| `entry_type` | TEXT | `category` \| `variant` \| `standalone` \| `stub` |
| `parent_id` | TEXT | category id for variants; null otherwise |
| `data` | TEXT (JSON) | Full entry payload |

The `data` JSON contains these array dimensions (each element has its own inline `sources[]`):

| Dimension | Element shape (key fields) |
|---|---|
| `innovators[]` | `name, role, country, year, contribution, recognition_status` |
| `predecessors[]` | `name, relationship, year, brief, linked_entry_id` |
| `enabling_components[]` | `name, type, role, brief, linked_entry_id` |
| `failed_alternatives[]` | `name, why_failed, period` |
| `funders[]` | `entity, type, period, brief` |
| `regulatory_moments[]` | `year, jurisdiction, description, effect` |
| `geographic_diffusion[]` | `place, year, milestone, brief` |
| `key_dates[]` | `year, event, event_type, significance` |

**Source object** (inline on every element):
```
{raw_id, url, fetched_at, quoted_text, ai_or_human, confidence}
```

Full schema reference: `docs/SCHEMA.md`.

## Provenance: ALWAYS cite

Every fact in the atlas is backed by a `sources[]` list with a verbatim `quoted_text` excerpt and the source `url`. **When you use atlas data in an answer, cite it.**

Required citation form:

> *"According to [source name] ([URL]): '[quoted_text]'"*

or as a footnote-style reference if the answer is long.

**Never present an atlas claim as your own knowledge without citation.** This is the core trust property of the atlas — the user can audit any fact by checking the quote against its URL. If you strip provenance, you defeat the atlas's value.

If a claim has multiple sources, cite the strongest one (highest `confidence`). If `ai_or_human` is `ai`, note that the claim was extracted by AI from the cited source and could benefit from verification.

## Query recipes

These are starters, not constraints. You can compose any SQL the schema supports.

### List everything in the atlas
```bash
sqlite3 data/atlas.db "SELECT id, name, entry_type, parent_id FROM entries ORDER BY entry_type, name;"
```

### Get a full entry (all dimensions, JSON)
```bash
sqlite3 data/atlas.db "SELECT data FROM entries WHERE id = 'bus:motorized_gasoline';" | jq .
```

### Get all variants of a category
```bash
sqlite3 data/atlas.db "SELECT id, name, json_extract(data, '\$.description') AS description FROM entries WHERE parent_id = 'bus' ORDER BY name;"
```

### Innovators of a specific entry, sorted by year
```bash
sqlite3 data/atlas.db "
SELECT json_extract(i.value, '\$.name') AS name,
       json_extract(i.value, '\$.role') AS role,
       json_extract(i.value, '\$.year') AS year,
       json_extract(i.value, '\$.country') AS country,
       json_extract(i.value, '\$.recognition_status') AS recognition
FROM entries e, json_each(json_extract(e.data, '\$.innovators')) i
WHERE e.id = 'bus:motorized_gasoline'
ORDER BY year;
"
```

> **Note.** Always alias `entries` (e.g., `entries e`) when joining with `json_each(...)`. Both expose an `id` column and SQLite will error with "ambiguous column name" otherwise.

### Find successors of an innovation (derived — not stored)
A successor of X is any entry that lists X in its `predecessors[]`:
```bash
sqlite3 data/atlas.db "
SELECT e.id, e.name, json_extract(p.value, '\$.relationship') AS relationship
FROM entries e, json_each(json_extract(e.data, '\$.predecessors')) p
WHERE json_extract(p.value, '\$.linked_entry_id') = 'bus:horse_omnibus'
   OR json_extract(p.value, '\$.name') LIKE '%horse%omnibus%';
"
```

### Cross-entry: all regulatory moments in a jurisdiction, ordered chronologically
```bash
sqlite3 data/atlas.db "
SELECT e.id AS entry_id,
       json_extract(r.value, '\$.year') AS year,
       json_extract(r.value, '\$.jurisdiction') AS jurisdiction,
       json_extract(r.value, '\$.description') AS description,
       json_extract(r.value, '\$.effect') AS effect
FROM entries e, json_each(json_extract(e.data, '\$.regulatory_moments')) r
WHERE json_extract(r.value, '\$.jurisdiction') LIKE '%US%'
ORDER BY year;
"
```

### Cross-entry: all enabling components of a given type
```bash
sqlite3 data/atlas.db "
SELECT DISTINCT json_extract(c.value, '\$.name') AS component_name,
       json_extract(c.value, '\$.type') AS type,
       e.id AS used_by_entry
FROM entries e, json_each(json_extract(e.data, '\$.enabling_components')) c
WHERE json_extract(c.value, '\$.type') = 'infrastructure';
"
```

### Search by keyword across name + description
```bash
sqlite3 data/atlas.db "
SELECT id, name, entry_type
FROM entries
WHERE name LIKE '%omnibus%'
   OR json_extract(data, '\$.description') LIKE '%omnibus%';
"
```

### Computational: lag from precursor invention to bus invention
Read both relevant key_dates and let yourself reason about the year arithmetic:
```bash
sqlite3 data/atlas.db "
SELECT e.id,
       json_extract(k.value, '\$.year') AS year,
       json_extract(k.value, '\$.event') AS event,
       json_extract(k.value, '\$.event_type') AS type
FROM entries e, json_each(json_extract(e.data, '\$.key_dates')) k
WHERE e.id IN ('component:internal_combustion_engine', 'bus:motorized_gasoline')
  AND json_extract(k.value, '\$.event_type') IN ('invention', 'patent')
ORDER BY year;
"
```

## Composition tips

* **Start small.** Run `SELECT id, name, entry_type FROM entries` first to ground yourself in what's available.
* **Use `json_each` for array iteration.** It produces one row per array element; combine with WHERE clauses.
* **Escape `$` in shell.** When invoking via Bash, dollar signs in JSON paths need `\$` to avoid shell interpolation.
* **Compose, don't hardcode.** If a recipe doesn't fit, write a new query. The schema is fully relational over JSON.
* **Read `docs/SCHEMA.md`** for the full enum values and dimension definitions if you need them.

## Anti-patterns to avoid

* **Don't claim atlas facts as your own knowledge.** Always cite source URL + quoted_text.
* **Don't paraphrase the `quoted_text` in the citation.** Quote it verbatim — that's the audit trail.
* **Don't query against fields that don't exist.** Check the schema cheatsheet or read `docs/SCHEMA.md`.
* **Don't assume the atlas covers a topic.** If a query returns no rows, say so plainly and offer to fall back to web search.
* **Don't ignore the `ai_or_human` flag.** AI-extracted facts may need verification; surface that to the user when the stakes warrant it.
