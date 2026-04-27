# tech-atlas (prototype)

An empirical atlas of frontier technology and its innovators.

This prototype packs a small slice of bus history and exposes it to Claude Code via a project-scoped skill that teaches direct SQL access to the underlying SQLite database.

## What's here

```
technology-atlas/
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

Pre-requisites: macOS or Linux with `sqlite3` installed (preinstalled on both).

```bash
git clone <repo-url>
cd technology-atlas
```

Open Claude Code in the directory. The project-scoped skill `tech-atlas` auto-loads and teaches Claude how to query `data/atlas.db`. 

Try a query:

> *"What's in the atlas? Run a search for buses and walk me through what you find."*

## License & redistribution

The schema, code, and atlas data (`data/seeds/`, `data/atlas.db`) are provided under the project license. Source materials cited in entries remain under their original licenses; attribution is preserved per-element via inline `sources` with `quoted_text` and source URLs.
