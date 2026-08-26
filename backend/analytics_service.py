"""
Attribution & Analytics Event Service for FixtureCast.

Features:
- Multi-step event tracking (landing, track_record_view, signup, click_cta).
- Bot and crawler detection via user-agent signatures.
- Sliding-window duplicate suppression (prevents double-counting fast page reloads).
- Privacy-preserving rotating IP hashing.
- Aggregated attribution reporting separating raw visits from likely human visits.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import re
from typing import Any, Dict, List, Optional

# Known crawler / bot signatures
BOT_REGEX = re.compile(
    r"(bot|crawl|spider|slurp|facebookexternalhit|whatsapp|telegrambot|twitterbot|"
    r"bytespider|gptbot|claudebot|googlebot|bingbot|yandexbot|duckduckbot|applebot|"
    r"semrushbot|ahrefsbot|mj12bot|python-requests|aiohttp|httpx|curl|wget|postman|"
    r"headlesschrome|phantomjs|lighthouse)",
    re.IGNORECASE,
)

# Allowed UTM platforms / sources
VALID_UTM_SOURCES = {"tiktok", "instagram", "youtube", "x", "twitter", "reddit", "facebook", "newsletter", "direct", "organic"}


def is_bot_user_agent(user_agent: Optional[str]) -> bool:
    if not user_agent:
        return False
    return bool(BOT_REGEX.search(user_agent))


def hash_ip(ip_str: Optional[str]) -> str:
    if not ip_str:
        return "unknown"
    # Rotating daily salt
    date_salt = datetime.utcnow().strftime("%Y-%m-%d")
    raw = f"{ip_str}:{date_salt}:fc_attribution_salt"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def log_event(
    event_data: Dict[str, Any],
    client_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    referrer: Optional[str] = None,
    db_conn: Any = None,
) -> Dict[str, Any]:
    """
    Ingests and records an attribution event with bot detection and duplicate suppression.
    """
    try:
        from backend.database import USE_POSTGRES, get_db, _ensure_analytics_events_table
    except ImportError:
        from database import USE_POSTGRES, get_db, _ensure_analytics_events_table

    session_id = str(event_data.get("session_id") or "").strip()
    if not session_id:
        session_id = f"anon_{hashlib.md5(str(datetime.utcnow().timestamp()).encode()).hexdigest()[:12]}"

    event_type = str(event_data.get("event_type") or "landing").strip().lower()
    landing_path = str(event_data.get("path") or "/today").strip()
    utm_source = str(event_data.get("utm_source") or "").strip().lower()
    utm_medium = str(event_data.get("utm_medium") or "").strip().lower()
    utm_campaign = str(event_data.get("utm_campaign") or "").strip().lower()
    utm_content = str(event_data.get("utm_content") or "").strip()  # Content ID e.g. fc_20260820_single_v1
    ref = str(referrer or event_data.get("referrer") or "").strip()
    ua = str(user_agent or "").strip()

    is_bot = 1 if is_bot_user_agent(ua) else 0
    ip_h = hash_ip(client_ip)

    conn_context = None
    if db_conn is None:
        conn_context = get_db()
        conn = conn_context.__enter__()
    else:
        conn = db_conn

    try:
        cursor = conn.cursor()
        _ensure_analytics_events_table(cursor)

        # Sliding window duplicate suppression (60 seconds for same session + event_type + path)
        cutoff_time = (datetime.utcnow() - timedelta(seconds=60)).strftime("%Y-%m-%d %H:%M:%S")
        ph = "%s" if USE_POSTGRES else "?"

        cursor.execute(
            f"""
            SELECT id FROM analytics_events
            WHERE session_id = {ph} AND event_type = {ph} AND landing_path = {ph} AND created_at >= {ph}
            LIMIT 1
            """,
            (session_id, event_type, landing_path, cutoff_time),
        )
        recent = cursor.fetchone()
        if recent:
            return {
                "status": "suppressed_duplicate",
                "session_id": session_id,
                "event_type": event_type,
            }

        # Insert new event
        if USE_POSTGRES:
            cursor.execute(
                """
                INSERT INTO analytics_events (
                    session_id, event_type, landing_path, utm_source,
                    utm_medium, utm_campaign, utm_content, referrer,
                    is_bot, ip_hash, user_agent
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    session_id, event_type, landing_path, utm_source or None,
                    utm_medium or None, utm_campaign or None, utm_content or None,
                    ref or None, is_bot, ip_h, ua[:255] if ua else None,
                ),
            )
            row = cursor.fetchone()
            event_id = row[0] if isinstance(row, (list, tuple)) else row["id"]
        else:
            cursor.execute(
                """
                INSERT INTO analytics_events (
                    session_id, event_type, landing_path, utm_source,
                    utm_medium, utm_campaign, utm_content, referrer,
                    is_bot, ip_hash, user_agent
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id, event_type, landing_path, utm_source or None,
                    utm_medium or None, utm_campaign or None, utm_content or None,
                    ref or None, is_bot, ip_h, ua[:255] if ua else None,
                ),
            )
            event_id = cursor.lastrowid

        try:
            conn.commit()
        except Exception:
            pass

        return {
            "status": "recorded",
            "event_id": event_id,
            "session_id": session_id,
            "event_type": event_type,
            "is_bot": bool(is_bot),
        }
    finally:
        if conn_context:
            conn_context.__exit__(None, None, None)


def get_attribution_summary(
    days: int = 30,
    db_conn: Any = None,
) -> Dict[str, Any]:
    """
    Returns aggregated traffic by platform, campaign, and content ID,
    clearly separating raw visits from likely human visits and reporting conversion funnels.
    """
    try:
        from backend.database import USE_POSTGRES, get_db, _ensure_analytics_events_table
    except ImportError:
        from database import USE_POSTGRES, get_db, _ensure_analytics_events_table

    since_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

    conn_context = None
    if db_conn is None:
        conn_context = get_db()
        conn = conn_context.__enter__()
    else:
        conn = db_conn

    try:
        cursor = conn.cursor()
        _ensure_analytics_events_table(cursor)
        ph = "%s" if USE_POSTGRES else "?"

        # Query all events in window
        cursor.execute(
            f"""
            SELECT session_id, event_type, utm_source, utm_campaign, utm_content, is_bot, created_at
            FROM analytics_events
            WHERE created_at >= {ph}
            ORDER BY created_at ASC
            """,
            (since_date,),
        )
        rows = cursor.fetchall()

        total_raw_events = len(rows)
        total_human_events = 0
        platforms: Dict[str, Dict[str, Any]] = {}
        content_items: Dict[str, Dict[str, Any]] = {}
        sessions_seen = set()
        human_sessions_seen = set()

        for row in rows:
            def _get(r, key, idx):
                return r[key] if isinstance(r, dict) or hasattr(r, "keys") else r[idx]

            s_id = _get(row, "session_id", 0)
            e_type = _get(row, "event_type", 1)
            source = (_get(row, "utm_source", 2) or "direct").lower()
            campaign = (_get(row, "utm_campaign", 3) or "general").lower()
            content_id = _get(row, "utm_content", 4) or "unspecified"
            is_bot = bool(_get(row, "is_bot", 5) or 0)

            if not is_bot:
                total_human_events += 1
                human_sessions_seen.add(s_id)
            sessions_seen.add(s_id)

            # Aggregate by platform/source
            if source not in platforms:
                platforms[source] = {
                    "raw_visits": 0,
                    "likely_human_visits": 0,
                    "unique_sessions": set(),
                    "human_sessions": set(),
                    "track_record_views": 0,
                    "signups": 0,
                }
            plat = platforms[source]
            plat["raw_visits"] += 1
            plat["unique_sessions"].add(s_id)
            if not is_bot:
                plat["likely_human_visits"] += 1
                plat["human_sessions"].add(s_id)
                if e_type == "track_record_view":
                    plat["track_record_views"] += 1
                elif e_type == "signup":
                    plat["signups"] += 1

            # Aggregate by content_id
            if content_id not in content_items:
                content_items[content_id] = {
                    "content_id": content_id,
                    "platform": source,
                    "raw_visits": 0,
                    "likely_human_visits": 0,
                    "track_record_views": 0,
                    "signups": 0,
                }
            c_item = content_items[content_id]
            c_item["raw_visits"] += 1
            if not is_bot:
                c_item["likely_human_visits"] += 1
                if e_type == "track_record_view":
                    c_item["track_record_views"] += 1
                elif e_type == "signup":
                    c_item["signups"] += 1

        # Format platform breakdown
        #
        # Each platform carries a reading of how much its numbers can bear.
        # This is deliberately NOT called statistical significance: twenty or
        # thirty human sessions can show which platform looks worth more
        # effort, and cannot establish a winner. Naming it significance would
        # invite exactly the conclusion the sample cannot support.
        MIN_DIRECTIONAL_SAMPLE = 20      # below this, a comparison says nothing
        COMPARABLE_SAMPLE = 30           # above this, a direction is worth acting on

        def _sample_reading(sessions: int) -> dict:
            if sessions >= COMPARABLE_SAMPLE:
                return {
                    "level": "directional",
                    "note": (
                        f"{sessions} human sessions — enough to show which way this platform "
                        "leans. Still not a proven winner; treat it as a direction to back, "
                        "not a result."
                    ),
                }
            if sessions >= MIN_DIRECTIONAL_SAMPLE:
                return {
                    "level": "weak",
                    "note": (
                        f"{sessions} human sessions — at the edge of meaning anything. "
                        f"Worth watching, not worth reallocating effort on."
                    ),
                }
            return {
                "level": "too_few",
                "note": (
                    f"{sessions} human sessions — too few to compare against another "
                    f"platform. Below {MIN_DIRECTIONAL_SAMPLE} the rates above move several "
                    "points on a single visit."
                ),
            }

        platform_summary = []
        for src, data in sorted(platforms.items(), key=lambda x: x[1]["likely_human_visits"], reverse=True):
            h_vis = data["likely_human_visits"]
            tr_views = data["track_record_views"]
            su = data["signups"]
            tr_rate = round((tr_views / h_vis * 100), 1) if h_vis > 0 else 0.0
            su_rate = round((su / h_vis * 100), 1) if h_vis > 0 else 0.0

            sessions = len(data["human_sessions"])
            platform_summary.append({
                "source": src,
                "raw_visits": data["raw_visits"],
                "likely_human_visits": h_vis,
                "unique_human_sessions": sessions,
                "track_record_views": tr_views,
                "signups": su,
                "track_record_view_rate_pct": tr_rate,
                "signup_rate_pct": su_rate,
                "sample": _sample_reading(sessions),
            })

        # Format content breakdown
        content_summary = []
        for cid, data in sorted(content_items.items(), key=lambda x: x[1]["likely_human_visits"], reverse=True):
            content_summary.append({
                "content_id": cid,
                "platform": data["platform"],
                "raw_visits": data["raw_visits"],
                "likely_human_visits": data["likely_human_visits"],
                "track_record_views": data["track_record_views"],
                "signups": data["signups"],
            })

        return {
            "period_days": days,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "totals": {
                "raw_events": total_raw_events,
                "likely_human_events": total_human_events,
                "unique_human_sessions": len(human_sessions_seen),
                "bot_events": total_raw_events - total_human_events,
            },
            "platforms": platform_summary,
            "content_performance": content_summary,
            "sample_guidance": (
                "Platform rates carry a 'sample' reading. Twenty to thirty human sessions "
                "is a minimum directional sample: it can show which platform looks "
                "promising and cannot establish a winner."
            ),
        }
    finally:
        if conn_context:
            conn_context.__exit__(None, None, None)
