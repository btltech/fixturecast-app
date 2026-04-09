#!/usr/bin/env python3
"""
generate_worker_leagues.py — sync FixtureCast's Cloudflare worker system prompt
from the canonical data/leagues.json.

Usage:
    python3 scripts/generate_worker_leagues.py          # patch the worker in place
    python3 scripts/generate_worker_leagues.py --check  # exit 1 if worker is stale

Run before every `wrangler deploy` to guarantee the assistant is in sync with
the canonical league list.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEAGUES_JSON  = ROOT / "data" / "leagues.json"
WORKER_FILE   = Path("/Users/mobolaji/Myassistant") / "cloudflare-worker-enhanced.js"

TIER_LABELS = {
    0: "FIFA & Continental Competitions",
    1: "Top Domestic Leagues",
    2: "Second Divisions & Promotion Leagues",
    3: "Domestic Cups & Knockout Competitions",
    4: "Friendlies",
}

# World/confederation competitions that don't need a country suffix
_NO_COUNTRY = {"World", ""}


def _entry(league: dict) -> str:
    country = league.get("country", "")
    name    = league["name"]
    if country and country not in _NO_COUNTRY:
        return f"{name} ({country})"
    return name


def generate_competitions_block(leagues: list) -> str:
    """Return the COMPETITIONS COVERED text block (no trailing newline)."""
    total = len(leagues)
    tiers: dict[int, list] = {}
    for l in leagues:
        tiers.setdefault(l["tier"], []).append(l)

    lines = [f"COMPETITIONS COVERED ({total} total across {len(tiers)} tiers):"]

    for tier_num in sorted(tiers.keys()):
        tier_leagues = tiers[tier_num]
        label = TIER_LABELS.get(tier_num, f"Tier {tier_num}")
        lines.append(f"\nTIER {tier_num} — {label}:")

        if tier_num == 4:
            # Keep the template-literal nav references as literal text so they
            # survive inside the JS template string unchanged.
            names = ", ".join(
                f"{l['name']} {l.get('emoji','')}" for l in tier_leagues
            )
            lines.append(names)
            lines.append(
                "NOTE: Friendly fixtures appear on [Fixtures](${nav.fixtures}) and "
                "[Predictions](${nav.predictions}) pages when populated by the football "
                "data API. ML predictions ARE generated for friendlies when fixture data "
                "is available."
            )
        else:
            entries = [_entry(l) for l in tier_leagues]
            # Wrap long lists at ~100 chars for readability
            line = ""
            wrapped = []
            for e in entries:
                if line and len(line) + len(e) + 2 > 100:
                    wrapped.append(line.rstrip(", "))
                    line = ""
                line += e + ", "
            if line:
                wrapped.append(line.rstrip(", "))
            lines.append("\n".join(wrapped))

    return "\n".join(lines)


# Regex that matches the COMPETITIONS COVERED block up to (but not including)
# the following SEASON FORMAT section.  Uses re.DOTALL.
_BLOCK_RE = re.compile(
    r"(COMPETITIONS COVERED \(\d+ total.*?\n)(.+?)(\nSEASON FORMAT:)",
    re.DOTALL,
)


def patch_worker(worker_text: str, new_block: str) -> str:
    """Replace the COMPETITIONS COVERED body in the worker text."""
    def _replace(m: re.Match) -> str:
        return new_block + m.group(3)

    result, count = _BLOCK_RE.subn(_replace, worker_text)
    if count == 0:
        raise RuntimeError(
            "Could not locate COMPETITIONS COVERED block in worker file. "
            "Check that the section heading and 'SEASON FORMAT:' marker are present."
        )
    return result


def main() -> int:
    check_only = "--check" in sys.argv

    if not LEAGUES_JSON.exists():
        print(f"ERROR: {LEAGUES_JSON} not found — run from repo root", file=sys.stderr)
        return 1
    if not WORKER_FILE.exists():
        print(f"ERROR: {WORKER_FILE} not found", file=sys.stderr)
        return 1

    leagues      = json.loads(LEAGUES_JSON.read_text())
    new_block    = generate_competitions_block(leagues)
    worker_text  = WORKER_FILE.read_text()
    patched_text = patch_worker(worker_text, new_block)

    if patched_text == worker_text:
        print("✅ Worker leagues block is already up to date.")
        return 0

    if check_only:
        print(
            "❌ Worker system prompt is STALE — run "
            "'python3 scripts/generate_worker_leagues.py' to sync."
        )
        return 1

    WORKER_FILE.write_text(patched_text)
    print(
        f"✅ Worker updated: {len(leagues)} competitions across "
        f"{len(set(l['tier'] for l in leagues))} tiers."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
