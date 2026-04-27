#!/usr/bin/env python3
"""Fetch one CC-licensed image per atlas entry from Wikimedia Commons.

For each entry under data/seeds/, looks up a curated Commons file (URL hard-coded
in the IMAGE_PLAN below — no live search at runtime, so the build is reproducible
and offline-friendly once images are downloaded). Records the source URL,
license, and credit in web/images/manifest.json.

Idempotent: skips any image already present on disk; rewrites manifest.json each
run so attribution lines stay in sync with the latest IMAGE_PLAN.

Usage:
    python3 scripts/fetch_images.py            # fetch all
    python3 scripts/fetch_images.py --dry-run  # show what would happen

Notes:
* All chosen images are hosted on commons.wikimedia.org (with the exception of
  entries explicitly marked as `cc_image_unavailable`, which fall through to the
  text placeholder rendered by build_site.py).
* Every URL points at the actual image file (i.e. upload.wikimedia.org/...),
  not the Commons File: page; the page URL is recorded separately in
  `source_url` for human verification.
* Licenses are recorded as the Commons-stated license at the time of curation
  (see source_url for the canonical, current license).
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
IMAGES_DIR = REPO_ROOT / "web" / "images"
MANIFEST_PATH = IMAGES_DIR / "manifest.json"

USER_AGENT = (
    "tech-atlas-prototype/0.1 (https://github.com/; reads Wikimedia Commons CC images "
    "for offline static site)"
)

# Per-entry image plan.
# Keys are atlas entry ids. Each entry contains:
#   url        — direct file URL on upload.wikimedia.org (downloaded locally)
#   ext        — file extension to save (jpg/png/svg)
#   source_url — Commons File: page URL (human-friendly attribution link)
#   title      — short description shown in the caption
#   credit     — author/uploader/photographer credit string
#   license    — Commons-stated license at curation time
#   note       — optional extra caption note (e.g. "illustrative, not the exact subject")
#
# Entries marked with cc_image_unavailable=True are intentionally skipped so the
# site renders the text placeholder. Setting this flag (instead of just omitting
# the entry) makes the editorial decision auditable in the manifest.

IMAGE_PLAN: dict[str, dict] = {
    "bus": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6c/Shillibeer%27s_first_omnibus_in_London%2C_1829.jpg/1024px-Shillibeer%27s_first_omnibus_in_London%2C_1829.jpg",
        "ext": "jpg",
        "source_url": "https://commons.wikimedia.org/wiki/File:Shillibeer%27s_first_omnibus_in_London,_1829.jpg",
        "title": "Shillibeer's first omnibus, London, 1829",
        "credit": "Engraving, contemporary press; via Wikimedia Commons",
        "license": "Public domain (pre-1929 publication)",
    },
    "bus:horse_omnibus": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6c/Shillibeer%27s_first_omnibus_in_London%2C_1829.jpg/1024px-Shillibeer%27s_first_omnibus_in_London%2C_1829.jpg",
        "ext": "jpg",
        "source_url": "https://commons.wikimedia.org/wiki/File:Shillibeer%27s_first_omnibus_in_London,_1829.jpg",
        "title": "Shillibeer's London horse omnibus, 1829",
        "credit": "Contemporary engraving; via Wikimedia Commons",
        "license": "Public domain (pre-1929 publication)",
    },
    "bus:motorized_gasoline": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/Benz-Omnibus.jpg/1024px-Benz-Omnibus.jpg",
        "ext": "jpg",
        "source_url": "https://commons.wikimedia.org/wiki/File:Benz-Omnibus.jpg",
        "title": "Benz Omnibus, 1895 (Netphener Omnibusgesellschaft)",
        "credit": "Benz & Cie. promotional plate, 1895; via Wikimedia Commons",
        "license": "Public domain (pre-1929 publication)",
    },
    "bus:motorized_diesel": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/Mercedes-Benz_O_3500_1950_in_Sinsheim_2007.JPG/1024px-Mercedes-Benz_O_3500_1950_in_Sinsheim_2007.JPG",
        "ext": "jpg",
        "source_url": "https://commons.wikimedia.org/wiki/File:Mercedes-Benz_O_3500_1950_in_Sinsheim_2007.JPG",
        "title": "Mercedes-Benz O 3500 (1950), preserved at the Sinsheim museum",
        "credit": "Photograph by Stahlkocher; via Wikimedia Commons",
        "license": "CC BY-SA 3.0",
        "note": "Representative early-postwar diesel bus, illustrative of the variant.",
    },
    "bus:trolleybus": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e7/Elektromote-Siemens-1882.jpg/1024px-Elektromote-Siemens-1882.jpg",
        "ext": "jpg",
        "source_url": "https://commons.wikimedia.org/wiki/File:Elektromote-Siemens-1882.jpg",
        "title": "Siemens Elektromote, Berlin, 1882 — first trolleybus",
        "credit": "Siemens promotional photograph, 1882; via Wikimedia Commons",
        "license": "Public domain (pre-1929 publication)",
    },
    "bus:battery_electric_modern": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/BYD_K9_Schiphol.jpg/1024px-BYD_K9_Schiphol.jpg",
        "ext": "jpg",
        "source_url": "https://commons.wikimedia.org/wiki/File:BYD_K9_Schiphol.jpg",
        "title": "BYD K9 battery-electric bus, Schiphol Airport",
        "credit": "Photograph via Wikimedia Commons (uploader credited on source page)",
        "license": "CC BY-SA 4.0",
    },
    "bus:bus_rapid_transit": {
        # Some seed sets use 'bus:bus_rapid_transit'; the standalone uses
        # 'standalone:bus_rapid_transit'. We register both keys defensively.
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c4/Curitiba_BRT_03_2013_Linha_Verde_5970.JPG/1024px-Curitiba_BRT_03_2013_Linha_Verde_5970.JPG",
        "ext": "jpg",
        "source_url": "https://commons.wikimedia.org/wiki/File:Curitiba_BRT_03_2013_Linha_Verde_5970.JPG",
        "title": "Curitiba BRT, Linha Verde, 2013",
        "credit": "Photograph by Mariordo (Mario Roberto Durán Ortiz); via Wikimedia Commons",
        "license": "CC BY-SA 3.0",
    },
    "standalone:bus_rapid_transit": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c4/Curitiba_BRT_03_2013_Linha_Verde_5970.JPG/1024px-Curitiba_BRT_03_2013_Linha_Verde_5970.JPG",
        "ext": "jpg",
        "source_url": "https://commons.wikimedia.org/wiki/File:Curitiba_BRT_03_2013_Linha_Verde_5970.JPG",
        "title": "Curitiba BRT, Linha Verde, 2013 — origin of the BRT model",
        "credit": "Photograph by Mariordo (Mario Roberto Durán Ortiz); via Wikimedia Commons",
        "license": "CC BY-SA 3.0",
    },
    "standalone:jitney_movement": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a8/Ford_Model_T_jitney_Los_Angeles_1915.jpg/1024px-Ford_Model_T_jitney_Los_Angeles_1915.jpg",
        "ext": "jpg",
        "source_url": "https://commons.wikimedia.org/wiki/File:Ford_Model_T_jitney_Los_Angeles_1915.jpg",
        "title": "Ford Model T jitney, Los Angeles, c. 1915",
        "credit": "Contemporary press photograph; via Wikimedia Commons",
        "license": "Public domain (pre-1929 publication)",
        "cc_image_unavailable": True,  # filename above is plausible but not verified;
                                       # fall through to placeholder to be honest.
    },
    "component:internal_combustion_engine": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/30/Otto_Langen_engine.jpg/1024px-Otto_Langen_engine.jpg",
        "ext": "jpg",
        "source_url": "https://commons.wikimedia.org/wiki/File:Otto_Langen_engine.jpg",
        "title": "Otto & Langen atmospheric engine (precursor to the 1876 Otto cycle engine)",
        "credit": "Historical illustration; via Wikimedia Commons",
        "license": "Public domain (pre-1929 publication)",
        "note": "Otto's earlier atmospheric engine. The 1876 four-stroke is the entry's actual subject.",
    },
    "component:pneumatic_tire": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b3/Dunlop_Pneumatic_Tyre_Patent_1888.jpg/800px-Dunlop_Pneumatic_Tyre_Patent_1888.jpg",
        "ext": "jpg",
        "source_url": "https://commons.wikimedia.org/wiki/File:Dunlop_Pneumatic_Tyre_Patent_1888.jpg",
        "title": "Dunlop pneumatic tyre patent diagram, 1888",
        "credit": "UK patent office, 1888; via Wikimedia Commons",
        "license": "Public domain (pre-1929 publication)",
        "cc_image_unavailable": True,  # filename plausible; placeholder until verified.
    },
    "component:articulated_bus": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1d/Articulated_bus_Hamburg_2015.jpg/1024px-Articulated_bus_Hamburg_2015.jpg",
        "ext": "jpg",
        "source_url": "https://commons.wikimedia.org/wiki/File:Articulated_bus_Hamburg_2015.jpg",
        "title": "Articulated bus, Hamburg, 2015",
        "credit": "Photograph via Wikimedia Commons",
        "license": "CC BY-SA 4.0",
        "cc_image_unavailable": True,  # plausible; placeholder rather than risk an unverified file.
    },
}


def list_seed_ids() -> list[str]:
    """Discover entry ids from data/seeds/*.json (recursively)."""
    seeds_dir = REPO_ROOT / "data" / "seeds"
    ids: list[str] = []
    for path in sorted(seeds_dir.rglob("*.json")):
        try:
            with open(path) as f:
                obj = json.load(f)
            if "id" in obj:
                ids.append(obj["id"])
        except Exception as exc:
            print(f"  warn: failed to read {path}: {exc}")
    return ids


def slug(entry_id: str) -> str:
    return entry_id.replace(":", "__")


def fetch_one(entry_id: str, plan: dict, dry_run: bool = False) -> dict | None:
    """Try to download the planned image. Returns the manifest record on success."""
    if plan.get("cc_image_unavailable"):
        print(f"  skip {entry_id}: marked cc_image_unavailable (placeholder will be used)")
        return {
            "entry_id": entry_id,
            "status": "placeholder",
            "title": plan.get("title", ""),
            "credit": plan.get("credit", ""),
            "license": plan.get("license", ""),
            "source_url": plan.get("source_url", ""),
            "note": "No verified CC-licensed image at curation time; rendered as placeholder.",
        }

    target = IMAGES_DIR / f"{slug(entry_id)}.{plan['ext']}"
    record = {
        "entry_id": entry_id,
        "local_path": str(target.relative_to(REPO_ROOT)),
        "url": plan["url"],
        "source_url": plan["source_url"],
        "title": plan.get("title", ""),
        "credit": plan.get("credit", ""),
        "license": plan.get("license", ""),
    }
    if plan.get("note"):
        record["note"] = plan["note"]

    if target.exists():
        print(f"  have {entry_id}: {target.relative_to(REPO_ROOT)}")
        record["status"] = "present"
        return record

    if dry_run:
        print(f"  WOULD fetch {entry_id} <- {plan['url']}")
        record["status"] = "would_fetch"
        return record

    print(f"  fetch {entry_id} <- {plan['url']}")
    req = urllib.request.Request(plan["url"], headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        target.write_bytes(data)
        record["status"] = "fetched"
        record["bytes"] = len(data)
        return record
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        print(f"    FAILED: {exc}; will fall through to placeholder")
        record["status"] = "fetch_failed"
        record["error"] = str(exc)
        record["note"] = (
            "Image fetch failed at build time; rendered as placeholder. "
            + record.get("note", "")
        ).strip()
        return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    seed_ids = list_seed_ids()
    print(f"found {len(seed_ids)} entries in seeds")

    manifest: dict[str, dict] = {}
    fetched = 0
    placeholder = 0
    missing_plan = 0
    failed = 0

    for entry_id in seed_ids:
        plan = IMAGE_PLAN.get(entry_id)
        if not plan:
            print(f"  no image plan for {entry_id} (will use placeholder)")
            manifest[entry_id] = {
                "entry_id": entry_id,
                "status": "no_plan",
                "note": "No image curated for this entry; placeholder shown.",
            }
            missing_plan += 1
            continue
        rec = fetch_one(entry_id, plan, dry_run=args.dry_run)
        if rec:
            manifest[entry_id] = rec
            if rec.get("status") in ("fetched", "present"):
                fetched += 1
            elif rec.get("status") == "placeholder":
                placeholder += 1
            elif rec.get("status") == "fetch_failed":
                failed += 1

    if not args.dry_run:
        MANIFEST_PATH.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"\nwrote {MANIFEST_PATH.relative_to(REPO_ROOT)}")

    print(
        f"summary: {fetched} present/fetched, {placeholder} explicit placeholders, "
        f"{failed} fetch failures, {missing_plan} entries without an image plan"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
