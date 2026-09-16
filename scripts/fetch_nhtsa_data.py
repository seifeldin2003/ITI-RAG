# -*- coding: utf-8 -*-
"""
Phase 1 data collection -- pulls NHTSA Recalls + Complaints for a fixed scope
of (make, model, year) triples and saves the RAW responses to local JSON
files under data/raw/nhtsa/.

Why this is a separate one-time script, not notebook code: the notebook
(Phase 2) must run top-to-bottom deterministically (Kernel > Restart & Run
All) without depending on a live network call succeeding 300+ times in a
row. Run this script ONCE now; the notebook only ever reads the saved
files it produces.

Source: api.nhtsa.gov -- public, no API key, U.S. federal government data
(public domain, per usa.gov/publicdomain/label/1.0).
"""
import json
import time
from pathlib import Path

import requests

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "nhtsa"
OUT_DIR.mkdir(parents=True, exist_ok=True)

RECALLS_URL = "https://api.nhtsa.gov/recalls/recallsByVehicle"
COMPLAINTS_URL = "https://api.nhtsa.gov/complaints/complaintsByVehicle"

# A fixed, defensible scope: popular makes/models (+ the BMW X6 from the
# original example) across 8 recent model years. 20 make/model pairs x 8
# years x 2 endpoints = 320 calls -- large enough to be a real reference
# corpus, small enough to fetch in a few minutes being polite to the API.
MAKE_MODELS = [
    ("TOYOTA", "CAMRY"), ("TOYOTA", "COROLLA"), ("TOYOTA", "RAV4"),
    ("HONDA", "CIVIC"), ("HONDA", "ACCORD"), ("HONDA", "CR-V"),
    ("FORD", "F-150"), ("FORD", "EXPLORER"), ("FORD", "ESCAPE"),
    ("CHEVROLET", "SILVERADO"), ("CHEVROLET", "MALIBU"), ("CHEVROLET", "EQUINOX"),
    ("BMW", "X5"), ("BMW", "X6"), ("BMW", "3 SERIES"),
    ("NISSAN", "ALTIMA"), ("NISSAN", "ROGUE"),
    ("HYUNDAI", "ELANTRA"), ("HYUNDAI", "TUCSON"),
    ("JEEP", "GRAND CHEROKEE"),
]
YEARS = list(range(2016, 2024))  # 2016-2023 inclusive

REQUEST_DELAY_SEC = 0.25  # be polite to a free public API
TIMEOUT_SEC = 15
MAX_RETRIES = 2


def fetch(url: str, params: dict) -> dict | None:
    """GET with a couple of retries; returns None (not an exception) for a
    persistent failure so the loop can keep going -- one bad combination
    (a model that didn't exist in that year, a transient network blip)
    should not kill a 320-call run."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(url, params=params, timeout=TIMEOUT_SEC)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 400:
                # Genuinely invalid combination (e.g. model/year never
                # existed) -- not worth retrying.
                return None
            # Other codes (429/5xx): brief backoff, then retry.
        except requests.RequestException:
            pass
        if attempt < MAX_RETRIES:
            time.sleep(1.0 * (attempt + 1))
    return None


def main():
    stats = {"recalls_calls": 0, "recalls_hits": 0, "recalls_records": 0,
              "complaints_calls": 0, "complaints_hits": 0, "complaints_records": 0,
              "empty_or_failed": 0}

    for make, model in MAKE_MODELS:
        for year in YEARS:
            params = {"make": make, "model": model, "modelYear": year}
            slug = f"{make}_{model}_{year}".replace(" ", "-").replace("/", "-")

            recalls = fetch(RECALLS_URL, params)
            stats["recalls_calls"] += 1
            time.sleep(REQUEST_DELAY_SEC)

            complaints = fetch(COMPLAINTS_URL, params)
            stats["complaints_calls"] += 1
            time.sleep(REQUEST_DELAY_SEC)

            got_any = False
            if recalls and recalls.get("results"):
                (OUT_DIR / f"recalls_{slug}.json").write_text(
                    json.dumps(recalls, ensure_ascii=False, indent=1), encoding="utf-8"
                )
                stats["recalls_hits"] += 1
                stats["recalls_records"] += len(recalls["results"])
                got_any = True

            if complaints and complaints.get("results"):
                (OUT_DIR / f"complaints_{slug}.json").write_text(
                    json.dumps(complaints, ensure_ascii=False, indent=1), encoding="utf-8"
                )
                stats["complaints_hits"] += 1
                stats["complaints_records"] += len(complaints["results"])
                got_any = True

            if not got_any:
                stats["empty_or_failed"] += 1

            print(f"{make:12s} {model:16s} {year} -> "
                  f"recalls={len(recalls['results']) if recalls and recalls.get('results') else 0:3d}  "
                  f"complaints={len(complaints['results']) if complaints and complaints.get('results') else 0:3d}")

    print("\n=== DONE ===")
    print(json.dumps(stats, indent=2))
    (OUT_DIR / "_fetch_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
