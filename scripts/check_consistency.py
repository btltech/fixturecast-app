#!/usr/bin/env python3
"""
check_consistency.py — FixtureCast data drift checker.

Fails (exit 1) if any of the following are out of sync:
  1. data/leagues.json IDs  vs  backend/config.json allowed_competitions
  2. data/leagues.json IDs  vs  FEATURED_LEAGUE_IDS in frontend leagues.js
  3. frontend/public/sitemap.xml routes  vs  static routes in AppContent.svelte

Run manually:
    python3 scripts/check_consistency.py

Or wire it into CI:
    - name: Drift check
      run: python3 scripts/check_consistency.py
"""

import json
import os
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent

# ── helpers ──────────────────────────────────────────────────────────────────

def load_json(path: Path) -> object:
    with open(path) as f:
        return json.load(f)


def _ids_from_text(text: str, array_name: str) -> set[int]:
    """Extract numeric IDs from a JS const array declaration (ignores comments)."""
    m = re.search(rf"export const {array_name}\s*=\s*\[([^\]]+)\]", text, re.DOTALL)
    if not m:
        return set()
    body = m.group(1)
    # Strip line comments so year-like numbers in comments aren't treated as IDs
    body = re.sub(r"//[^\n]*", "", body)
    # Strip block comments
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.DOTALL)
    nums = re.findall(r"\b(\d+)\b", body)
    return {int(n) for n in nums}


# ── check 1 — leagues.json vs config.json ────────────────────────────────────

def check_leagues_json_vs_config() -> list[str]:
    errors: list[str] = []
    leagues_path = ROOT / "data" / "leagues.json"
    config_path  = ROOT / "backend" / "config.json"

    if not leagues_path.exists():
        return [f"MISSING {leagues_path}"]
    if not config_path.exists():
        return [f"MISSING {config_path}"]

    league_ids = {l["id"] for l in load_json(leagues_path)}
    config_ids = set(load_json(config_path).get("allowed_competitions", []))

    only_in_json   = league_ids - config_ids
    only_in_config = config_ids - league_ids

    if only_in_json:
        errors.append(
            f"IDs in leagues.json but NOT in config.json allowed_competitions: {sorted(only_in_json)}"
        )
    if only_in_config:
        errors.append(
            f"IDs in config.json allowed_competitions but NOT in leagues.json: {sorted(only_in_config)}"
        )
    return errors


# ── check 2 — leagues.json vs FEATURED_LEAGUE_IDS ────────────────────────────

def check_featured_league_ids() -> list[str]:
    errors: list[str] = []
    leagues_path   = ROOT / "data" / "leagues.json"
    js_path        = ROOT / "frontend" / "src" / "services" / "leagues.js"

    if not leagues_path.exists() or not js_path.exists():
        return []  # already reported in check 1

    league_ids = {l["id"] for l in load_json(leagues_path)}
    featured   = _ids_from_text(js_path.read_text(), "FEATURED_LEAGUE_IDS")

    only_in_featured = featured - league_ids
    if only_in_featured:
        errors.append(
            f"FEATURED_LEAGUE_IDS entries not found in leagues.json: {sorted(only_in_featured)}"
        )
    # Note: leagues.json may contain leagues NOT in FEATURED_LEAGUE_IDS — that is fine.
    return errors


# ── check 3 — sitemap.xml routes vs AppContent.svelte ────────────────────────

# Routes intentionally omitted from the public sitemap (auth-only, admin, etc.)
_SITEMAP_EXCLUDES = {
    "/admin/metrics",
    "/accas",          # alias for /accumulators — same content, canonical is /accumulators
    "/today",          # alias for /fixtures — same content, canonical is /fixtures
}


def check_sitemap_routes() -> list[str]:
    errors: list[str] = []
    sitemap_path   = ROOT / "frontend" / "public" / "sitemap.xml"
    appcontents    = ROOT / "frontend" / "src" / "components" / "AppContent.svelte"

    if not sitemap_path.exists():
        return [f"MISSING {sitemap_path}"]
    if not appcontents.exists():
        return [f"MISSING {appcontents}"]

    # Parse sitemap URLs
    tree = ET.parse(sitemap_path)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    sitemap_paths = set()
    for url in tree.findall("sm:url/sm:loc", ns):
        text = (url.text or "").strip()
        # Extract path component
        m = re.search(r"https?://[^/]+(/.*)$", text)
        sitemap_paths.add(m.group(1) if m else text)

    # Extract static routes from AppContent.svelte (no :param segments)
    svelte_text = appcontents.read_text()
    raw_routes  = re.findall(r'path="(/[^"]*)"', svelte_text)
    static_routes = {r for r in raw_routes if ":" not in r} - _SITEMAP_EXCLUDES

    missing_from_sitemap = static_routes - sitemap_paths
    if missing_from_sitemap:
        errors.append(
            f"Static routes in AppContent.svelte but NOT in sitemap.xml: {sorted(missing_from_sitemap)}"
        )
    return errors


# ── check 4 — worker system prompt vs leagues.json ──────────────────────────

def check_worker_leagues() -> list[str]:
    """Check that the worker's COMPETITIONS COVERED block is in sync with leagues.json."""
    import subprocess
    gen_script = ROOT / "scripts" / "generate_worker_leagues.py"
    if not gen_script.exists():
        return [f"MISSING {gen_script}"]
    result = subprocess.run(
        [sys.executable, str(gen_script), "--check"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return [result.stdout.strip() or result.stderr.strip()]
    return []


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    checks = [
        ("leagues.json vs config.json", check_leagues_json_vs_config),
        ("FEATURED_LEAGUE_IDS vs leagues.json", check_featured_league_ids),
        ("sitemap.xml vs AppContent.svelte routes", check_sitemap_routes),
        ("worker system prompt vs leagues.json", check_worker_leagues),
    ]

    all_errors: list[str] = []
    for label, fn in checks:
        errs = fn()
        if errs:
            print(f"\n❌ {label}:")
            for e in errs:
                print(f"   • {e}")
            all_errors.extend(errs)
        else:
            print(f"✅ {label}")

    if all_errors:
        print(f"\n{len(all_errors)} consistency error(s) found — fix before deploying.")
        return 1

    print("\nAll consistency checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
