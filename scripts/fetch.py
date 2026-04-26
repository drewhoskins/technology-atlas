#!/usr/bin/env python3
"""Fetch a source URL into data/raw/ and update the manifest.

Phase 1 stub. Real implementation lands in Phase 4 (population pipeline).

Two-layer model: this script writes Layer 1 (raw cached artifacts).
Layer 2 (derived seeds) is produced by extract.py from cached artifacts.

Manifest schema (data/raw/manifest.json):
    {
      "version": 1,
      "artifacts": [
        {
          "id":              "wikipedia:Bus@2026-04-25T22:15:00Z",
          "url":             "https://en.wikipedia.org/wiki/Bus",
          "type":            "wikipedia",      # wikipedia | owid | paper | gov | other
          "fetched_at":      "2026-04-25T22:15:00Z",
          "artifact_path":   "data/raw/wikipedia/Bus.txt",
          "hash":            "sha256:abc...",
          "license":         "CC-BY-SA",       # source license tag
          "redistributable": true,             # whether full text can be shipped
          "revision_id":     "12345"           # Wikipedia revision id where applicable
        }
      ]
    }

Note: data/raw/ is gitignored. Cache lives only on the dev machine.
"""

from __future__ import annotations

import sys


def main() -> int:
    print("scripts/fetch.py is a Phase 1 stub. Real implementation in Phase 4.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
