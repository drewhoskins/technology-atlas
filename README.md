# tech-atlas (prototype)

An empirical atlas of frontier technology and its innovators.

This prototype packs a small slice of bus history (4 variants + ~12 enabling components) and exposes it to Claude Code via a project-scoped skill that teaches direct SQL access to the underlying SQLite database.

## What's here

```
tech-atlas-prototype/
├── tech_atlas/           # pydantic schema + DB helpers (Python)
├── scripts/              # build_db.py, fetch.py, extract.py
├── data/
│   ├── seeds/            # one JSON file per atlas entry — the source of truth
│   └── atlas.db          # SQLite, derived from seeds/
├── .claude/skills/tech-atlas/
│   └── SKILL.md          # how Claude Code queries the atlas
└── docs/
    ├── SCHEMA.md         # human-readable schema doc
    └── DEMO.md           # 5-min demo script + Pepsi-challenge prompts
```

`data/raw/` (cached source artifacts) is **gitignored** — it lives only on the developer's machine. Schema changes can re-derive `data/seeds/*` from the local cache without re-fetching the web.

## Setup (interviewer)

Pre-requisites: macOS or Linux with `sqlite3` installed (preinstalled on both). No Python required to use the atlas.

```bash
git clone <repo-url>
cd tech-atlas-prototype
```

Open Claude Code in the directory. The project-scoped skill `tech-atlas` auto-loads and teaches Claude how to query `data/atlas.db`.

Try a query:

> *"What's in the atlas? Run a search for buses and walk me through what you find."*

## Setup (developer)

Add Python tooling for rebuilding the DB from seeds, populating new entries, and validating schemas.

```bash
uv sync
uv run python scripts/build_db.py     # rebuild atlas.db from data/seeds/*.json
```

## The Pepsi challenge

The demo compares two Claude Code sessions on the same research task:
* **Atlas-armed**: Claude Code in this directory, with the skill + DB
* **No-atlas**: Claude Code in an empty directory, with WebSearch + WebFetch only

This isolates the atlas as the differentiator against the realistic baseline (web-armed Claude Code, which is how serious researchers work today). See `docs/DEMO.md` for the prompts and recording protocol.

## License & redistribution

The schema, code, and atlas data (`data/seeds/`, `data/atlas.db`) are provided under the project license. Source materials cited in entries remain under their original licenses; attribution is preserved per-element via inline `sources` with `quoted_text` and source URLs.

Raw cached source content (`data/raw/`) is **not** redistributed.
