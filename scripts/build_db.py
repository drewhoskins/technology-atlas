#!/usr/bin/env python3
"""Build atlas.db from data/seeds/*.json (recursively).

Validates each seed against the pydantic schema, then inserts. Rebuilds the
table from scratch each run — seeds are the source of truth, the DB is derived.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tech_atlas.db import DB_PATH, get_connection, init_db  # noqa: E402
from tech_atlas.schema import Entry  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
SEEDS_DIR = REPO_ROOT / "data" / "seeds"


def find_seed_files(seeds_dir: Path) -> list[Path]:
    return sorted(seeds_dir.rglob("*.json"))


def main() -> int:
    init_db()
    seed_files = find_seed_files(SEEDS_DIR)

    if not seed_files:
        print(f"No seed JSON files found in {SEEDS_DIR}")
        print("Add entries to data/seeds/ and re-run.")
        return 0

    failures: list[tuple[Path, str]] = []
    loaded = 0

    # Disable FK enforcement during the load so insertion order doesn't matter,
    # then explicitly validate referential integrity after — gives clearer errors
    # than "FOREIGN KEY constraint failed".
    with get_connection() as conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("DELETE FROM entries")
        for seed_file in seed_files:
            try:
                with open(seed_file) as f:
                    raw = json.load(f)
                entry = Entry.model_validate(raw)
                conn.execute(
                    "INSERT INTO entries (id, name, domain, entry_type, parent_id, data) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        entry.id,
                        entry.name,
                        entry.domain,
                        entry.entry_type,
                        entry.parent_id,
                        entry.model_dump_json(),
                    ),
                )
                rel = seed_file.relative_to(REPO_ROOT)
                print(f"  loaded {entry.id:<40} ({entry.entry_type:<10}) <- {rel}")
                loaded += 1
            except Exception as e:
                failures.append((seed_file, str(e)))

        # Referential integrity check: every parent_id must resolve.
        orphans = conn.execute(
            "SELECT id, parent_id FROM entries "
            "WHERE parent_id IS NOT NULL "
            "  AND parent_id NOT IN (SELECT id FROM entries)"
        ).fetchall()
        for orphan in orphans:
            failures.append(
                (Path(orphan["id"]), f"parent_id '{orphan['parent_id']}' not found in atlas")
            )

        if failures:
            conn.rollback()
            print("\nFAILURES:")
            for path, err in failures:
                print(f"  {path}: {err}")
            return 1

        conn.commit()

    print(f"\nBuilt {DB_PATH} with {loaded} entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
