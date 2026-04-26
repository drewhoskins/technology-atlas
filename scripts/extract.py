#!/usr/bin/env python3
"""Extract structured atlas entries from cached raw artifacts.

Phase 1 stub. Real implementation lands in Phase 4.

Why this is a separate step from fetch.py: schema changes can re-run extraction
against the existing data/raw/ cache without re-fetching from the live web.
This is the whole point of the two-layer model.

Inputs:  data/raw/* (cached source content) + data/raw/manifest.json
Outputs: data/seeds/*.json (one per atlas entry, schema-conforming)
"""

from __future__ import annotations

import sys


def main() -> int:
    print("scripts/extract.py is a Phase 1 stub. Real implementation in Phase 4.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
