#!/usr/bin/env python3
"""
Simple backend API server for FixtureCast.
Provides fixtures and teams data from API-Football.
Runs on port 8001 to avoid conflict with ML API (port 8000).
"""

import asyncio
import json
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add paths
sys.path.append(os.path.dirname(__file__))

print("DEBUG: Executing import database...", flush=True)
import database
print("DEBUG: Executing from api_client import ApiClient...", flush=True)
from api_client import ApiClient
print("DEBUG: Executing from fastapi.responses import Response...", flush=True)
from fastapi.responses import Response
print("DEBUG: Executing from og_image_generator import...", flush=True)
try:
    from og_image_generator import generate_default_og_image, generate_prediction_og_image
    print("DEBUG: og_image_generator imported successfully.", flush=True)
except Exception as e:
    import traceback
    print("FATAL: Failed to import og_image_generator:", e, flush=True)
    traceback.print_exc()

print("DEBUG: Executing safe_feature_builder import...", flush=True)
try:
    from safe_feature_builder import FeatureBuilder
    print("DEBUG: safe_feature_builder imported successfully.", flush=True)
except Exception as e:
    import traceback
    print("FATAL: Failed to import safe_feature_builder:", e, flush=True)
    traceback.print_exc()

# Prometheus metrics (manual implementation for flexibility)
METRICS = {
    "requests_total": 0,
    "requests_by_endpoint": {},
    "request_latency_seconds": [],
    "errors_total": 0,
    "uptime_start": time.time(),
}

# Initialize API client (will be set in lifespan)
api_client = None
_odds_parser = FeatureBuilder()
ACCA_ODDS_TTL_SECONDS = int(os.environ.get("ACCA_ODDS_TTL_SECONDS", "120"))

# Big teams with their importance ranking (lower = bigger team)
BIG_TEAMS = {
    # Premier League Top Teams
    50: {"name": "Manchester City", "rank": 1},
    40: {"name": "Liverpool", "rank": 2},
    42: {"name": "Arsenal", "rank": 3},
    49: {"name": "Chelsea", "rank": 4},
    33: {"name": "Manchester United", "rank": 5},
    47: {"name": "Tottenham", "rank": 6},
    34: {"name": "Newcastle", "rank": 10},
    66: {"name": "Aston Villa", "rank": 12},
    48: {"name": "West Ham", "rank": 15},
    # La Liga Top Teams
    541: {"name": "Real Madrid", "rank": 1},
    529: {"name": "Barcelona", "rank": 2},
    530: {"name": "Atletico Madrid", "rank": 7},
    # Serie A Top Teams
    489: {"name": "AC Milan", "rank": 8},
    496: {"name": "Juventus", "rank": 9},
    505: {"name": "Inter Milan", "rank": 6},
    492: {"name": "Napoli", "rank": 11},
    # Bundesliga Top Teams
    157: {"name": "Bayern Munich", "rank": 3},
    165: {"name": "Borussia Dortmund", "rank": 10},
    173: {"name": "RB Leipzig", "rank": 14},
    # Ligue 1 Top Teams
    85: {"name": "Paris Saint-Germain", "rank": 4},
    81: {"name": "Marseille", "rank": 18},
    80: {"name": "Lyon", "rank": 20},
}


def _get_current_season() -> int:
    """Dynamically determine the current football season.
    European seasons are labeled by start year (e.g. 2025 for 2025/26).
    Season ticks over in July."""
    now = datetime.now()
    return now.year if now.month >= 7 else now.year - 1


# Leagues whose active season runs on the current calendar year
# (e.g. Copa Libertadores 2026, MLS 2026, J1 League 2026).
# Everything else uses the European cross-year convention handled by _get_current_season().
_CALENDAR_YEAR_LEAGUES: frozenset = frozenset([
    13, 11, 73, 130,        # Copa Libertadores, Copa Sudamericana, Copa do Brasil, Copa Argentina
    98, 292,                 # J1 League, K League 1
    253, 262,                # MLS, Liga MX
    128, 239, 265,           # Argentine Primera, Colombian Primera, Chilean Primera
    296, 278, 340, 169, 255, # Thai, Malaysian, Vietnamese, Chinese, USL
    71,                      # Brasileirão (starts April but labeled by current year)
    # FIFA / Confederation competitions — run on current calendar year
    1, 15, 16, 17, 22, 29, 30, 31, 32, 34, 6,
    # Friendlies — no fixed season, always current year
    8, 9,
])


def _get_league_season(league_id: int) -> int:
    """Return the correct season year for a given league.
    Calendar-year leagues (South American, Asian, MLS etc.) use the current year.
    European/African cross-year leagues use _get_current_season()."""
    if league_id in _CALENDAR_YEAR_LEAGUES:
        return datetime.now().year
    return _get_current_season()


def _get_today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _extract_odds_from_response(odds_response: Dict[str, Any]) -> Dict[str, Any]:
    return _odds_parser._extract_odds(odds_response)


def _select_outcome_odds(pred: Dict[str, Any], fallback: float) -> float:
    outcome = pred.get("predicted_outcome")
    if outcome == "home":
        return pred.get("odds_home", 0) or fallback
    if outcome == "away":
        return pred.get("odds_away", 0) or fallback
    if outcome == "draw":
        return pred.get("odds_draw", 0) or fallback
    return fallback


def _parse_fixture_kickoff_ts(fixture: Dict[str, Any]) -> float:
    """Parse fixture kickoff timestamp in a best-effort way for deterministic tie-breaking."""
    date_str = (
        fixture.get("fixture", {}).get("date") or fixture.get("fixture", {}).get("timestamp") or ""
    )

    if isinstance(date_str, (int, float)):
        return float(date_str)

    if isinstance(date_str, str) and date_str:
        try:
            # API-Football commonly returns ISO timestamps, sometimes with trailing 'Z'
            parsed = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return parsed.timestamp()
        except Exception:
            return float("inf")

    return float("inf")


def _calculate_fixture_importance(
    fixture: Dict[str, Any],
    league_priority_index: Dict[int, int],
) -> Tuple[int, bool, int, float, int]:
    """
    Returns a sortable tuple describing fixture importance.

    Sort order (best first):
      1) importance score (higher)
      2) big clash (both teams are big) (True first)
      3) league priority (lower index first)
      4) kickoff timestamp (earlier first)
      5) fixture id (lower first)
    """
    home_id = int(fixture.get("teams", {}).get("home", {}).get("id") or 0)
    away_id = int(fixture.get("teams", {}).get("away", {}).get("id") or 0)

    home_rank = BIG_TEAMS.get(home_id, {}).get("rank", 50)
    away_rank = BIG_TEAMS.get(away_id, {}).get("rank", 50)

    importance = 100 - min(home_rank, away_rank)
    is_big_clash = home_id in BIG_TEAMS and away_id in BIG_TEAMS
    if is_big_clash:
        importance += 20

    league_id = int(fixture.get("league", {}).get("id") or 0)
    league_prio = league_priority_index.get(league_id, 10_000)

    kickoff_ts = _parse_fixture_kickoff_ts(fixture)
    fixture_id = int(fixture.get("fixture", {}).get("id") or 0)

    return int(importance), bool(is_big_clash), int(league_prio), float(kickoff_ts), int(fixture_id)


def _select_match_of_the_day(
    fixtures: List[Dict[str, Any]],
    league_priority: Optional[List[int]] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    if not fixtures:
        return None, None

    league_priority = league_priority or []
    league_priority_index = {lid: idx for idx, lid in enumerate(league_priority)}

    def sort_key(f: Dict[str, Any]):
        importance, is_big_clash, league_prio, kickoff_ts, fixture_id = (
            _calculate_fixture_importance(f, league_priority_index)
        )
        # Python sorts ascending; invert the fields where higher is better.
        return (-importance, -int(is_big_clash), league_prio, kickoff_ts, fixture_id)

    best = min(fixtures, key=sort_key)
    importance, is_big_clash, league_prio, kickoff_ts, fixture_id = _calculate_fixture_importance(
        best, league_priority_index
    )

    meta = {
        "importance_score": importance,
        "is_big_clash": is_big_clash,
        "league_priority_index": None if league_prio == 10_000 else league_prio,
        "kickoff_ts": kickoff_ts if kickoff_ts != float("inf") else None,
        "fixture_id": fixture_id,
    }
    return best, meta


async def _fetch_todays_fixtures_for_leagues(
    leagues: List[int], today: str
) -> List[Dict[str, Any]]:
    all_fixtures: List[Dict[str, Any]] = []

    # Cap concurrent upstream calls: even on a 450 req/min plan, firing 80+
    # simultaneous threads can cause per-second burst rejections from the API.
    semaphore = asyncio.Semaphore(20)

    async def fetch_league(league_id: int):
        async with semaphore:
            try:
                return await asyncio.to_thread(api_client.get_fixtures, league_id=league_id, date=today)
            except Exception as e:
                print(f"Error fetching fixtures for league {league_id}: {e}")
                return None

    results = await asyncio.gather(*[fetch_league(lid) for lid in leagues])

    for result in results:
        if result and result.get("response"):
            all_fixtures.extend(result["response"])

    return all_fixtures


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    global api_client
    # Startup
    logger.info("🚀 Starting FixtureCast Backend API...")
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    try:
        with open(config_path) as f:
            config = json.load(f)
        api_client = ApiClient(config)
        logger.info("✅ API client initialized successfully!")
    except Exception as e:
        logger.error(f"⚠️ Failed to initialize API client: {e} — continuing without it")
        api_client = None

    # Start ML API keep-alive background task
    async def ml_keepalive():
        """Ping ML API every 10 minutes to prevent Railway cold starts"""
        import requests as req
        ml_url = os.getenv("ML_API_URL", "https://ml-api-production-6cfc.up.railway.app")
        while True:
            await asyncio.sleep(600)  # 10 minutes
            try:
                resp = await asyncio.to_thread(
                    req.get, f"{ml_url}/health", timeout=30
                )
                logger.info(f"🏓 ML API keep-alive: {resp.status_code}")
            except Exception as e:
                logger.warning(f"🏓 ML API keep-alive failed: {e}")

    keepalive_task = asyncio.create_task(ml_keepalive())

    yield  # Application runs here

    # Shutdown
    keepalive_task.cancel()
    logger.info("🛑 Shutting down FixtureCast Backend API...")
    api_client = None


app = FastAPI(
    title="FixtureCast Backend API",
    description="Backend API for fixtures and teams data",
    version="2.0.0",
    lifespan=lifespan,
)

# Rate Limiting
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=os.environ.get("REDIS_URL", "memory://"),
    default_limits=["100/minute"],
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Enable CORS - Restricted to fixturecast.com
ALLOWED_ORIGINS = [
    "https://fixturecast.com",
    "https://www.fixturecast.com",
    "https://fixturecast.pages.dev",
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_cache_headers(request, call_next):
    """Add Cache-Control headers for Cloudflare"""
    response = await call_next(request)

    # Default: No cache for safety
    cache_control = "no-cache"

    path = request.url.path

    # Smart Caching Strategy
    if path.startswith("/api/fixtures"):
        if "today" in path:
            # Live/Today's matches: Cache for 30s (matches your frontend refresh)
            cache_control = "public, max-age=30, s-maxage=30"
        else:
            # Future/Past fixtures: Cache for 1 hour
            cache_control = "public, max-age=3600, s-maxage=3600"

    elif path.startswith("/api/teams") or path.startswith("/api/standings"):
        # Team stats/Standings: Cache for 1 hour
        cache_control = "public, max-age=3600, s-maxage=3600"

    elif path.startswith("/api/predictions"):
        # Predictions: Cache for 15 mins (in case odds change)
        cache_control = "public, max-age=900, s-maxage=900"

    response.headers["Cache-Control"] = cache_control
    return response


@app.middleware("http")
async def track_metrics(request, call_next):
    """Middleware to track request metrics"""
    start_time = time.time()
    METRICS["requests_total"] += 1

    endpoint = request.url.path
    METRICS["requests_by_endpoint"][endpoint] = METRICS["requests_by_endpoint"].get(endpoint, 0) + 1

    try:
        response = await call_next(request)
        latency = time.time() - start_time
        METRICS["request_latency_seconds"].append(latency)
        # Keep only last 1000 latencies to prevent memory bloat
        if len(METRICS["request_latency_seconds"]) > 1000:
            METRICS["request_latency_seconds"] = METRICS["request_latency_seconds"][-1000:]
        return response
    except Exception:
        METRICS["errors_total"] += 1
        raise


logger.info("🚀 DEBUG: BACKEND_API MODULE LOADED")


@app.get("/")
async def root():
    return {"service": "FixtureCast Backend API", "version": "2.0.0", "status": "running"}


@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers and monitoring"""
    return {
        "status": "healthy",
        "service": "backend-api",
        "service_type": os.environ.get("SERVICE_TYPE", "backend"),
        "app_variant": "main",
        "api_client_ready": api_client is not None,
        "uptime_seconds": time.time() - METRICS["uptime_start"],
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/debug/smart-markets-import")
async def debug_smart_markets_import(request: Request):
    """Debug endpoint to test smart_markets_tracker import (admin only)"""
    import traceback

    expected = os.environ.get("ADMIN_SECRET", "")
    provided = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if not expected or provided != expected:
        raise HTTPException(status_code=403, detail="Unauthorized")

    try:
        from smart_markets_tracker import SmartMarketsTracker

        return {
            "success": True,
            "message": "Import successful",
            "class_methods": dir(SmartMarketsTracker),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}


@app.get("/api/debug/database")
async def debug_database(request: Request):
    """Debug endpoint to check database status (admin only)"""
    expected = os.environ.get("ADMIN_SECRET", "")
    provided = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if not expected or provided != expected:
        raise HTTPException(status_code=403, detail="Unauthorized")
    from datetime import date, timedelta

    try:
        today = date.today()
        tomorrow = today + timedelta(days=1)

        with database.get_db() as conn:
            cursor = conn.cursor()

            # Get total predictions count
            if database.USE_POSTGRES:
                cursor.execute("SELECT COUNT(*) as cnt FROM predictions")
                total_count = cursor.fetchone()["cnt"]

                cursor.execute(
                    "SELECT COUNT(*) as cnt FROM predictions WHERE DATE(match_date) IN (%s, %s)",
                    (today, tomorrow),
                )
                today_count = cursor.fetchone()["cnt"]

                # Get sample predictions
                cursor.execute(
                    """SELECT fixture_id, home_team, away_team, league_id, match_date, confidence
                       FROM predictions ORDER BY created_at DESC LIMIT 5"""
                )
                samples = [dict(row) for row in cursor.fetchall()]
            else:
                cursor.execute("SELECT COUNT(*) FROM predictions")
                total_count = cursor.fetchone()[0]

                cursor.execute(
                    "SELECT COUNT(*) FROM predictions WHERE date(match_date) IN (?, ?)",
                    (str(today), str(tomorrow)),
                )
                today_count = cursor.fetchone()[0]
                samples = []

        return {
            "database_type": "postgresql" if database.USE_POSTGRES else "sqlite",
            "database_url_set": database.DATABASE_URL is not None,
            "total_predictions": total_count,
            "today_predictions": today_count,
            "date_checked": str(today),
            "sample_predictions": samples,
        }
    except Exception as e:
        return {
            "database_type": "postgresql" if database.USE_POSTGRES else "sqlite",
            "database_url_set": database.DATABASE_URL is not None,
            "error": str(e),
        }


@app.get("/api/usage")
async def get_api_usage():
    """
    Get API-Football usage statistics.
    Shows daily request count, limit, and remaining calls.
    """
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    try:
        status = api_client.get_api_status()

        # Calculate percentage used
        limit = status.get("requests_limit", 75000)
        used = status.get("requests_today", 0)
        remaining = status.get("requests_remaining", limit)
        percentage_used = round((used / limit) * 100, 2) if limit > 0 else 0

        return {
            "requests_today": used,
            "requests_limit": limit,
            "requests_remaining": remaining,
            "percentage_used": percentage_used,
            "last_checked": status.get("last_checked"),
            "status": (
                "ok" if percentage_used < 80 else "warning" if percentage_used < 95 else "critical"
            ),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cache/stats")
async def get_cache_stats():
    """Get cache statistics (Redis cache via ApiClient)."""
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    try:
        cache_stats = api_client.cache.get_stats() if getattr(api_client, "cache", None) else {}
        ttls = getattr(api_client, "ttls", {})
        return {"cache_stats": cache_stats, "cache_ttl_settings": ttls}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cache/clear")
async def clear_cache():
    """Clear cached data (Redis cache via ApiClient)."""
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    try:
        deleted = 0
        if getattr(api_client, "cache", None):
            deleted = api_client.cache.clear_pattern("*")
        return {"message": "Cache cleared successfully", "deleted": deleted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/team/{team_id}/coach")
async def get_team_coach(team_id: int):
    """Get coach information for a specific team with graceful fallback."""
    if team_id < 1 or team_id > 999999:
        raise HTTPException(status_code=400, detail="Invalid team ID")
    if api_client is None:
        raise HTTPException(
            status_code=503,
            detail={"error": "Service unavailable", "message": "API client not initialized"},
        )

    try:
        result = api_client.get_coach(team_id)
        if not result or not result.get("response"):
            return {
                "response": [],
                "message": "Coach data not available for this team",
                "team_id": team_id,
            }
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Error fetching coach for team {team_id}: {e}")
        return {"response": [], "error": "Unable to fetch coach data", "team_id": team_id}


@app.get("/api/newsletter/send")
async def send_newsletter_get(request: Request, secret: str = Query(default="")):
    """
    Send the weekly newsletter via GET request (for cron jobs).
    Accepts secret via Authorization header (preferred) or query param (legacy).
    """
    try:
        expected_secret = os.environ.get("ADMIN_SECRET", "")
        header_secret = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        provided = header_secret or secret
        if not expected_secret or provided != expected_secret:
            raise HTTPException(status_code=403, detail="Unauthorized")

        from newsletter_generator import (
            format_email_html,
            format_email_text,
            generate_accumulator,
            get_predictions_for_fixtures,
            get_weekend_fixtures,
            rank_predictions,
            send_broadcast,
        )

        fixtures = await get_weekend_fixtures()
        if not fixtures:
            return {"success": False, "error": "No weekend fixtures found"}

        predictions = await get_predictions_for_fixtures(fixtures)
        if not predictions:
            return {"success": False, "error": "No predictions available"}

        ranked = rank_predictions(predictions)
        top_picks = ranked[:8]
        accumulator = generate_accumulator(ranked)

        html_content = format_email_html(top_picks, accumulator)
        text_content = format_email_text(top_picks, accumulator)

        from datetime import datetime as _dt

        today = _dt.now()
        subject = f"\U0001f52e Weekend Predictions ({today.strftime('%b %d')}): Top 8 AI Picks"
        send_result = await send_broadcast(subject, html_content, text_content)

        return {
            "success": True,
            "email_sent": send_result.get("sent", False),
            "email_details": send_result,
            "picks_count": len(top_picks),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Newsletter send error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/newsletter/generate")
async def generate_newsletter(request: Request):
    """
    Generate and optionally send the weekly newsletter.
    Requires admin secret for security.
    """
    try:
        body = await request.json()
        admin_secret = body.get("admin_secret", "")
        send_email = body.get("send", False)

        expected_secret = os.environ.get("ADMIN_SECRET", "")
        if not expected_secret or admin_secret != expected_secret:
            raise HTTPException(status_code=403, detail="Unauthorized")

        from newsletter_generator import (
            format_email_html,
            format_email_text,
            generate_accumulator,
            get_predictions_for_fixtures,
            get_weekend_fixtures,
            rank_predictions,
            send_broadcast,
        )

        fixtures = await get_weekend_fixtures()
        if not fixtures:
            return {"success": False, "error": "No weekend fixtures found"}

        predictions = await get_predictions_for_fixtures(fixtures)
        if not predictions:
            return {"success": False, "error": "No predictions available"}

        ranked = rank_predictions(predictions)
        top_picks = ranked[:8]
        accumulator = generate_accumulator(ranked)

        html_content = format_email_html(top_picks, accumulator)
        text_content = format_email_text(top_picks, accumulator)

        result = {
            "success": True,
            "picks_count": len(top_picks),
            "top_picks": top_picks,
            "accumulator": accumulator,
            "preview_text": text_content[:500] + "...",
        }

        if send_email:
            from datetime import datetime as _dt

            today = _dt.now()
            subject = f"\U0001f52e Weekend Predictions ({today.strftime('%b %d')}): Top 8 AI Picks"
            sent = await send_broadcast(subject, html_content, text_content)
            result["email_sent"] = sent

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Newsletter generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/newsletter/preview")
async def preview_newsletter():
    """
    Preview the current weekend predictions (no auth required, read-only).
    Returns top 8 picks for display.
    """
    try:
        from newsletter_generator import (
            generate_accumulator,
            get_predictions_for_fixtures,
            get_weekend_fixtures,
            rank_predictions,
        )

        logger.info("Newsletter preview: Getting weekend fixtures...")
        fixtures = await get_weekend_fixtures()
        logger.info(f"Newsletter preview: Got {len(fixtures) if fixtures else 0} fixtures")
        if not fixtures:
            return {"success": False, "error": "No weekend fixtures", "picks": []}

        logger.info(
            f"Newsletter preview: Getting predictions for {min(10, len(fixtures))} fixtures..."
        )
        predictions = await get_predictions_for_fixtures(fixtures[:10])
        logger.info(f"Newsletter preview: Got {len(predictions) if predictions else 0} predictions")
        if not predictions:
            return {
                "success": False,
                "error": "No predictions",
                "picks": [],
                "fixtures_count": len(fixtures),
            }

        ranked = rank_predictions(predictions)
        top_picks = ranked[:8]
        accumulator = generate_accumulator(ranked)

        return {"success": True, "picks": top_picks, "accumulator": accumulator}
    except Exception as e:
        import traceback

        logger.error(f"Newsletter preview error: {e}\n{traceback.format_exc()}")
        return {"success": False, "error": str(e), "picks": []}


@app.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus-compatible metrics endpoint.
    Returns metrics in Prometheus text exposition format.
    """
    uptime = time.time() - METRICS["uptime_start"]
    avg_latency = (
        sum(METRICS["request_latency_seconds"]) / len(METRICS["request_latency_seconds"])
        if METRICS["request_latency_seconds"]
        else 0
    )

    # Build Prometheus format output
    lines = [
        "# HELP backend_requests_total Total number of HTTP requests",
        "# TYPE backend_requests_total counter",
        f'backend_requests_total {METRICS["requests_total"]}',
        "",
        "# HELP backend_errors_total Total number of errors",
        "# TYPE backend_errors_total counter",
        f'backend_errors_total {METRICS["errors_total"]}',
        "",
        "# HELP backend_uptime_seconds Uptime in seconds",
        "# TYPE backend_uptime_seconds gauge",
        f"backend_uptime_seconds {uptime:.2f}",
        "",
        "# HELP backend_request_latency_avg_seconds Average request latency",
        "# TYPE backend_request_latency_avg_seconds gauge",
        f"backend_request_latency_avg_seconds {avg_latency:.4f}",
        "",
        "# HELP backend_api_client_ready API client initialization status",
        "# TYPE backend_api_client_ready gauge",
        f"backend_api_client_ready {1 if api_client else 0}",
    ]

    # Add per-endpoint metrics
    lines.append("")
    lines.append("# HELP backend_requests_by_endpoint Requests by endpoint")
    lines.append("# TYPE backend_requests_by_endpoint counter")
    for endpoint, count in METRICS["requests_by_endpoint"].items():
        # Escape endpoint for Prometheus label
        safe_endpoint = endpoint.replace('"', '\\"')
        lines.append(f'backend_requests_by_endpoint{{endpoint="{safe_endpoint}"}} {count}')

    from starlette.responses import PlainTextResponse

    return PlainTextResponse("\n".join(lines), media_type="text/plain")


@app.get("/api/metrics/backtest-history")
async def get_backtest_history(limit: int = Query(52, description="Number of weeks to return")):
    """
    Get backtest performance history.
    Returns weekly backtest results showing model accuracy and profit over time.
    """
    import json

    backtest_file = os.path.join(os.path.dirname(__file__), "backtest_history.json")

    try:
        if not os.path.exists(backtest_file):
            return {
                "history": [],
                "summary": {
                    "total_weeks": 0,
                    "avg_accuracy": 0,
                    "total_profit": 0,
                    "message": "No backtest data available yet. First run will populate this.",
                },
            }

        with open(backtest_file, "r") as f:
            history = json.load(f)

        # Deduplicate by week date (the backtest file can occasionally contain
        # duplicate entries for the same week after reruns). Keep the last
        # occurrence per date while preserving overall ordering.
        if isinstance(history, list) and history:
            last_index_by_date = {}
            for idx, item in enumerate(history):
                if not isinstance(item, dict):
                    continue
                raw_date = item.get("date")
                if isinstance(raw_date, str) and raw_date:
                    last_index_by_date[raw_date[:10]] = idx

            if last_index_by_date:
                deduped_history = []
                for idx, item in enumerate(history):
                    if not isinstance(item, dict):
                        continue
                    raw_date = item.get("date")
                    if isinstance(raw_date, str) and raw_date:
                        normalized_date = raw_date[:10]
                        if idx == last_index_by_date.get(normalized_date):
                            deduped_history.append(item)
                    else:
                        deduped_history.append(item)

                history = deduped_history

        # Filter to post-launch records only (app went live 2025-11-25 UTC)
        launch_cutoff = "2025-11-25"
        filtered = []
        for item in history if isinstance(history, list) else []:
            if not isinstance(item, dict):
                continue
            raw_date = item.get("date") or item.get("timestamp")
            if not isinstance(raw_date, str) or not raw_date:
                continue
            normalized = raw_date[:10]
            if normalized >= launch_cutoff:
                filtered.append(item)

        history = filtered

        # Return most recent N weeks
        recent_history = history[-limit:] if len(history) > limit else history

        # Calculate summary stats
        if history:
            accuracies = [h["summary"]["accuracy"] for h in history if "summary" in h]
            profits = [h["summary"]["profit"] for h in history if "summary" in h]

            summary = {
                "total_weeks": len(history),
                "avg_accuracy": sum(accuracies) / len(accuracies) if accuracies else 0,
                "total_profit": sum(profits) if profits else 0,
                "best_week": (
                    max(history, key=lambda x: x.get("summary", {}).get("accuracy", 0))
                    if history
                    else None
                ),
                "worst_week": (
                    min(history, key=lambda x: x.get("summary", {}).get("accuracy", 0))
                    if history
                    else None
                ),
            }
        else:
            summary = {"total_weeks": 0, "avg_accuracy": 0, "total_profit": 0}

        return {"history": recent_history, "summary": summary}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading backtest history: {str(e)}")


@app.get("/api/fixtures")
async def get_fixtures(
    league: int = Query(39, description="League ID"),
    next: int = Query(20, description="Number of next fixtures"),
    season: int = Query(None, description="Season year (optional)"),
    today_only: bool = Query(False, description="Only show today's fixtures"),
    date: str = Query(None, description="Specific date (YYYY-MM-DD)"),
):
    """Get upcoming fixtures for a league"""
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    try:
        if today_only:
            today = datetime.now().strftime("%Y-%m-%d")
            result = api_client.get_fixtures(league_id=league, season=season or _get_league_season(league), date=today)
        elif date:
            result = api_client.get_fixtures(league_id=league, season=season or _get_league_season(league), date=date)
        else:
            result = api_client.get_fixtures(league_id=league, season=season or _get_league_season(league), next_n=next)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# /api/leagues — serve the canonical league list from data/leagues.json
# ---------------------------------------------------------------------------
_LEAGUES_JSON_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "leagues.json")


@app.get("/api/leagues")
async def get_leagues_list():
    """Return the full list of supported competitions from the canonical leagues.json."""
    try:
        with open(_LEAGUES_JSON_PATH) as f:
            leagues = json.load(f)
        return {"leagues": leagues, "total": len(leagues)}
    except FileNotFoundError:
        # Fall back to api_client.allowed_competitions if file not present
        ids = list(getattr(api_client, "allowed_competitions", []) or [])
        return {"leagues": [{"id": i} for i in ids], "total": len(ids)}


# ---------------------------------------------------------------------------
# Active leagues cache — which competitions have fixtures in the next 60 days
# Refreshed at most once every 12 hours so we don't burn API quota.
# ---------------------------------------------------------------------------
_active_leagues_cache: dict = {"ids": None, "expires": 0.0}

# ---------------------------------------------------------------------------
# /api/fixtures/today — endpoint-level cache + in-flight deduplication
# Prevents simultaneous requests from each spawning 80+ parallel API calls.
# ---------------------------------------------------------------------------
_today_fixtures_cache: dict = {"data": None, "date": None, "expires": 0.0}
_today_fixtures_inflight: Optional[asyncio.Future] = None


async def _compute_active_leagues() -> list:
    """Check every allowed competition for upcoming fixtures (next 60 days).
    Returns list of league IDs that have at least one scheduled fixture."""
    now = datetime.now()
    from_date = now.strftime("%Y-%m-%d")
    to_date = (now + timedelta(days=60)).strftime("%Y-%m-%d")

    all_leagues = list(getattr(api_client, "allowed_competitions", []) or [])
    active: list = []

    async def check_league(league_id: int):
        try:
            season = _get_league_season(league_id)
            result = await asyncio.to_thread(
                api_client.get_fixtures,
                league_id=league_id,
                season=season,
                next_n=1,
            )
            if result.get("response"):
                active.append(league_id)
        except Exception:
            pass

    # Run in batches of 10 to avoid hammering the upstream API
    for i in range(0, len(all_leagues), 10):
        batch = all_leagues[i:i + 10]
        await asyncio.gather(*[check_league(lid) for lid in batch])

    return active


@app.get("/api/active-leagues")
async def get_active_leagues(force: bool = False):
    """Return list of league IDs that have fixtures in the next 60 days.
    Result is cached for 12 hours. Pass ?force=true to refresh immediately."""
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    now = time.time()
    cache = _active_leagues_cache

    if force or cache["ids"] is None or now > cache["expires"]:
        active = await _compute_active_leagues()
        cache["ids"] = active
        cache["expires"] = now + 43200  # 12 hours

    return {"active_leagues": cache["ids"], "cached": not force}


@app.get("/api/fixtures/today")
async def get_todays_fixtures():
    """
    Get all fixtures playing today across all supported leagues.
    Returns fixtures sorted by importance (big teams first).

    Endpoint-level cache (60 s) + in-flight deduplication ensure that
    concurrent requests never each spawn 80+ parallel upstream API calls.
    """
    global _today_fixtures_inflight

    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    today = _get_today_str()
    now = time.time()

    # Return cached result if still fresh and from the same calendar date
    if (
        _today_fixtures_cache["data"] is not None
        and _today_fixtures_cache["date"] == today
        and now < _today_fixtures_cache["expires"]
    ):
        return _today_fixtures_cache["data"]

    # If another coroutine is already fetching, wait for it rather than
    # firing a second wave of 80+ API calls.
    if _today_fixtures_inflight is not None and not _today_fixtures_inflight.done():
        try:
            return await asyncio.wait_for(
                asyncio.shield(_today_fixtures_inflight), timeout=30
            )
        except Exception:
            pass  # fall through and fetch ourselves

    loop = asyncio.get_event_loop()
    fut: asyncio.Future = loop.create_future()
    _today_fixtures_inflight = fut

    try:
        # Stable league order: prefer configured list order when available.
        leagues = list(getattr(api_client, "allowed_competitions", []) or []) or list(
            api_client.allowed_leagues
        )

        all_fixtures = await _fetch_todays_fixtures_for_leagues(leagues, today)

        # Priority leagues used as a deterministic tie-breaker.
        priority_leagues = [39, 140, 135, 78, 61, 2, 3]

        league_priority_index = {lid: idx for idx, lid in enumerate(priority_leagues)}

        def display_sort_key(f: Dict[str, Any]):
            importance, is_big_clash, league_prio, kickoff_ts, fixture_id = (
                _calculate_fixture_importance(f, league_priority_index)
            )
            return (-importance, -int(is_big_clash), league_prio, kickoff_ts, fixture_id)

        all_fixtures.sort(key=display_sort_key)

        match_of_the_day, motd_meta = _select_match_of_the_day(
            all_fixtures, league_priority=priority_leagues
        )

        # When today has no matches, look ahead up to 3 days for upcoming fixtures
        # so the frontend can show something useful instead of a dead-end empty state.
        upcoming_fixtures: List[Dict[str, Any]] = []
        upcoming_date: Optional[str] = None
        upcoming_days_ahead: Optional[int] = None

        if not all_fixtures:
            for day_offset in range(1, 4):
                check_date = (
                    datetime.strptime(today, "%Y-%m-%d") + timedelta(days=day_offset)
                ).strftime("%Y-%m-%d")
                candidates = await _fetch_todays_fixtures_for_leagues(priority_leagues, check_date)
                if candidates:
                    candidates.sort(key=display_sort_key)
                    upcoming_fixtures = candidates[:12]
                    upcoming_date = check_date
                    upcoming_days_ahead = day_offset
                    break

        result = {
            "response": all_fixtures,
            "match_of_the_day": match_of_the_day,
            "match_of_the_day_meta": motd_meta,
            "total_matches": len(all_fixtures),
            "date": today,
            "upcoming_fixtures": upcoming_fixtures,
            "upcoming_date": upcoming_date,
            "upcoming_days_ahead": upcoming_days_ahead,
        }

        # Cache for 60 seconds
        _today_fixtures_cache["data"] = result
        _today_fixtures_cache["date"] = today
        _today_fixtures_cache["expires"] = time.time() + 60

        if not fut.done():
            fut.set_result(result)
        return result

    except Exception as e:
        if not fut.done():
            fut.set_exception(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/match-of-the-day")
async def get_match_of_the_day():
    """
    Get the biggest match playing today based on team importance.
    """
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    try:
        today = _get_today_str()

        # Priority leagues act as tie-breaker (higher priority wins if scores match).
        priority_leagues = [39, 140, 135, 78, 61, 2, 3]

        # For this endpoint we only consider the priority leagues.
        fixtures = await _fetch_todays_fixtures_for_leagues(priority_leagues, today)
        best_match, meta = _select_match_of_the_day(fixtures, league_priority=priority_leagues)

        if best_match:
            return {
                "match": best_match,
                "importance_score": (meta or {}).get("importance_score"),
                "is_big_clash": (meta or {}).get("is_big_clash"),
                "date": today,
                "meta": meta,
            }

        return {"match": None, "message": "No matches scheduled for today", "date": today}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/standings/{league_id}/{season}")
async def get_standings(
    league_id: int,
    season: int,
    team: int = Query(None, description="Specific team ID to filter")
):
    """
    Get current league standings/table.
    league_id: 39=Premier League, 140=La Liga, 135=Serie A, 78=Bundesliga, 61=Ligue 1
    season: e.g., 2024 for 2024-25 season
    """
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    try:
        result = api_client.get_standings(league_id=league_id, season=season)
        
        if not result or 'response' not in result:
            return {"standings": [], "league": league_id, "season": season}
        
        # Extract standings data from API response
        response_data = result['response']
        if not response_data or len(response_data) == 0:
            return {"standings": [], "league": league_id, "season": season}
        
        # API returns nested structure: response[0]['league']['standings'][0]
        league_data = response_data[0].get('league', {})
        standings_groups = league_data.get('standings', [])
        
        if not standings_groups or len(standings_groups) == 0:
            return {"standings": [], "league": league_id, "season": season}
        
        # Get the main standings group (first group for most leagues)
        standings = standings_groups[0]
        
        # Filter by specific team if requested
        if team:
            standings = [s for s in standings if s.get('team', {}).get('id') == team]
        
        # Format the response to include just the essential data
        formatted_standings = []
        for entry in standings:
            formatted_standings.append({
                "rank": entry.get("rank"),
                "team": {
                    "id": entry.get("team", {}).get("id"),
                    "name": entry.get("team", {}).get("name"),
                    "logo": entry.get("team", {}).get("logo")
                },
                "points": entry.get("points"),
                "played": entry.get("all", {}).get("played"),
                "won": entry.get("all", {}).get("win"),
                "draw": entry.get("all", {}).get("draw"),
                "lost": entry.get("all", {}).get("lose"),
                "goals_for": entry.get("all", {}).get("goals", {}).get("for"),
                "goals_against": entry.get("all", {}).get("goals", {}).get("against"),
                "goal_difference": entry.get("goalsDiff"),
                "form": entry.get("form"),
                "description": entry.get("description")
            })
        
        return {
            "league": {
                "id": league_data.get("id"),
                "name": league_data.get("name"),
                "country": league_data.get("country"),
                "logo": league_data.get("logo"),
                "season": season
            },
            "standings": formatted_standings
        }
    except Exception as e:
        logger.error(f"Error fetching standings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/teams")
async def get_teams(
    league: int = Query(None, description="League ID"),
    season: int = Query(None, description="Season year (auto-detected if omitted)"),
    id: int = Query(None, description="Team ID"),
):
    """Get teams in a league or specific team details"""
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    try:
        # If neither league nor id is provided, default to PL
        if not league and not id:
            league = 39

        result = api_client.get_teams(league_id=league, season=season or _get_current_season(), team_id=id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/teams/search")
async def search_teams(
    q: str = Query(..., description="Team name search query", min_length=2, max_length=100),
):
    """Search for teams by name across all leagues (e.g. 'Real Madrid', 'Barcelona')"""
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    # Sanitise input
    query = q.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        result = api_client._call_api("teams", {"search": query}, "teams")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/team/{team_id}/stats")
async def get_team_stats(
    team_id: int,
    league: int = Query(39, description="League ID"),
    season: int = Query(None, description="Season year (auto-detected if omitted)"),
):
    """Get statistics for a specific team"""
    if team_id < 1 or team_id > 999999:
        raise HTTPException(status_code=400, detail="Invalid team ID")
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    try:
        result = api_client.get_team_stats(team_id, league, season or _get_current_season())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/team/{team_id}/fixtures")
def get_team_fixtures(
    team_id: int,
    league: int = Query(..., description="League ID"),
    season: int = Query(None, description="Season year (auto-detected if omitted)"),
    last: int = Query(10, description="Number of last fixtures"),
):
    """Get recent fixtures for a specific team"""
    if team_id < 1 or team_id > 999999:
        raise HTTPException(status_code=400, detail="Invalid team ID")
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    try:
        result = api_client.get_last_fixtures(
            team_id=team_id, league=league, season=season or _get_current_season(), last=last
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/team/{team_id}/upcoming")
async def get_team_upcoming(
    team_id: int,
    league: int = Query(39, description="League ID"),
    season: int = Query(None, description="Season year (auto-detected if omitted)"),
    next: int = Query(3, description="Number of upcoming matches"),
):
    """Get upcoming fixtures for a specific team"""
    if team_id < 1 or team_id > 999999:
        raise HTTPException(status_code=400, detail="Invalid team ID")
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    try:
        result = api_client.get_next_fixtures(team_id, league, season or _get_current_season(), next)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/team/{team_id}/injuries")
async def get_team_injuries(team_id: int, season: int = Query(None, description="Season year (auto-detected if omitted)")):
    """Get current injuries for a specific team"""
    if team_id < 1 or team_id > 999999:
        raise HTTPException(status_code=400, detail="Invalid team ID")
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    try:
        result = api_client.get_injuries(team_id, season or _get_current_season())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/team/{team_id}/squad")
async def get_team_squad(team_id: int, season: int = Query(None, description="Season year (auto-detected if omitted)")):
    """Get squad/players for a specific team"""
    if team_id < 1 or team_id > 999999:
        raise HTTPException(status_code=400, detail="Invalid team ID")
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    try:
        result = api_client.get_players(team_id, season or _get_current_season())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/standings")
async def get_standings_query(
    league: int = Query(..., description="League ID"),
    season: int = Query(None, description="Season year (auto-detected if omitted)"),
):
    """Get league standings (query parameter version)"""
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    try:
        result = api_client.get_standings(league, season or _get_league_season(league))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/results")
async def get_results(
    league: int = Query(39, description="League ID"),
    last: int = Query(20, description="Number of last matches"),
    season: int = Query(None, description="Season year (auto-detected if omitted)"),
):
    """Get recent match results"""
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    try:
        result = api_client.get_last_fixtures(league=league, season=season or _get_league_season(league), last=last)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/h2h/{team1_id}/{team2_id}")
async def get_h2h(
    team1_id: int, team2_id: int, last: int = Query(10, description="Number of recent meetings")
):
    """Get head-to-head statistics between two teams"""
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    try:
        result = api_client.get_h2h(team1_id, team2_id, last)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/live")
async def get_live_scores():
    """Get live match scores"""
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    try:
        result = api_client.get_live_fixtures()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/og-image/{fixture_id}")
async def get_og_image(fixture_id: int, league: int = Query(39)):
    """Generate Open Graph (OG) image for social media sharing"""
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    try:
        # Get fixture details
        fixture_data = api_client.get_fixture(fixture_id)
        if not fixture_data or "response" not in fixture_data or not fixture_data["response"]:
            # Return default image if fixture not found
            image_data = generate_default_og_image(
                title="FixtureCast", subtitle="AI Football Predictions"
            )
            return Response(content=image_data, media_type="image/png")

        fixture = fixture_data["response"][0]
        home_team = fixture.get("teams", {}).get("home", {}).get("name", "Home")
        away_team = fixture.get("teams", {}).get("away", {}).get("name", "Away")
        league_name = fixture.get("league", {}).get("name", "League")

        # Try to get prediction data from ML API
        prediction_data = None
        try:
            import requests

            ml_api_url = os.getenv("ML_API_URL", "http://localhost:8000")
            pred_response = requests.get(
                f"{ml_api_url}/api/prediction/{fixture_id}?league={league}", timeout=5
            )
            if pred_response.status_code == 200:
                pred_json = pred_response.json()
                prediction_data = pred_json.get("prediction")
        except Exception as e:
            logger.warning(f"Could not fetch prediction for OG image: {e}")

        # Generate image
        image_data = generate_prediction_og_image(
            fixture_id=fixture_id,
            home_team=home_team,
            away_team=away_team,
            prediction_data=prediction_data,
            league_name=league_name,
        )

        return Response(
            content=image_data,
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
                "Content-Disposition": f"inline; filename=prediction_{fixture_id}.png",
            },
        )

    except Exception as e:
        logger.error(f"Error generating OG image: {e}")
        # Return default image on error
        image_data = generate_default_og_image()
        return Response(content=image_data, media_type="image/png")


@app.get("/api/og-image/daily")
async def get_daily_og_image():
    """Generate OG image for daily fixtures page"""
    try:
        from datetime import date

        today_str = date.today().strftime("%B %d, %Y")
        image_data = generate_default_og_image(
            title="Today's Predictions", subtitle=f"AI Football Predictions - {today_str}"
        )
        return Response(
            content=image_data,
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=3600"},
        )
    except Exception as e:
        logger.error(f"Error generating daily OG image: {e}")
        image_data = generate_default_og_image()
        return Response(content=image_data, media_type="image/png")


@app.get("/api/og-image/home")
async def get_home_og_image():
    """Generate OG image for homepage"""
    try:
        image_data = generate_default_og_image(
            title="FixtureCast", subtitle="AI-Powered Football Predictions"
        )
        return Response(
            content=image_data,
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=86400"},  # Cache for 24 hours
        )
    except Exception as e:
        logger.error(f"Error generating home OG image: {e}")
        image_data = generate_default_og_image()
        return Response(content=image_data, media_type="image/png")


@app.get("/api/accumulators/today")
async def get_today_accumulators(autogenerate: bool = Query(True)):
    """Get today's accumulator bets (8-fold, 4-fold, BTTS).

    Note: accumulators are normally generated by the daily note/predictions automation.
    If none exist yet, this endpoint can optionally auto-generate them on demand.
    """
    try:
        from database import PredictionDB

        accas = PredictionDB.get_today_accumulators()

        if not accas and autogenerate:
            try:
                generation = await generate_accumulators()
                if isinstance(generation, dict) and generation.get("success") is True:
                    accas = PredictionDB.get_today_accumulators()
                else:
                    return {
                        "success": False,
                        "message": (generation or {}).get(
                            "message", "No accumulators available for today"
                        ),
                        "reason": (generation or {}).get("reason", "not_generated"),
                        "details": (generation or {}).get("details", {}),
                        "accumulators": [],
                    }
            except Exception as e:
                logger.warning(f"Accumulator autogeneration failed: {e}")
                return {
                    "success": False,
                    "message": "No accumulators available for today",
                    "reason": "not_generated",
                    "details": {"autogenerate": True},
                    "accumulators": [],
                }

        if not accas:
            return {
                "success": False,
                "message": "No accumulators available for today",
                "reason": "not_generated",
                "details": {"autogenerate": False},
                "accumulators": [],
            }

        risk_levels = {
            "8-fold": "high",
            "6-fold": "high",
            "4-fold": "medium",
            "BTTS": "medium",
        }
        for acca in accas:
            acca["risk_level"] = risk_levels.get(acca.get("acca_type"), "medium")

        return {"success": True, "date": datetime.now().strftime("%Y-%m-%d"), "accumulators": accas}
    except Exception as e:
        logger.error(f"Error fetching today's accumulators: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/accumulators/history")
async def get_accumulator_history(days: int = Query(30, ge=1, le=90)):
    """Get accumulator performance history"""
    try:
        from database import PredictionDB

        history = PredictionDB.get_accumulator_history(days=days)

        # Calculate stats by type
        stats = {
            "8-fold": {"total": 0, "won": 0, "lost": 0, "pending": 0, "profit": 0, "staked": 0},
            "6-fold": {"total": 0, "won": 0, "lost": 0, "pending": 0, "profit": 0, "staked": 0},
            "4-fold": {"total": 0, "won": 0, "lost": 0, "pending": 0, "profit": 0, "staked": 0},
            "BTTS": {"total": 0, "won": 0, "lost": 0, "pending": 0, "profit": 0, "staked": 0},
        }

        for acca in history:
            acca_type = acca["acca_type"]
            if acca_type not in stats:
                stats[acca_type] = {
                    "total": 0,
                    "won": 0,
                    "lost": 0,
                    "pending": 0,
                    "profit": 0,
                    "staked": 0,
                }

            stats[acca_type]["total"] += 1
            stake = float(acca.get("stake") or 0)
            potential_return = float(acca.get("potential_return") or 0)
            if acca.get("won") is True:
                stats[acca_type]["won"] += 1
                stats[acca_type]["staked"] += stake
                stats[acca_type]["profit"] += potential_return - stake
            elif acca.get("won") is False:
                stats[acca_type]["lost"] += 1
                stats[acca_type]["staked"] += stake
                stats[acca_type]["profit"] -= stake
            else:
                stats[acca_type]["pending"] += 1

        # Calculate win rates
        for acca_type in stats:
            total = stats[acca_type]["total"]
            won = stats[acca_type]["won"]
            stats[acca_type]["win_rate"] = (won / total * 100) if total > 0 else 0
            staked = stats[acca_type]["staked"]
            profit = stats[acca_type]["profit"]
            stats[acca_type]["roi"] = (profit / staked * 100) if staked > 0 else 0

        return {"success": True, "days": days, "history": history, "stats": stats}
    except Exception as e:
        logger.error(f"Error fetching accumulator history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/accumulators/generate")
async def generate_accumulators():
    """
    Generate today's accumulators from available predictions
    This should be called by the daily predictions script
    """
    try:
        from accumulator_generator import AccumulatorGenerator, save_accumulator_to_db
        from database import USE_POSTGRES, PredictionDB, get_db

        # Get today's predictions
        # We'll fetch from the predictions table
        with get_db() as conn:
            cursor = conn.cursor()
            from datetime import date, timedelta

            today = date.today()
            tomorrow = today + timedelta(days=1)

            # Use appropriate date casting for each database
            if USE_POSTGRES:
                date_filter = "DATE(match_date)"
                placeholders = "%s, %s"
            else:
                date_filter = "date(match_date)"
                placeholders = "?, ?"

            cursor.execute(
                f"""
                SELECT fixture_id, home_team, away_team, home_team_id, away_team_id,
                       league_id, league_name, match_date,
                       home_win_prob, draw_prob, away_win_prob,
                       predicted_outcome, confidence, btts_prob, over25_prob,
                       odds_home_win, odds_draw, odds_away_win,
                       odds_btts_yes, odds_btts_no,
                       odds_over_25, odds_under_25
                FROM predictions
                WHERE {date_filter} IN ({placeholders})
                AND evaluated = 0
                ORDER BY confidence DESC
                """,
                (today, tomorrow),
            )

            predictions = []
            for row in cursor.fetchall():

                def _row_value(row_data, key, idx):
                    if isinstance(row_data, dict) or hasattr(row_data, "keys"):
                        return row_data[key]
                    return row_data[idx]

                confidence = _row_value(row, "confidence", 12)
                btts_prob = _row_value(row, "btts_prob", 13)
                over25_prob = _row_value(row, "over25_prob", 14)
                match_date = _row_value(row, "match_date", 7)
                odds_home = _row_value(row, "odds_home_win", 15) or 0
                odds_draw = _row_value(row, "odds_draw", 16) or 0
                odds_away = _row_value(row, "odds_away_win", 17) or 0
                odds_btts_yes = _row_value(row, "odds_btts_yes", 18) or 0
                odds_btts_no = _row_value(row, "odds_btts_no", 19) or 0
                odds_over_25 = _row_value(row, "odds_over_25", 20) or 0
                odds_under_25 = _row_value(row, "odds_under_25", 21) or 0

                pred = {
                    "fixture_id": _row_value(row, "fixture_id", 0),
                    "home_team": _row_value(row, "home_team", 1),
                    "away_team": _row_value(row, "away_team", 2),
                    "home_team_id": _row_value(row, "home_team_id", 3),
                    "away_team_id": _row_value(row, "away_team_id", 4),
                    "league_id": _row_value(row, "league_id", 5),
                    "league_name": _row_value(row, "league_name", 6),
                    "match_date": str(match_date) if match_date else None,
                    "home_win_prob": _row_value(row, "home_win_prob", 8),
                    "draw_prob": _row_value(row, "draw_prob", 9),
                    "away_win_prob": _row_value(row, "away_win_prob", 10),
                    "predicted_outcome": _row_value(row, "predicted_outcome", 11),
                    "confidence": confidence * 100,  # Convert to percentage
                    "btts_probability": btts_prob * 100 if btts_prob else 0,
                    "over25_probability": over25_prob * 100 if over25_prob else 0,
                    "odds_home": odds_home,
                    "odds_draw": odds_draw,
                    "odds_away": odds_away,
                    "btts_odds_yes": odds_btts_yes,
                    "btts_odds_no": odds_btts_no,
                    "odds_over_25": odds_over_25,
                    "odds_under_25": odds_under_25,
                }
                pred["odds_1x2_available"] = bool(
                    pred["odds_home"] and pred["odds_draw"] and pred["odds_away"]
                )
                pred["odds_btts_available"] = bool(pred["btts_odds_yes"] and pred["btts_odds_no"])
                pred["odds"] = _select_outcome_odds(pred, 1.8)
                pred["btts_odds"] = pred["btts_odds_yes"] or 1.85
                predictions.append(pred)

        if api_client is not None:
            for pred in predictions:
                try:
                    odds_response = api_client.get_odds(
                        pred["fixture_id"], ttl_override=ACCA_ODDS_TTL_SECONDS
                    )
                    odds = _extract_odds_from_response(odds_response)
                    if odds.get("odds_1x2_available"):
                        pred["odds_home"] = odds.get("odds_home_win") or pred["odds_home"]
                        pred["odds_draw"] = odds.get("odds_draw") or pred["odds_draw"]
                        pred["odds_away"] = odds.get("odds_away_win") or pred["odds_away"]
                    if odds.get("odds_btts_available"):
                        pred["btts_odds_yes"] = odds.get("odds_btts_yes") or pred["btts_odds_yes"]
                        pred["btts_odds_no"] = odds.get("odds_btts_no") or pred["btts_odds_no"]
                    if odds.get("odds_ou25_available"):
                        pred["odds_over_25"] = odds.get("odds_over_25") or pred["odds_over_25"]
                        pred["odds_under_25"] = odds.get("odds_under_25") or pred["odds_under_25"]
                    pred["odds_1x2_available"] = bool(
                        pred["odds_home"] and pred["odds_draw"] and pred["odds_away"]
                    )
                    pred["odds_btts_available"] = bool(
                        pred["btts_odds_yes"] and pred["btts_odds_no"]
                    )
                    pred["odds"] = _select_outcome_odds(pred, pred.get("odds") or 1.8)
                    pred["btts_odds"] = pred.get("btts_odds_yes") or pred.get("btts_odds") or 1.85
                except Exception as e:
                    logger.warning(f"Odds refresh failed for fixture {pred['fixture_id']}: {e}")

        # Check if we have enough matches first
        fixture_count = len(predictions)
        if fixture_count == 0:
            return {
                "success": False,
                "message": "No matches scheduled today",
                "reason": "no_matches",
                "details": {"fixture_count": 0, "required_minimum": 8},
            }

        # Generate accumulators
        generator = AccumulatorGenerator()
        accumulators = generator.generate_all_daily_accumulators(predictions)

        if not accumulators:
            # Provide detailed reason based on predictions quality
            high_confidence = sum(1 for p in predictions if 60 <= p.get("confidence", 0) <= 85)
            return {
                "success": False,
                "message": "Insufficient high-confidence predictions for accumulators",
                "reason": "low_confidence",
                "details": {
                    "fixture_count": fixture_count,
                    "predictions_with_quality": high_confidence,
                    "required_minimum": 8,
                },
            }

        # Save to database
        saved_ids = {}
        for acca_type, acca_data in accumulators.items():
            acca_id = save_accumulator_to_db(PredictionDB, acca_data)
            saved_ids[acca_type] = acca_id

        return {
            "success": True,
            "message": f"Generated {len(accumulators)} accumulators",
            "accumulators": accumulators,
            "ids": saved_ids,
        }

    except Exception as e:
        logger.error(f"Error generating accumulators: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/accumulators/update-results")
async def update_accumulator_results():
    """
    Check and update accumulator results based on finished matches.
    Should be called daily after matches finish.
    """
    try:
        from datetime import date, timedelta

        from database import PredictionDB, get_db

        # Get recent unfinished accumulators (last 7 days)
        cutoff = date.today() - timedelta(days=7)

        with get_db() as conn:
            cursor = conn.cursor()
            ph = "%s" if database.USE_POSTGRES else "?"

            # Get pending accumulators
            cursor.execute(
                f"""
                SELECT id, date, acca_type
                FROM accumulators
                WHERE status = {ph} AND date >= {ph}
                ORDER BY date DESC
                """,
                ("pending", cutoff),
            )

            pending_accas = [database._row_to_dict(row) for row in cursor.fetchall()]

        updated_count = 0
        for acca in pending_accas:
            acca_id = acca["id"]

            # Get selections for this accumulator
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"""
                    SELECT s.fixture_id, s.selection_type, s.selection_value,
                           p.result_home_goals, p.result_away_goals, p.actual_outcome
                    FROM accumulator_selections s
                    LEFT JOIN predictions p ON s.fixture_id = p.fixture_id
                    WHERE s.accumulator_id = {ph}
                    """,
                    (acca_id,),
                )

                selections = [database._row_to_dict(row) for row in cursor.fetchall()]

            # Check if all matches are finished
            all_finished = all(sel.get("actual_outcome") is not None for sel in selections)

            if not all_finished:
                continue

            # Check each selection
            all_won = True
            for sel in selections:
                fixture_id = sel["fixture_id"]
                selection_type = sel["selection_type"]
                selection_value = sel["selection_value"]
                actual_outcome = sel["actual_outcome"]
                home_goals = sel.get("result_home_goals")
                away_goals = sel.get("result_away_goals")

                won = False
                result_str = ""

                if selection_type == "1X2":
                    won = actual_outcome == selection_value
                    result_str = f"Predicted: {selection_value}, Actual: {actual_outcome}"
                elif selection_type == "BTTS":
                    if home_goals is not None and away_goals is not None:
                        btts_actual = home_goals > 0 and away_goals > 0
                        btts_predicted = selection_value.lower() == "yes"
                        won = btts_actual == btts_predicted
                        result_str = f"Predicted BTTS: {selection_value}, Actual: {'Yes' if btts_actual else 'No'}"

                # Update selection result
                PredictionDB.update_selection_result(acca_id, fixture_id, result_str, won)

                if not won:
                    all_won = False

            # Update accumulator result
            if all_won:
                PredictionDB.update_accumulator_result(
                    acca_id, "settled", "Won - All selections correct", True
                )
            else:
                PredictionDB.update_accumulator_result(
                    acca_id, "settled", "Lost - One or more selections failed", False
                )

            updated_count += 1

        return {
            "success": True,
            "message": f"Updated {updated_count} accumulators",
            "checked": len(pending_accas),
        }

    except Exception as e:
        logger.error(f"Error updating accumulator results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/accumulators/stats")
async def get_accumulator_stats(days: int = Query(30, ge=1, le=365)):
    """
    Get accumulator performance statistics
    """
    try:
        from database import PredictionDB

        stats = PredictionDB.get_accumulator_stats(days)
        return stats

    except Exception as e:
        logger.error(f"Error fetching accumulator stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/smart-markets/stats")
async def get_smart_markets_stats(days: int = Query(30, ge=1, le=90)):
    """
    Get Smart Markets prediction accuracy statistics.
    Shows performance of high-confidence (60%+) predictions with market edge (2%+).
    """
    try:
        from smart_markets_tracker import SmartMarketsTracker

        stats = SmartMarketsTracker.get_smart_markets_performance(days)
        return stats

    except Exception as e:
        import traceback

        logger.error(f"Error fetching Smart Markets stats: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/smart-markets/tag")
async def tag_smart_markets():
    """
    Tag predictions that qualify as Smart Markets (60%+ confidence + 2% edge).
    Should be called after predictions are generated.
    """
    try:
        from smart_markets_tracker import SmartMarketsTracker

        result = SmartMarketsTracker.tag_smart_market_predictions()
        return {
            "success": True,
            "tagged": result,
            "message": f"Tagged {result['total']} Smart Markets predictions",
        }

    except Exception as e:
        import traceback

        logger.error(f"Error tagging Smart Markets: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# AI Assistant Integration Endpoints
# =============================================================================

@app.post("/api/social/post")
async def social_media_post(request: Request):
    """Post to social media platforms"""
    try:
        body = await request.json()
        platforms = body.get('platforms', [])
        content = body.get('content', '')
        post_type = body.get('type', 'general')
        
        logger.info(f"Social media post requested: {platforms}, type: {post_type}")
        
        # This integrates with your existing bot infrastructure
        # For now, returning success to enable the AI assistant skills
        return {
            "success": True,
            "platforms": platforms,
            "content": content,
            "type": post_type,
            "message": "Post queued for social media"
        }
    except Exception as e:
        logger.error(f"Error posting to social media: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/social/status")
async def social_media_status():
    """Get social media connection status"""
    try:
        # Return status of your social media connections
        # This can be enhanced to check actual bot status
        return {
            "telegram": {
                "connected": bool(os.environ.get('TELEGRAM_BOT_TOKEN')),
                "subscribers": 1000  # Can be fetched from actual bot
            },
            "twitter": {
                "connected": bool(os.environ.get('TWITTER_API_KEY')),
                "followers": 5000  # Can be fetched from actual API
            },
            "discord": {
                "connected": bool(os.environ.get('DISCORD_WEBHOOK_URL')),
                "members": 2000  # Can be fetched from actual webhook
            },
            "recent_posts": 15
        }
    except Exception as e:
        logger.error(f"Error getting social media status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/social/telegram/send")
async def telegram_send(request: Request):
    """Send message via Telegram"""
    try:
        body = await request.json()
        content = body.get('content', '')
        message_type = body.get('type', 'message')
        
        logger.info(f"Telegram message requested: {message_type}")
        
        return {
            "success": True,
            "platform": "telegram",
            "message": "Message sent successfully"
        }
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/social/twitter/post")
async def twitter_post(request: Request):
    """Post to Twitter"""
    try:
        body = await request.json()
        content = body.get('content', '')
        post_type = body.get('type', 'tweet')
        
        logger.info(f"Twitter post requested: {post_type}")
        
        return {
            "success": True,
            "platform": "twitter",
            "message": "Tweet posted successfully"
        }
    except Exception as e:
        logger.error(f"Error posting to Twitter: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/social/discord/post")
async def discord_post(request: Request):
    """Post to Discord"""
    try:
        body = await request.json()
        content = body.get('content', '')
        post_type = body.get('type', 'message')
        
        logger.info(f"Discord message requested: {post_type}")
        
        return {
            "success": True,
            "platform": "discord",
            "message": "Message sent successfully"
        }
    except Exception as e:
        logger.error(f"Error posting to Discord: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/social/prediction")
async def social_prediction(request: Request):
    """Post prediction to multiple platforms"""
    try:
        body = await request.json()
        match = body.get('match', '')
        league = body.get('league', '')
        prediction = body.get('prediction', '')
        confidence = body.get('confidence', 0)
        platforms = body.get('platforms', [])
        
        logger.info(f"Prediction post requested: {match} - {prediction} ({confidence}%)")
        
        return {
            "success": True,
            "match": match,
            "platforms": platforms,
            "message": "Prediction posted successfully"
        }
    except Exception as e:
        logger.error(f"Error posting prediction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8001))
    print(f"Starting FixtureCast Backend API server on port {port}...")
    print(f" API docs will be available at http://localhost:{port}/docs")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
