"""Persistent heartbeat for scheduled capture jobs.

Why this exists
---------------
The `daily-edge-capture` GitHub Action commits snapshots to main. Verifying that
it actually ran is impossible from an environment without GitHub credentials:
a local clone only reflects the last `git pull`, so "no commit dated today"
is equally consistent with success and with failure.

Reading the committed file back off a deployed container does not solve it
either -- the container serves whatever was baked in at deploy time, so the
answer would depend on redeploy timing rather than on the job.

So the job pushes its own status here over HTTP at the end of every run, and we
persist it. The stored row is then the single source of truth for "did the
capture run today", readable by anything that can reach the public API.

Storage is deliberately a single row per job name, upserted via delete+insert to
stay portable across the SQLite and PostgreSQL backends in database.py.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import database

logger = logging.getLogger(__name__)

# A capture older than this is treated as stale. The cron is 06:00 UTC but
# GitHub's scheduled-run queue routinely delays it by ~2h, so a full day plus
# slack avoids flagging a merely-late run as a missed one.
STALE_AFTER_HOURS = 30

_TABLE = "capture_heartbeat"


def _placeholder() -> str:
    return "%s" if database.USE_POSTGRES else "?"


def ensure_table() -> None:
    """Create the heartbeat table if it does not exist. Idempotent."""
    with database.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {_TABLE} (
                job           TEXT PRIMARY KEY,
                captured_at   TEXT,
                rows_captured INTEGER,
                committed     INTEGER,
                run_url       TEXT,
                recorded_at   TEXT NOT NULL
            )
            """
        )


def record(
    job: str,
    captured_at: Optional[str],
    rows_captured: int = 0,
    committed: bool = False,
    run_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Store the outcome of a capture run, replacing any previous row for `job`."""
    ensure_table()
    recorded_at = datetime.now(timezone.utc).isoformat()
    ph = _placeholder()

    with database.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {_TABLE} WHERE job = {ph}", (job,))
        cursor.execute(
            f"""
            INSERT INTO {_TABLE}
                (job, captured_at, rows_captured, committed, run_url, recorded_at)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """,
            (job, captured_at, int(rows_captured), 1 if committed else 0, run_url, recorded_at),
        )

    return {
        "job": job,
        "captured_at": captured_at,
        "rows_captured": int(rows_captured),
        "committed": bool(committed),
        "run_url": run_url,
        "recorded_at": recorded_at,
    }


def _age_hours(timestamp: Optional[str]) -> Optional[float]:
    if not timestamp:
        return None
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - parsed).total_seconds() / 3600.0


def read(job: str) -> Dict[str, Any]:
    """Return the stored heartbeat for `job`, annotated with age and staleness.

    Never raises for the ordinary "nothing recorded yet" case -- that is a
    normal state on a fresh database, not an error, and callers should be able
    to distinguish it from "the job failed".
    """
    try:
        ensure_table()
        ph = _placeholder()
        with database.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT job, captured_at, rows_captured, committed, run_url, recorded_at
                FROM {_TABLE} WHERE job = {ph}
                """,
                (job,),
            )
            row = cursor.fetchone()
    except Exception as exc:  # pragma: no cover - depends on deployed DB
        logger.error("capture_heartbeat read failed: %s", exc)
        return {
            "status": "unavailable",
            "job": job,
            "message": str(exc),
        }

    if row is None:
        return {
            "status": "never",
            "job": job,
            "message": (
                "No heartbeat recorded yet. Expected once per run of the "
                "daily-edge-capture GitHub Action."
            ),
        }

    row = dict(row)
    captured_at = row.get("captured_at")
    age = _age_hours(row.get("recorded_at"))
    stale = age is not None and age > STALE_AFTER_HOURS

    return {
        "status": "stale" if stale else "ok",
        "job": row.get("job", job),
        "captured_at": captured_at,
        "rows_captured": row.get("rows_captured"),
        "committed": bool(row.get("committed")),
        "run_url": row.get("run_url"),
        "recorded_at": row.get("recorded_at"),
        "age_hours": round(age, 2) if age is not None else None,
        "stale_after_hours": STALE_AFTER_HOURS,
    }
