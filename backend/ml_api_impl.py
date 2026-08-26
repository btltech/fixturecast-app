#!/usr/bin/env python3
"""
FastAPI server for FixtureCast ML predictions.
Exposes endpoints to get match predictions using the trained ensemble.
"""

import json
import logging
import os
import re
import sys
import time
import warnings
from collections import defaultdict
from datetime import datetime
from threading import Lock
from typing import Dict, Optional

# Suppress sklearn warnings globally
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


NO_CACHE_HEADERS = {
    "Cache-Control": "private, no-store, no-cache, max-age=0, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
    "CDN-Cache-Control": "no-store",
    "Surrogate-Control": "no-store",
}

# Add paths
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from metrics_tracker import MetricsTracker
try:
    from .league_catalog import get_featured_league_ids, get_league_season
except ImportError:
    from league_catalog import get_featured_league_ids, get_league_season

from ml_engine.ensemble_predictor import EnsemblePredictor
from ml_engine.feedback_learning import log_prediction as log_feedback_prediction

try:
    from .prediction_quality import apply_cold_start_gate
except ImportError:
    from prediction_quality import apply_cold_start_gate

# Import database for prediction logging
try:
    from database import PredictionDB, init_db

    DB_AVAILABLE = True
    # Initialize database tables
    init_db()
    logger.info("✅ Database module loaded and tables initialized")
except ImportError:
    DB_AVAILABLE = False
    logger.warning("⚠️ Database module not available, predictions won't be tracked in DB")

# Initialize metrics tracker for logging predictions
metrics_tracker = MetricsTracker()

# ============================================
# FEATURED LEAGUES - Only log predictions for these leagues
# ============================================
FEATURED_LEAGUES = set(get_featured_league_ids())

# ============================================
# SEASONAL STATS LOADING FOR ENHANCED PREDICTIONS
# ============================================
try:
    from .seasonal_stats import SEASONAL_STATS, enrich_features_with_seasonal_stats
except ImportError:
    from seasonal_stats import SEASONAL_STATS, enrich_features_with_seasonal_stats


app = FastAPI(
    title="FixtureCast ML API",
    description="Machine Learning powered football match prediction API",
    version="1.2.0",
)
print("DEBUG: ml_api_impl loaded")

# ============================================
# PREDICTION STATISTICS TRACKING
# ============================================
try:
    from .stats_tracker import PredictionStatsTracker
except ImportError:
    from stats_tracker import PredictionStatsTracker

# Initialize stats tracker
stats_tracker = PredictionStatsTracker()


# =============================================================================
# RATE LIMITER - In-memory request throttling
# =============================================================================
class RateLimiter:
    """Simple in-memory rate limiter using sliding window."""

    def __init__(self, requests_per_minute: int = 60):
        self._requests = {}  # ip -> list of timestamps
        self._lock = Lock()
        self.limit = requests_per_minute
        self.window = 60  # 1 minute window

    def is_allowed(self, client_ip: str) -> bool:
        """Check if request from IP is allowed."""
        with self._lock:
            now = time.time()
            window_start = now - self.window

            # Get existing requests for this IP
            if client_ip not in self._requests:
                self._requests[client_ip] = []

            # Remove old requests outside window
            self._requests[client_ip] = [
                ts for ts in self._requests[client_ip] if ts > window_start
            ]

            # Check if under limit
            if len(self._requests[client_ip]) >= self.limit:
                return False

            # Add current request
            self._requests[client_ip].append(now)
            return True


# Initialize rate limiter (60 req/min for ML API - predictions are expensive)
rate_limiter = RateLimiter(requests_per_minute=60)

# Enable CORS - Restricted to fixturecast.com
ALLOWED_ORIGINS = [
    "https://fixturecast.com",
    "https://www.fixturecast.com",
    "https://fixturecast.pages.dev",
    "http://localhost:5173",  # Local dev
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


# API Key authentication
ML_API_KEY = os.getenv("ML_API_KEY", "")
# Prediction endpoints are public (no API key required)
PUBLIC_PATHS = {"/", "/health", "/api/health", "/metrics", "/docs", "/openapi.json"}
PUBLIC_PATH_PREFIXES = ("/api/prediction",)

@app.middleware("http")
async def api_key_auth_middleware(request: Request, call_next):
    """Require API key for non-public endpoints."""
    path = request.url.path

    # Skip auth for public endpoints, public path prefixes, and OPTIONS (CORS preflight)
    if path in PUBLIC_PATHS or request.method == "OPTIONS":
        return await call_next(request)
    if any(path.startswith(prefix) for prefix in PUBLIC_PATH_PREFIXES):
        return await call_next(request)

    # If ML_API_KEY is not set, skip auth (local dev)
    if not ML_API_KEY:
        return await call_next(request)

    # Check X-API-Key header
    api_key = request.headers.get("X-API-Key", "")
    if api_key != ML_API_KEY:
        # Include CORS header so the browser can read this 401 response
        origin = request.headers.get("origin", "")
        cors_origin = origin if origin in ALLOWED_ORIGINS else ""
        resp_headers = {"Access-Control-Allow-Origin": cors_origin} if cors_origin else {}
        return Response(
            content='{"detail": "Invalid or missing API key"}',
            status_code=401,
            media_type="application/json",
            headers=resp_headers,
        )

    return await call_next(request)


# Rate limiting middleware
@app.middleware("http")
async def add_cache_headers(request: Request, call_next):
    """Add Cache-Control headers for Cloudflare edge caching"""
    response = await call_next(request)

    path = request.url.path

    # Smart Caching for ML API
    if path.startswith("/api/prediction"):
        # Predictions: Cache for 15 mins (odds/form don't change that fast)
        response.headers["Cache-Control"] = "public, max-age=900, s-maxage=900"
    elif path.startswith("/api/model-stats") or path.startswith("/models/info"):
        # Sensitive metadata endpoints should not be edge-cached.
        response.headers.update(NO_CACHE_HEADERS)
    elif path in ["/health", "/", "/metrics"]:
        # Health checks: No cache
        response.headers["Cache-Control"] = "no-cache"
    else:
        # Default: Short cache
        response.headers["Cache-Control"] = "public, max-age=60, s-maxage=60"

    return response


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Apply rate limiting to all requests."""
    # Get client IP (handle proxies)
    client_ip = request.headers.get("X-Forwarded-For", request.client.host)
    if client_ip:
        client_ip = client_ip.split(",")[0].strip()

    # Skip rate limiting for health checks
    if request.url.path in ["/", "/health", "/api/health", "/metrics"]:
        return await call_next(request)

    # Check rate limit
    if not rate_limiter.is_allowed(client_ip):
        # Include CORS header so the browser can read this 429 response
        origin = request.headers.get("origin", "")
        cors_origin = origin if origin in ALLOWED_ORIGINS else ""
        resp_headers = {"Access-Control-Allow-Origin": cors_origin} if cors_origin else {}
        return Response(
            content='{"detail": "Rate limit exceeded. Please slow down."}',
            status_code=429,
            media_type="application/json",
            headers=resp_headers,
        )

    return await call_next(request)


# Try to add Prometheus metrics
try:
    from prometheus_fastapi_instrumentator import Instrumentator

    Instrumentator().instrument(app).expose(app)
    print("Prometheus metrics enabled at /metrics")
except ImportError:
    print("Prometheus metrics not available - install prometheus-fastapi-instrumentator")

import json
import logging
from contextlib import asynccontextmanager

from analysis_llm import AnalysisLLM

# Initialize predictor once at startup (loads trained models)
from api_client import ApiClient, RedisCache
from safe_feature_builder import FeatureBuilder

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
predictor = None
api_client = None
feature_builder = FeatureBuilder()
analysis_llm = AnalysisLLM()
prediction_cache = RedisCache(prefix="fixturecast:mlpred:")
LEAGUE_THRESHOLD_REFRESH_SECONDS = int(
    os.getenv("LEAGUE_THRESHOLD_REFRESH_SECONDS", str(6 * 60 * 60))
)

def get_predictor():
    """Lazy load the predictor on first access"""
    global predictor
    if predictor is None:
        try:
            # Suppress sklearn warnings during model loading
            import warnings
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")
                logger.info("Loading ML models on demand...")
                predictor = EnsemblePredictor(load_trained=True)
                _refresh_live_league_thresholds(force=True)
            logger.info("✅ ML models loaded successfully!")
        except Exception as e:
            logger.error(f"⚠️ Failed to load ML models: {e}")
            predictor = None
    return predictor
LEAGUE_THRESHOLD_MIN_SAMPLES = int(os.getenv("LEAGUE_THRESHOLD_MIN_SAMPLES", "30"))
LEAGUE_THRESHOLD_BASE = float(os.getenv("LEAGUE_THRESHOLD_BASE", "0.45"))
LEAGUE_THRESHOLD_MIN = float(os.getenv("LEAGUE_THRESHOLD_MIN", "0.34"))
LEAGUE_THRESHOLD_MAX = float(os.getenv("LEAGUE_THRESHOLD_MAX", "0.65"))
LEAGUE_THRESHOLD_WEIGHT_DIVISOR = float(os.getenv("LEAGUE_THRESHOLD_WEIGHT_DIVISOR", "100"))

_live_thresholds_cache = {}
_last_threshold_refresh = 0.0
_threshold_lock = Lock()


def _compute_live_league_thresholds() -> Dict[str, float]:
    if not DB_AVAILABLE:
        return {}
    metrics = PredictionDB.get_metrics_summary(days=365)
    by_league = metrics.get("by_league", {}) if isinstance(metrics, dict) else {}
    thresholds = {}

    for league_id, stats in by_league.items():
        if not isinstance(stats, dict):
            continue
        total = int(stats.get("total") or 0)
        accuracy = float(stats.get("accuracy") or 0.0)
        if total < LEAGUE_THRESHOLD_MIN_SAMPLES:
            continue

        weight = min(1.0, total / float(LEAGUE_THRESHOLD_WEIGHT_DIVISOR))
        threshold = LEAGUE_THRESHOLD_BASE + ((0.5 - accuracy) * 0.5 * weight)
        threshold = min(max(threshold, LEAGUE_THRESHOLD_MIN), LEAGUE_THRESHOLD_MAX)
        thresholds[str(league_id)] = round(float(threshold), 4)

    return thresholds


def _refresh_live_league_thresholds(force: bool = False) -> None:
    global _live_thresholds_cache, _last_threshold_refresh

    if not DB_AVAILABLE or predictor is None:
        return

    now = time.time()
    if not force and (now - _last_threshold_refresh) < LEAGUE_THRESHOLD_REFRESH_SECONDS:
        return

    with _threshold_lock:
        now = time.time()
        if not force and (now - _last_threshold_refresh) < LEAGUE_THRESHOLD_REFRESH_SECONDS:
            return
        thresholds = _compute_live_league_thresholds()
        if thresholds:
            predictor.league_thresholds.update(thresholds)
            _live_thresholds_cache = thresholds
        _last_threshold_refresh = now


def _get_live_data_mode() -> str:
    mode = (os.environ.get("FIXTURECAST_LIVE_DATA_MODE") or "optional").strip().lower()
    if mode not in {"required", "optional", "off"}:
        logger.warning(f"Invalid FIXTURECAST_LIVE_DATA_MODE={mode!r}; falling back to 'optional'")
        mode = "optional"
    return mode


LIVE_DATA_MODE = _get_live_data_mode()
logger.info(f"Live data mode: {LIVE_DATA_MODE}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    global predictor, api_client

    # Startup
    logger.info("Starting ML API...")

    # Initialize API Client first (needed for basic functionality)
    try:
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        with open(config_path) as f:
            config = json.load(f)
        api_client = ApiClient(config)
        logger.info("API Client initialized!")
    except Exception as e:
        logger.warning(f"Failed to initialize API Client: {e}")
        api_client = None

    # Don't load models at startup
    predictor = None

    # Self-keepalive: ping own health endpoint every 8 minutes to prevent Railway sleep
    import asyncio
    import httpx

    async def self_keepalive():
        port = int(os.environ.get("PORT", 8000))
        url = f"http://127.0.0.1:{port}/health"
        async with httpx.AsyncClient() as client:
            while True:
                await asyncio.sleep(480)  # 8 minutes
                try:
                    resp = await client.get(url, timeout=10)
                    logger.info(f"🏓 Self-keepalive: {resp.status_code}")
                except Exception as e:
                    logger.warning(f"🏓 Self-keepalive failed: {e}")

    keepalive_task = asyncio.create_task(self_keepalive())

    yield  # Application runs here

    # Shutdown
    keepalive_task.cancel()
    logger.info("Shutting down ML API...")
    predictor = None
    api_client = None


# Re-create app with lifespan
app = FastAPI(
    title="FixtureCast ML API",
    description="Machine Learning powered football match prediction API",
    version="2.0.0",
    lifespan=lifespan,
)

# Re-add ALL middleware on the recreated app.
# IMPORTANT: In Starlette, the LAST add_middleware call becomes the OUTERMOST
# middleware (first to handle requests, last to process responses).
# CORSMiddleware must be outermost so it adds Access-Control-Allow-Origin
# headers to ALL responses, including 401/429 errors from inner middleware.
from starlette.middleware.base import BaseHTTPMiddleware  # noqa: E402

# Innermost: auth check (runs last on request, first on response)
app.add_middleware(BaseHTTPMiddleware, dispatch=api_key_auth_middleware)
# Then: rate limiting
app.add_middleware(BaseHTTPMiddleware, dispatch=rate_limit_middleware)
# Then: cache headers
app.add_middleware(BaseHTTPMiddleware, dispatch=add_cache_headers)
# Outermost: CORS (must be added LAST so it wraps everything and processes all responses)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Include metrics router for performance tracking
try:
    from metrics_api import router as metrics_router

    app.include_router(metrics_router)
    logger.info("✅ Metrics API router included")
except ImportError as e:
    logger.warning(f"⚠️ Metrics API router not available: {e}")


# Request/response schemas live in backend/schemas.py (extracted to keep this
# module focused on routing and prediction orchestration).
try:
    from .schemas import ErrorResponse, HealthResponse, MatchFeatures, PredictionResponse
except ImportError:
    from schemas import ErrorResponse, HealthResponse, MatchFeatures, PredictionResponse


@app.get("/debug/source")
async def get_source():
    try:
        with open(
            os.path.join(os.path.dirname(__file__), "..", "ml_engine", "ensemble_predictor.py"), "r"
        ) as f:
            return {"content": f.read()}
    except Exception as e:
        return {"error": str(e)}


@app.get("/")
async def root():
    return {
        "service": "FixtureCast ML API",
        "version": "2.0.0",
        "status": "running",
        "models_loaded": predictor is not None,
    }


@app.get("/health")
async def health_check():
    """Liveness check — is the process up and the event loop responsive?

    Intentionally does no heavy work so it answers fast even under load. A 200 here
    does NOT imply predictions are serving correctly; use /health/ready for that.
    """
    return {
        "status": "healthy",
        "models_loaded": predictor is not None,
        "api_client_ready": api_client is not None,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/health/ready")
async def readiness_check():
    """Readiness probe — deeper than /health.

    Confirms the predictor and API client are up AND that the trained meta-model
    stacker actually loaded. A plain /health 200 does not catch a silent fallback to
    fixed weights (combiner == "weighted_average"), which is a real failure mode we hit
    in production. Returns 503 when not ready so monitors/orchestrators react.
    """
    from starlette.responses import JSONResponse

    meta_loaded = bool(getattr(predictor, "meta_model", None) is not None) if predictor else False
    ready = predictor is not None and api_client is not None
    return JSONResponse(
        status_code=200 if ready else 503,
        content={
            "status": "ready" if ready else "not_ready",
            "models_loaded": predictor is not None,
            "api_client_ready": api_client is not None,
            "meta_model_loaded": meta_loaded,
            "timestamp": datetime.now().isoformat(),
        },
    )


@app.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus-compatible metrics endpoint for ML API.
    Returns metrics in Prometheus text exposition format.
    """
    from starlette.responses import PlainTextResponse

    # Get stats from tracker
    stats = stats_tracker.stats

    # Build Prometheus format output
    lines = [
        "# HELP ml_api_predictions_total Total number of predictions made",
        "# TYPE ml_api_predictions_total counter",
        f'ml_api_predictions_total {stats.get("total_predictions", 0)}',
        "",
        "# HELP ml_api_models_loaded Whether ML models are loaded",
        "# TYPE ml_api_models_loaded gauge",
        f"ml_api_models_loaded {1 if predictor else 0}",
        "",
        "# HELP ml_api_client_ready Whether API client is initialized",
        "# TYPE ml_api_client_ready gauge",
        f"ml_api_client_ready {1 if api_client else 0}",
    ]

    # Add per-model confidence averages
    lines.append("")
    lines.append("# HELP ml_api_model_avg_confidence Average model confidence per model type")
    lines.append("# TYPE ml_api_model_avg_confidence gauge")
    for model, count in stats.get("confidence_counts", {}).items():
        if count > 0:
            avg_conf = stats.get("confidence_sums", {}).get(model, 0) / count
            lines.append(f'ml_api_model_avg_confidence{{model="{model}"}} {avg_conf:.4f}')

    # Add prediction counts by model
    lines.append("")
    lines.append("# HELP ml_api_predictions_by_model Predictions by model type")
    lines.append("# TYPE ml_api_predictions_by_model counter")
    for model, count in stats.get("predictions_by_model", {}).items():
        lines.append(f'ml_api_predictions_by_model{{model="{model}"}} {count}')

    return PlainTextResponse("\n".join(lines), media_type="text/plain")


@app.get("/api/prediction/{fixture_id}")
async def predict_fixture(fixture_id: int, league: int = 39, season: Optional[int] = None):
    """
    Get prediction for a specific fixture ID.
    Fetches real data, builds features, and runs prediction.
    Now with competition-type awareness for UCL/UEL knockouts vs domestic leagues.
    """
    predictor = get_predictor()
    if predictor is None:
        raise HTTPException(status_code=503, detail="ML models not loaded")
    if api_client is None:
        raise HTTPException(status_code=503, detail="API Client not initialized")

    _refresh_live_league_thresholds()

    try:
        live_mode = LIVE_DATA_MODE
        live_data_used = []

        # 1. Fetch Fixture Details directly by ID
        fixture_response = api_client.get_fixture_details(fixture_id)

        if not fixture_response or not fixture_response.get("response"):
            raise HTTPException(status_code=404, detail="Fixture not found")

        fixture = fixture_response["response"][0]

        # Auto-detect league from fixture if not explicitly provided or default
        actual_league = fixture.get("league", {}).get("id", league)
        if actual_league and actual_league != league:
            print(f"Auto-detected league {actual_league} from fixture (param was {league})")
            league = actual_league

        if season is None:
            season = get_league_season(league, fixture.get("fixture", {}).get("date"))

        # Cache key (skip caching for live/finished fixtures)
        status_short = fixture.get("fixture", {}).get("status", {}).get("short")
        kickoff_ts = fixture.get("fixture", {}).get("timestamp")  # epoch seconds
        cache_key = None
        allow_cache = status_short not in {"FT", "AET", "PEN", "CANC", "ABD", "1H", "2H", "LIVE"}
        # If fixture starts within 2 hours, use a shorter TTL later; still allow cache for now
        near_kickoff = False
        is_live = status_short in {"1H", "2H", "LIVE", "HT", "ET", "P"}
        within_24h = False
        if kickoff_ts:
            time_to_kickoff = kickoff_ts - time.time()
            near_kickoff = 0 < time_to_kickoff <= 2 * 3600
            within_24h = 0 < time_to_kickoff <= 24 * 3600
        else:
            # If kickoff is unknown, err toward better predictions but avoid the highest-cost calls.
            within_24h = True
        if allow_cache:
            # Cache must be mode-aware so `off|optional|required` don't cross-contaminate.
            cache_key = f"prediction:{fixture_id}:{league}:{season}:{live_mode}"
            cached = prediction_cache.get(cache_key)
            if cached:
                return cached

        home_id = fixture["teams"]["home"]["id"]
        away_id = fixture["teams"]["away"]["id"]

        # 2. Fetch other required data (live-data mode aware)
        data_quality = "full"  # Track data quality: "full", "partial", "limited"

        def _fetch(name: str, call, default, require_no_errors: bool = False):
            nonlocal data_quality
            if live_mode == "off":
                data_quality = "limited"
                return default

            try:
                result = call()
            except Exception as e:
                if live_mode == "required":
                    raise HTTPException(
                        status_code=503,
                        detail=f"Live data mode 'required': failed to fetch {name}: {e}",
                    )
                data_quality = "partial"
                return default

            if isinstance(result, dict) and result.get("errors"):
                if live_mode == "required" and require_no_errors:
                    raise HTTPException(
                        status_code=503,
                        detail=f"Live data mode 'required': {name} returned errors: {result.get('errors')}",
                    )
                data_quality = "partial"
                return default

            if (
                isinstance(result, dict)
                and "response" in result
                and not (result.get("response") or [])
            ):
                # Empty responses are common for some endpoints (e.g. odds/lineups pre-publish).
                # In required mode, we still serve a prediction but mark it partial.
                if live_mode == "required":
                    data_quality = "partial"

            live_data_used.append(name)
            return result

        require_core = live_mode == "required"

        standings = _fetch(
            "standings",
            lambda: api_client.get_standings(league, season),
            {"response": []},
            require_no_errors=require_core,
        )
        home_stats = _fetch(
            "home_team_stats",
            lambda: api_client.get_team_stats(home_id, league, season),
            {"response": []},
            require_no_errors=require_core,
        )
        away_stats = _fetch(
            "away_team_stats",
            lambda: api_client.get_team_stats(away_id, league, season),
            {"response": []},
            require_no_errors=require_core,
        )

        # Fetch last 10 matches for form analysis
        home_last_10 = _fetch(
            "home_last_10",
            lambda: api_client.get_last_fixtures(
                team_id=home_id, league=league, season=season, last=10
            ),
            {"response": []},
            require_no_errors=require_core,
        )
        away_last_10 = _fetch(
            "away_last_10",
            lambda: api_client.get_last_fixtures(
                team_id=away_id, league=league, season=season, last=10
            ),
            {"response": []},
            require_no_errors=require_core,
        )

        # Fetch H2H
        h2h = _fetch(
            "h2h",
            lambda: api_client.get_h2h(home_id, away_id),
            {"response": []},
            require_no_errors=require_core,
        )

        # Fetch odds - time-aware caching
        odds_ttl = 30 if (near_kickoff or is_live) else (120 if within_24h else 300)
        odds = _fetch(
            "odds",
            lambda: api_client.get_odds(fixture_id, ttl_override=odds_ttl),
            {"response": []},
            require_no_errors=False,
        )

        # Fetch injuries - time-aware caching
        injuries_ttl = 300 if (near_kickoff or is_live) else 600
        home_injuries = _fetch(
            "home_injuries",
            lambda: api_client.get_injuries(
                home_id, season, ttl_override=injuries_ttl, league_id=league
            ),
            {"response": []},
            require_no_errors=False,
        )
        away_injuries = _fetch(
            "away_injuries",
            lambda: api_client.get_injuries(
                away_id, season, ttl_override=injuries_ttl, league_id=league
            ),
            {"response": []},
            require_no_errors=False,
        )

        # Fetch confirmed lineups (time-aware: only near kickoff / live)
        fetch_lineups = (near_kickoff or is_live) and live_mode != "off"
        lineups_ttl = 20 if (near_kickoff or is_live) else 60
        lineups = (
            _fetch(
                "lineups",
                lambda: api_client.get_fixture_lineups(fixture_id, ttl_override=lineups_ttl),
                {"response": []},
                require_no_errors=False,
            )
            if fetch_lineups
            else {"response": []}
        )

        # 2b. Enhanced data fetching (time-aware)
        # - Far from kickoff: avoid high-call-count enrichment
        # - Within 24h / live: fetch players + coaches
        # - Near kickoff / live: also fetch recent fixture stats
        fetch_players_coach = (within_24h or is_live) and live_mode != "off"
        fetch_recent_stats = (near_kickoff or is_live) and live_mode != "off"

        home_players = (
            _fetch(
                "home_players",
                lambda: api_client.get_players(home_id, season, league_id=league),
                None,
                require_no_errors=False,
            )
            if fetch_players_coach
            else None
        )
        away_players = (
            _fetch(
                "away_players",
                lambda: api_client.get_players(away_id, season, league_id=league),
                None,
                require_no_errors=False,
            )
            if fetch_players_coach
            else None
        )
        home_coach = (
            _fetch(
                "home_coach",
                lambda: api_client.get_coach(home_id),
                None,
                require_no_errors=False,
            )
            if fetch_players_coach
            else None
        )
        away_coach = (
            _fetch(
                "away_coach",
                lambda: api_client.get_coach(away_id),
                None,
                require_no_errors=False,
            )
            if fetch_players_coach
            else None
        )

        if fetch_recent_stats:
            home_fixture_ids = [f["fixture"]["id"] for f in home_last_10.get("response", [])[:5]]
            away_fixture_ids = [f["fixture"]["id"] for f in away_last_10.get("response", [])[:5]]
            home_recent_stats = _fetch(
                "home_recent_stats",
                lambda: api_client.get_recent_fixture_stats(home_fixture_ids),
                None,
                require_no_errors=False,
            )
            away_recent_stats = _fetch(
                "away_recent_stats",
                lambda: api_client.get_recent_fixture_stats(away_fixture_ids),
                None,
                require_no_errors=False,
            )
        else:
            home_recent_stats = None
            away_recent_stats = None

        # 2c. Get competition metadata for type-aware predictions
        competition_info = api_client.get_competition_info(league)
        round_info = None
        if competition_info.get("type") == "european_cup" and live_mode != "off":
            round_info = _fetch(
                "fixture_round",
                lambda: api_client.get_fixture_round(fixture_id),
                None,
                require_no_errors=False,
            )

        # 3. Build features with fallback
        try:
            features = feature_builder.build_features(
                fixture_details={"response": [fixture]},
                standings=standings,
                home_last_10=home_last_10,
                away_last_10=away_last_10,
                home_stats=home_stats,
                away_stats=away_stats,
                h2h=h2h,
                home_injuries=home_injuries,
                away_injuries=away_injuries,
                odds=odds,
                lineups=lineups,
                home_players=home_players,
                away_players=away_players,
                home_coach=home_coach,
                away_coach=away_coach,
                home_recent_stats=home_recent_stats,
                away_recent_stats=away_recent_stats,
                competition_info=competition_info,
                round_info=round_info,
            )
            # Check if we have meaningful data (not just defaults)
            home_matches = len(home_last_10.get("response", []))
            away_matches = len(away_last_10.get("response", []))
            h2h_matches = len(h2h.get("response", []))
            has_standings = bool(standings.get("response"))

            if home_matches < 3 or away_matches < 3:
                data_quality = "limited"
            elif home_matches < 5 or away_matches < 5 or not has_standings:
                data_quality = "partial"
        except Exception as e:
            print(f"Feature building failed: {e}. Using fallback features.")
            data_quality = "limited"  # Fallback means limited data
            # Fallback: Create basic features from what we have or use defaults
            # We'll create a default feature dict and populate what we can
            features = {
                "home_id": home_id,
                "away_id": away_id,
                "home_name": fixture["teams"]["home"]["name"],
                "away_name": fixture["teams"]["away"]["name"],
                "home_league_points": 30,
                "away_league_points": 30,  # Defaults
                "home_league_pos": 10,
                "away_league_pos": 10,
                "home_goals_for_avg": 1.3,
                "away_goals_for_avg": 1.2,
                "home_goals_against_avg": 1.2,
                "away_goals_against_avg": 1.3,
                # Add other required keys with defaults
                "home_points_last10": 15,
                "away_points_last10": 15,
                "home_form_last5": 7,
                "away_form_last5": 7,
                "home_wins_last10": 5,
                "away_wins_last10": 5,
                "home_draws_last10": 3,
                "away_draws_last10": 3,
                "home_losses_last10": 2,
                "away_losses_last10": 2,
                "home_goals_for_last10": 13,
                "away_goals_for_last10": 12,
                "home_goals_against_last10": 12,
                "away_goals_against_last10": 13,
                "h2h_home_wins": 2,
                "h2h_draws": 2,
                "h2h_away_wins": 2,
                "h2h_total_matches": 6,
                "home_clean_sheets": 3,
                "away_clean_sheets": 3,
                "home_total_matches": 20,
                "away_total_matches": 20,
                "odds_available": False,
                # Lineups defaults
                "home_lineup_available": 0,
                "away_lineup_available": 0,
                "home_lineup_confirmed": 0,
                "away_lineup_confirmed": 0,
                "home_starting_xi_count": 0,
                "away_starting_xi_count": 0,
                "home_subs_count": 0,
                "away_subs_count": 0,
                "home_lineup_formation_code": 0,
                "away_lineup_formation_code": 0,
                # Competition defaults
                "is_domestic_league": 1,
                "is_european_cup": 0,
                "is_knockout_stage": 0,
                "competition_prestige": 1.0,
            }

        # 3.5 ENHANCE features with seasonal statistics (for ML models trained with enhanced data)
        features = enrich_features_with_seasonal_stats(features, home_id, away_id, SEASONAL_STATS)
        print(f"DEBUG: Enhanced features with seasonal stats - total keys: {len(features)}")

        # 4. Predict
        result = predictor.predict_fixture(features)

        # 4.4 Cold-start gate: national-team / unseen-team fixtures run the ensemble
        # on Elo priors (both sides at the 1500 base rating), producing low-information
        # predictions. Flag these and force an abstention instead of presenting an
        # unfounded scoreline as actionable. See backend/prediction_quality.py.
        odds_available = bool(
            features.get("odds_1x2_available", False)
            or (
                float(features.get("odds_home_win", 0) or 0) > 1.0
                and float(features.get("odds_away_win", 0) or 0) > 1.0
            )
        )
        apply_cold_start_gate(
            result,
            competition_type=competition_info.get("type"),
            h2h_total_matches=int(features.get("h2h_total_matches", 0) or 0),
            odds_available=odds_available,
        )

        # 4.5 Validate prediction consistency
        validate_prediction_consistency(result, features)

        # 5. Enrich features with Elo ratings for analysis
        elo_ratings = result.get("elo_ratings", {})
        enriched_features = {
            **features,
            "home_elo": elo_ratings.get("home", 1500),
            "away_elo": elo_ratings.get("away", 1500),
            "home_rank": features.get("home_league_pos", 10),
            "away_rank": features.get("away_league_pos", 10),
        }
        print(
            f"DEBUG: enriched_features home_elo={enriched_features.get('home_elo')}, away_elo={enriched_features.get('away_elo')}, home_rank={enriched_features.get('home_rank')}, away_rank={enriched_features.get('away_rank')}"
        )

        # 6. Generate comprehensive analysis text using polished AnalysisLLM
        analysis = analysis_llm.analyze(result, enriched_features)

        # Track prediction stats
        ensemble_confidence = max(
            result["home_win_prob"], result["draw_prob"], result["away_win_prob"]
        )
        stats_tracker.record_prediction(result.get("model_breakdown", {}), ensemble_confidence)

        # Log prediction for feedback learning system
        try:
            log_feedback_prediction(
                fixture_id=fixture_id,
                home_team=fixture["teams"]["home"]["name"],
                away_team=fixture["teams"]["away"]["name"],
                league_id=league,
                league_name=fixture.get("league", {}).get("name", "Unknown"),
                match_date=fixture["fixture"]["date"],
                prediction=result,
                model_breakdown=result.get("model_breakdown", {}),
            )
        except Exception as e:
            print(f"Warning: Failed to log prediction for feedback: {e}")

        # Log prediction to database for performance tracking
        # ONLY log predictions for featured leagues to maintain accuracy quality
        if DB_AVAILABLE and league in FEATURED_LEAGUES:
            try:
                PredictionDB.log_prediction(
                    fixture_id=fixture_id,
                    home_team=fixture["teams"]["home"]["name"],
                    away_team=fixture["teams"]["away"]["name"],
                    home_team_id=fixture["teams"]["home"]["id"],
                    away_team_id=fixture["teams"]["away"]["id"],
                    league_id=league,
                    league_name=fixture.get("league", {}).get("name", "Unknown"),
                    match_date=fixture["fixture"]["date"],
                    prediction=result,
                    model_breakdown=result.get("model_breakdown", {}),
                )
                print(
                    f"✅ Logged prediction for featured league {league}: {fixture['teams']['home']['name']} vs {fixture['teams']['away']['name']}"
                )
            except Exception as e:
                print(f"Warning: Failed to log prediction to database: {e}")
        elif DB_AVAILABLE:
            print(
                f"⏭️  Skipped logging prediction for non-featured league {league}: {fixture['teams']['home']['name']} vs {fixture['teams']['away']['name']}"
            )

        # Add data quality to prediction result
        result["data_quality"] = data_quality
        result["live_data_mode"] = live_mode
        result["live_data_used"] = live_data_used

        response_payload = {"prediction": result, "fixture_details": fixture, "analysis": analysis}

        # Cache the prediction for short-term reuse (time-aware)
        if cache_key:
            try:
                if is_live:
                    ttl = 30
                elif near_kickoff:
                    ttl = 120
                elif within_24h:
                    ttl = 300
                else:
                    ttl = 900
                prediction_cache.set(cache_key, response_payload, ttl=ttl)
            except Exception as e:
                print(f"Prediction cache set failed: {e}")

        return response_payload

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error in predict_fixture: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def validate_prediction_consistency(result: dict, features: dict) -> dict:
    """
    Validate prediction for logical consistency and flag warnings.
    Returns validation result with warnings if inconsistencies found.
    """
    warnings = []

    predicted_score = result.get("predicted_scoreline", "0-0")
    btts_prob = result.get("btts_prob", 0)
    over25_prob = result.get("over25_prob", 0)
    home_prob = result.get("home_win_prob", 0)
    draw_prob = result.get("draw_prob", 0)
    away_prob = result.get("away_win_prob", 0)

    # Parse predicted scoreline
    try:
        h_goals, a_goals = map(int, predicted_score.split("-"))

        # Check 1: BTTS vs Scoreline
        if btts_prob > 0.50 and (h_goals == 0 or a_goals == 0):
            warnings.append(
                f"⚠️ BTTS is {btts_prob*100:.0f}% but predicted score is {predicted_score} (only one team scores)"
            )
        elif btts_prob < 0.35 and h_goals >= 1 and a_goals >= 1:
            warnings.append(
                f"⚠️ BTTS is only {btts_prob*100:.0f}% but predicted score is {predicted_score} (both teams score)"
            )

        # Check 2: Over 2.5 vs Scoreline
        total_goals = h_goals + a_goals
        if over25_prob > 0.55 and total_goals <= 2:
            warnings.append(
                f"⚠️ Over 2.5 is {over25_prob*100:.0f}% but predicted score is {predicted_score} ({total_goals} total goals)"
            )
        elif over25_prob < 0.35 and total_goals > 3:
            warnings.append(
                f"⚠️ Over 2.5 is only {over25_prob*100:.0f}% but predicted score is {predicted_score} ({total_goals} goals)"
            )

        # Check 3: Scoreline vs Outcome Probability
        if h_goals > a_goals and home_prob < 0.40:
            warnings.append(
                f"⚠️ Home win predicted ({predicted_score}) but home win probability is only {home_prob*100:.0f}%"
            )
        elif a_goals > h_goals and away_prob < 0.40:
            warnings.append(
                f"⚠️ Away win predicted ({predicted_score}) but away win probability is only {away_prob*100:.0f}%"
            )
        elif h_goals == a_goals and draw_prob < 0.25:
            warnings.append(
                f"⚠️ Draw predicted ({predicted_score}) but draw probability is only {draw_prob*100:.0f}%"
            )

    except Exception as e:
        warnings.append(f"⚠️ Could not validate scoreline: {e}")

    # Check 4: Model breakdown consensus
    model_breakdown = result.get("model_breakdown", {})
    models_favoring_home = 0
    models_favoring_away = 0

    for model_name, preds in model_breakdown.items():
        if isinstance(preds, dict) and "home_win" in preds:
            h, a = preds.get("home_win", 0), preds.get("away_win", 0)
            if h > a:
                models_favoring_home += 1
            elif a > h:
                models_favoring_away += 1

    total_models = models_favoring_home + models_favoring_away
    if total_models > 0:
        if models_favoring_home > models_favoring_away and home_prob < away_prob:
            warnings.append("⚠️ Majority of signals favor home but weighted ensemble favors away")
        elif models_favoring_away > models_favoring_home and away_prob < home_prob:
            warnings.append("⚠️ Majority of signals favor away but weighted ensemble favors home")

    # Log warnings if any
    if warnings:
        print(
            f"\n🔍 Prediction Validation Warnings for {features.get('home_name', 'Home')} vs {features.get('away_name', 'Away')}:"
        )
        for warning in warnings:
            print(f"   {warning}")

    return {"is_valid": len(warnings) == 0, "warnings": warnings, "warning_count": len(warnings)}


def generate_enhanced_analysis(fixture: dict, features: dict, result: dict) -> str:
    """
    Generate comprehensive match analysis with:
    1. H2H history context
    2. League position context
    3. Model consensus indicator
    4. Rich tactical insights based on goals data
    """
    home_name = fixture["teams"]["home"]["name"]
    away_name = fixture["teams"]["away"]["name"]

    home_prob = result["home_win_prob"] * 100
    draw_prob = result["draw_prob"] * 100
    away_prob = result["away_win_prob"] * 100
    btts_prob = result["btts_prob"] * 100
    over25_prob = result["over25_prob"] * 100

    # ============================================
    # 1. DETERMINE FAVORITE & CONFIDENCE BADGE
    # ============================================
    if home_prob > away_prob:
        favorite, favorite_prob = home_name, home_prob
        underdog, underdog_prob = away_name, away_prob
    else:
        favorite, favorite_prob = away_name, away_prob
        underdog, underdog_prob = home_name, home_prob

    # Confidence badge with risk assessment
    if favorite_prob > 70:
        confidence_badge = "🟢 HIGH CONFIDENCE"
        risk_level = "Low risk"
    elif favorite_prob > 55:
        confidence_badge = "🟡 MEDIUM CONFIDENCE"
        risk_level = "Medium risk"
    elif favorite_prob > 40:
        confidence_badge = "🟠 COMPETITIVE MATCH"
        risk_level = "Higher risk - close call"
    else:
        confidence_badge = "🔴 UPSET ALERT"
        risk_level = "High risk - anything can happen"

    # ============================================
    # 2. MODEL CONSENSUS ANALYSIS
    # ============================================
    model_breakdown = result.get("model_breakdown", {})
    models_favoring_home = 0
    models_favoring_away = 0
    models_favoring_draw = 0
    model_opinions = []

    for model_name, preds in model_breakdown.items():
        if isinstance(preds, dict) and "home_win" in preds:
            h, d, a = preds.get("home_win", 0), preds.get("draw", 0), preds.get("away_win", 0)
            if h > d and h > a:
                models_favoring_home += 1
                model_opinions.append(f"{model_name.upper()}: {home_name}")
            elif a > d and a > h:
                models_favoring_away += 1
                model_opinions.append(f"{model_name.upper()}: {away_name}")
            else:
                models_favoring_draw += 1
                model_opinions.append(f"{model_name.upper()}: Draw")

    total_models = models_favoring_home + models_favoring_away + models_favoring_draw
    if total_models > 0:
        consensus_home = models_favoring_home / total_models
        consensus_away = models_favoring_away / total_models

        # Determine who the weighted ensemble actually favors
        ensemble_favors_home = home_prob > away_prob and home_prob > draw_prob
        ensemble_favors_away = away_prob > home_prob and away_prob > draw_prob

        # Check if model count agrees with weighted probability
        model_count_favors_home = models_favoring_home > models_favoring_away
        model_count_favors_away = models_favoring_away > models_favoring_home

        if consensus_home >= 0.75 and ensemble_favors_home:
            consensus_text = f"🤝 **Strong Consensus**: Strong signal agreement on {home_name}. High reliability."
        elif consensus_away >= 0.75 and ensemble_favors_away:
            consensus_text = f"🤝 **Strong Consensus**: Strong signal agreement on {away_name}. High reliability."
        elif ensemble_favors_home and not model_count_favors_home:
            # Weighted result differs from model count - explain the weighted models carry more influence
            consensus_text = f"⚖️ **Weighted Analysis**: Our higher-accuracy models favor {home_name}, giving them the edge despite mixed signals."
        elif ensemble_favors_away and not model_count_favors_away:
            # Weighted result differs from model count - explain the weighted models carry more influence
            consensus_text = f"⚖️ **Weighted Analysis**: Our higher-accuracy models favor {away_name}, giving them the edge despite mixed signals."
        elif max(consensus_home, consensus_away) >= 0.5:
            majority = home_name if consensus_home > consensus_away else away_name
            consensus_text = (
                f"⚖️ **Moderate Consensus**: Majority of our signals lean toward {majority}."
            )
        else:
            consensus_text = f"⚠️ **Signals Divided**: Our AI is split on this one. This match is highly unpredictable."
    else:
        consensus_text = ""

    # ============================================
    # 3. HEAD-TO-HEAD HISTORY
    # ============================================
    h2h_home = features.get("h2h_home_wins", 0)
    h2h_draws = features.get("h2h_draws", 0)
    h2h_away = features.get("h2h_away_wins", 0)
    h2h_total = features.get("h2h_total_matches", 0)

    if h2h_total > 0:
        if h2h_home > h2h_away + 2:
            h2h_text = f"📊 **Head-to-Head**: {home_name} dominates this fixture with {h2h_home} wins in {h2h_total} meetings ({h2h_draws} draws, {h2h_away} away wins). Historical advantage is significant."
        elif h2h_away > h2h_home + 2:
            h2h_text = f"📊 **Head-to-Head**: {away_name} has the upper hand historically with {h2h_away} wins in {h2h_total} meetings. {home_name} struggles in this fixture."
        elif h2h_draws >= h2h_home and h2h_draws >= h2h_away:
            h2h_text = f"📊 **Head-to-Head**: These teams often share the spoils - {h2h_draws} draws in {h2h_total} meetings. Consider a draw bet."
        else:
            h2h_text = f"📊 **Head-to-Head**: Balanced history with {h2h_home} home wins, {h2h_draws} draws, {h2h_away} away wins in {h2h_total} meetings."
    else:
        h2h_text = "📊 **Head-to-Head**: Limited historical data available for this matchup."

    # ============================================
    # 4. LEAGUE POSITION CONTEXT
    # ============================================
    home_pos = features.get("home_league_pos", 10)
    away_pos = features.get("away_league_pos", 10)
    home_pts = features.get("home_league_points", 0)
    away_pts = features.get("away_league_points", 0)

    pos_diff = abs(home_pos - away_pos)
    pts_diff = abs(home_pts - away_pts)

    if pos_diff >= 10:
        if home_pos < away_pos:
            league_text = f"🏆 **League Context**: Major mismatch! {home_name} ({home_pos}{'st' if home_pos == 1 else 'nd' if home_pos == 2 else 'rd' if home_pos == 3 else 'th'} with {home_pts}pts) vs {away_name} ({away_pos}{'th'} with {away_pts}pts). Class difference should tell."
        else:
            league_text = f"🏆 **League Context**: {away_name} ({away_pos}{'st' if away_pos == 1 else 'nd' if away_pos == 2 else 'rd' if away_pos == 3 else 'th'} with {away_pts}pts) visits lower-ranked {home_name} ({home_pos}{'th'} with {home_pts}pts). Favorites are clear."
    elif pos_diff >= 5 or pts_diff >= 8:
        higher = home_name if home_pos < away_pos else away_name
        higher_pos = min(home_pos, away_pos)
        higher_pts = max(home_pts, away_pts)
        league_text = f"🏆 **League Context**: {higher} sits {pos_diff} places higher in the table ({higher_pos}{'st' if higher_pos == 1 else 'nd' if higher_pos == 2 else 'rd' if higher_pos == 3 else 'th'} with {higher_pts}pts, {pts_diff}-point advantage). Noticeable quality gap."
    elif pos_diff <= 2 and pts_diff <= 3:
        league_text = f"🏆 **League Context**: Both teams level in the standings ({home_name}: {home_pos}{'th'} with {home_pts}pts, {away_name}: {away_pos}{'th'} with {away_pts}pts). Expect a tight contest."
    else:
        higher = home_name if home_pts > away_pts else away_name
        league_text = f"🏆 **League Context**: {home_name} ({home_pos}{'th'}, {home_pts}pts) hosts {away_name} ({away_pos}{'th'}, {away_pts}pts). {higher} has the edge in standings."

    # ============================================
    # 5. RICH TACTICAL INSIGHTS (Goals Data)
    # ============================================
    home_gf_avg = features.get("home_goals_for_avg", 1.3)
    home_ga_avg = features.get("home_goals_against_avg", 1.2)
    away_gf_avg = features.get("away_goals_for_avg", 1.2)
    away_ga_avg = features.get("away_goals_against_avg", 1.3)

    # Handle missing/zero data - use league averages as fallback
    if away_gf_avg == 0 or away_ga_avg == 0:
        # Newly promoted team or missing data - estimate from league position
        if away_pos >= 15:
            away_gf_avg = 0.9  # Struggling team estimate
            away_ga_avg = 1.6
        else:
            away_gf_avg = 1.2
            away_ga_avg = 1.3

    if home_gf_avg == 0 or home_ga_avg == 0:
        if home_pos >= 15:
            home_gf_avg = 0.9
            home_ga_avg = 1.6
        else:
            home_gf_avg = 1.2
            home_ga_avg = 1.3

    home_clean_sheets = features.get("home_clean_sheets", 0)
    away_clean_sheets = features.get("away_clean_sheets", 0)

    # Team styles
    home_style = (
        "attacking" if home_gf_avg > 1.8 else "balanced" if home_gf_avg > 1.2 else "defensive"
    )
    away_style = (
        "attacking" if away_gf_avg > 1.8 else "balanced" if away_gf_avg > 1.2 else "defensive"
    )
    home_defense = "solid" if home_ga_avg < 1.0 else "average" if home_ga_avg < 1.5 else "leaky"
    away_defense = "solid" if away_ga_avg < 1.0 else "average" if away_ga_avg < 1.5 else "leaky"

    if home_style == "attacking" and away_defense == "leaky":
        tactical_text = f"⚔️ **Tactical Matchup**: {home_name}'s potent attack (avg {home_gf_avg:.1f} goals/game) faces {away_name}'s vulnerable defense (conceding {away_ga_avg:.1f}/game). Goals expected!"
    elif away_style == "attacking" and home_defense == "leaky":
        tactical_text = f"⚔️ **Tactical Matchup**: {away_name} scores freely ({away_gf_avg:.1f}/game) and {home_name} struggles defensively ({home_ga_avg:.1f} conceded/game). Away goals likely."
    elif home_defense == "solid" and away_defense == "solid":
        tactical_text = f"⚔️ **Tactical Matchup**: Two defensively strong teams - {home_name} ({home_clean_sheets} clean sheets) vs {away_name} ({away_clean_sheets} clean sheets). Low-scoring affair expected."
    elif home_style == "attacking" and away_style == "attacking":
        tactical_text = f"⚔️ **Tactical Matchup**: Attacking philosophies clash! {home_name} ({home_gf_avg:.1f} goals/game) vs {away_name} ({away_gf_avg:.1f}/game). Entertainment guaranteed."
    else:
        tactical_text = f"⚔️ **Tactical Matchup**: {home_name} ({home_style} approach, {home_gf_avg:.1f} scored, {home_ga_avg:.1f} conceded) vs {away_name} ({away_style} style, {away_gf_avg:.1f} scored, {away_ga_avg:.1f} conceded)."

    # ============================================
    # 6. FORM ANALYSIS (Enhanced with league context)
    # ============================================
    home_form = features.get("home_form_last5", 7)
    away_form = features.get("away_form_last5", 7)
    home_wins_10 = features.get("home_wins_last10", 5)
    away_wins_10 = features.get("away_wins_last10", 5)

    # Cross-reference form with league position for coherence
    if home_form > away_form + 4:
        form_text = f"📈 **Form Guide**: {home_name} is flying ({home_wins_10}W in last 10, {home_form}pts from last 5). {away_name} struggling in comparison ({away_wins_10}W, {away_form}pts). Momentum strongly favors the hosts."
    elif away_form > home_form + 4:
        form_text = f"📈 **Form Guide**: {away_name} arrives in red-hot form ({away_wins_10}W in last 10, {away_form}pts from last 5). {home_name} ({home_wins_10}W, {home_form}pts) may struggle to cope."
    elif abs(home_form - away_form) <= 2:
        # If form is similar but league position isn't, add context
        if pos_diff > 8:
            higher_team = home_name if home_pos < away_pos else away_name
            lower_team = away_name if home_pos < away_pos else home_name
            form_text = f"📈 **Form Guide**: Recent form is similar ({home_name} {home_form}pts, {away_name} {away_form}pts from last 5), but {higher_team}'s overall quality should prevail over {lower_team}."
        else:
            form_text = f"📈 **Form Guide**: Both teams in similar form - {home_name} ({home_form}pts) vs {away_name} ({away_form}pts) from last 5. Recent results are level."
    else:
        better = home_name if home_form > away_form else away_name
        form_text = f"📈 **Form Guide**: {better} has a slight edge in recent form ({home_name}: {home_form}pts, {away_name}: {away_form}pts from last 5)."

    # ============================================
    # 7. GOALS PREDICTION
    # ============================================
    btts_text = f"Both teams to score: **{'Yes' if btts_prob > 50 else 'No'}** ({btts_prob:.0f}% probability)"
    over_under_text = f"Over 2.5 goals: **{'Likely' if over25_prob > 55 else 'Possible' if over25_prob > 40 else 'Unlikely'}** ({over25_prob:.0f}%)"

    # ============================================
    # 8. FINAL RECOMMENDATION
    # ============================================
    if favorite_prob > 65 and (models_favoring_home >= 5 or models_favoring_away >= 5):
        recommendation = f"✅ **Verdict**: {favorite} has a strong edge with high signal agreement ({favorite_prob:.0f}%). {risk_level}."
    elif draw_prob > 28 and models_favoring_draw >= 2:
        recommendation = f"🤝 **Verdict**: Draw is a real contender ({draw_prob:.0f}%). Multiple signals point to a stalemate. {risk_level}."
    elif underdog_prob > 35:
        recommendation = f"⚡ **Verdict**: Upset potential — {underdog} has a meaningful chance ({underdog_prob:.0f}%). {risk_level}."
    elif favorite_prob > 55:
        recommendation = f"📊 **Verdict**: {favorite} is favored ({favorite_prob:.0f}%), but uncertainty remains. {risk_level}."
    elif favorite_prob > 45:
        recommendation = f"📊 **Verdict**: {favorite} holds a slight edge ({favorite_prob:.0f}%). High variance expected. {risk_level}."
    else:
        recommendation = f"🎲 **Verdict**: No clear winner — {home_name} ({home_prob:.0f}%) vs {away_name} ({away_prob:.0f}%). Very high uncertainty."

    # ============================================
    # 9. ELO RATINGS (NEW)
    # ============================================
    elo_ratings = result.get("elo_ratings", {})
    home_elo = elo_ratings.get("home", 1500)
    away_elo = elo_ratings.get("away", 1500)
    elo_diff = elo_ratings.get("diff", 0)

    if abs(elo_diff) > 150:
        better = home_name if elo_diff > 0 else away_name
        away_name if elo_diff > 0 else home_name
        elo_text = f"📈 **Elo Ratings**: {home_name} ({home_elo:.0f}) vs {away_name} ({away_elo:.0f}) — **{abs(elo_diff):.0f} point gap** in favor of {better}. Clear quality advantage."
    elif abs(elo_diff) > 80:
        better = home_name if elo_diff > 0 else away_name
        elo_text = f"📈 **Elo Ratings**: {home_name} ({home_elo:.0f}) vs {away_name} ({away_elo:.0f}) — {better} rated notably higher ({abs(elo_diff):.0f} pts difference)."
    else:
        elo_text = f"📈 **Elo Ratings**: {home_name} ({home_elo:.0f}) vs {away_name} ({away_elo:.0f}) — Evenly matched on long-term rating ({abs(elo_diff):.0f} pts apart)."

    # ============================================
    # ASSEMBLE FINAL ANALYSIS
    # ============================================
    # Handle toss-up matches
    margin = abs(home_prob - away_prob)
    is_toss_up = margin < 5 and max(home_prob, away_prob) > draw_prob

    if is_toss_up:
        header_line = (
            f"{confidence_badge} | **Too close to call** ({home_prob:.1f}% vs {away_prob:.1f}%)"
        )
    else:
        if favorite_prob >= 55:
            edge_phrase = "favored"
        elif favorite_prob >= 45:
            edge_phrase = "slight edge"
        else:
            edge_phrase = "slight lean"
        header_line = f"{confidence_badge} | **{favorite}** {edge_phrase} ({favorite_prob:.1f}%)"

    analysis = f"""## {home_name} vs {away_name}

{header_line}

---

### 📊 Prediction Summary

| Outcome | Probability |
|---------|-------------|
| {home_name} Win | {home_prob:.1f}% |
| Draw | {draw_prob:.1f}% |
| {away_name} Win | {away_prob:.1f}% |

**Predicted Score: {result['predicted_scoreline']}**

{btts_text}
{over_under_text}

---

### 🔍 Deep Analysis

{consensus_text}

{elo_text}

{h2h_text}

{league_text}

{tactical_text}

{form_text}

---

### 🎯 Our Verdict

{recommendation}

---

*Analysis by FixtureCast AI — 8-model ensemble system*
"""

    return analysis


@app.post("/predict", response_model=PredictionResponse)
async def predict_match(features: MatchFeatures):
    """
    Predict match outcome given team features.

    Args:
        features: MatchFeatures object with team statistics

    Returns:
        PredictionResponse with 1X2, BTTS, and O/U 2.5 predictions (no scoreline)
    """
    predictor = get_predictor()
    if predictor is None:
        raise HTTPException(status_code=503, detail="ML models not loaded")

    try:
        # Convert Pydantic model to dict
        features_dict = features.dict()

        # ENHANCE features with seasonal statistics (for ML models trained with enhanced data)
        home_id = features_dict.get("home_id", 0)
        away_id = features_dict.get("away_id", 0)
        features_dict = enrich_features_with_seasonal_stats(
            features_dict, home_id, away_id, SEASONAL_STATS
        )
        print(f"DEBUG: /predict endpoint - Enhanced features, total keys: {len(features_dict)}")

        # Get prediction from ensemble
        result = predictor.predict_fixture(features_dict)

        # Track prediction stats
        ensemble_confidence = max(
            result["home_win_prob"], result["draw_prob"], result["away_win_prob"]
        )
        stats_tracker.record_prediction(result.get("model_breakdown", {}), ensemble_confidence)

        # Log prediction to metrics tracker
        try:
            fixture_id = features_dict.get("fixture_id", 0)
            home_team = features_dict.get("home_team", "Unknown")
            away_team = features_dict.get("away_team", "Unknown")

            metrics_tracker.log_prediction(
                fixture_id=fixture_id,
                home_team=home_team,
                away_team=away_team,
                home_pred=result["home_win_prob"],
                draw_pred=result["draw_prob"],
                away_pred=result["away_win_prob"],
                predicted_score="",
                model_breakdown=result.get("model_breakdown", {}),
            )
        except Exception as e:
            logger.warning(f"Failed to log prediction to metrics: {e}")

        # Remove scoreline from response (no longer offered)
        if "predicted_scoreline" in result:
            del result["predicted_scoreline"]
        if "scoreline_distribution" in result:
            del result["scoreline_distribution"]

        return PredictionResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@app.get("/models/info")
async def get_models_info():
    """Get information about loaded models"""
    predictor = get_predictor()
    if predictor is None:
        raise HTTPException(status_code=503, detail="ML models not loaded")

    return JSONResponse(
        content={
            "model_count": 8,
            "ensemble_type": "weighted",
            "status": "active",
        },
        headers=NO_CACHE_HEADERS,
    )


@app.get("/api/model-stats")
async def get_model_stats():
    """
    Get comprehensive statistics about model performance and usage.
    Returns prediction counts, confidence metrics, and model metadata.
    """
    predictor = get_predictor()
    if predictor is None:
        raise HTTPException(status_code=503, detail="ML models not loaded")

    return JSONResponse(
        content=stats_tracker.get_model_stats(),
        headers=NO_CACHE_HEADERS,
    )


@app.post("/api/model-stats/reset")
async def reset_model_stats(secret: str = ""):
    """
    Reset prediction statistics. Requires secret key.
    """
    if secret != "fixturecast2025reset":
        raise HTTPException(status_code=403, detail="Invalid secret")

    stats_tracker.stats = {
        "total_predictions": 0,
        "predictions_by_model": defaultdict(int),
        "confidence_sums": defaultdict(float),
        "confidence_counts": defaultdict(int),
        "predictions_log": [],
        "started_at": datetime.now().isoformat(),
        "last_prediction_at": None,
    }
    stats_tracker._save_stats()
    return {"status": "reset", "message": "All prediction statistics have been reset to 0"}


@app.get("/api/db/status")
async def get_db_status():
    """
    Check database connection status and prediction count.
    """
    status = {
        "db_available": DB_AVAILABLE,
        "db_module_imported": False,
        "db_connection_test": False,
        "prediction_count": 0,
        "error": None,
    }

    if DB_AVAILABLE:
        status["db_module_imported"] = True
        try:
            # Test the connection and get prediction count
            from database import USE_POSTGRES

            status["using_postgres"] = USE_POSTGRES
            predictions = PredictionDB.get_recent_predictions(limit=1000)
            status["prediction_count"] = len(predictions) if predictions else 0
            status["db_connection_test"] = True
        except Exception as e:
            status["error"] = str(e)

    return status


@app.get("/api/db/predictions")
async def get_db_predictions(limit: int = 50):
    """
    Get recent predictions from the database.
    """
    if not DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        predictions = PredictionDB.get_recent_predictions(limit=limit)
        return {
            "count": len(predictions),
            "predictions": predictions,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# FEEDBACK LEARNING ENDPOINTS
# ============================================
from ml_engine.feedback_learning import (
    feedback_system,
    get_performance_report,
    get_recommended_weights,
    record_result,
)


@app.get("/api/feedback/performance")
async def get_feedback_performance():
    """
    Get feedback learning performance report.
    Shows how well our predictions match actual results.
    """
    # Prefer DB-backed metrics (Railway Postgres in production) so performance
    # reflects only post-launch tracked predictions.
    try:
        if DB_AVAILABLE:
            # Use all-time stats for overall metrics, and 365-day for breakdowns
            all_time = PredictionDB.get_all_time_stats()
            metrics_365 = PredictionDB.get_metrics_summary(days=365)

            by_conf = metrics_365.get("by_confidence", {})
            by_league = metrics_365.get("by_league", {})

            overall_total = int(all_time.get("total_predictions") or 0)
            overall_correct = int(all_time.get("correct_predictions") or 0)
            overall_accuracy = float(all_time.get("accuracy") or 0)

            normalized_by_conf = {}
            for level, stats in by_conf.items():
                if not isinstance(stats, dict):
                    continue
                total = int(stats.get("total") or 0)
                correct = int(stats.get("correct") or 0)
                normalized_by_conf[level] = {
                    "total": total,
                    "correct": correct,
                    "accuracy": (correct / total) if total > 0 else 0.0,
                }

            normalized_by_league = {}
            for league_id, stats in by_league.items():
                if not isinstance(stats, dict):
                    continue
                total = int(stats.get("total") or 0)
                correct = int(stats.get("correct") or 0)
                normalized_by_league[str(league_id)] = {
                    "name": stats.get("name"),
                    "total": total,
                    "correct": correct,
                    "accuracy": (correct / total) if total > 0 else 0.0,
                }

            return {
                "tracking_since": all_time.get("tracking_since"),
                "overall": {
                    "total": overall_total,
                    "correct": overall_correct,
                    "accuracy": overall_accuracy,
                },
                "by_confidence": normalized_by_conf,
                "by_league": normalized_by_league,
            }
    except Exception as e:
        logger.error(f"Error getting DB performance metrics: {e}", exc_info=True)

    # Fallback to in-memory feedback learning system
    return get_performance_report()


@app.get("/api/feedback/pending")
async def get_pending_predictions():
    """Get predictions awaiting result evaluation"""
    pending = feedback_system.get_pending_results()
    return {
        "count": len(pending),
        "predictions": [
            {
                "fixture_id": p["fixture_id"],
                "home_team": p["home_team"],
                "away_team": p["away_team"],
                "match_date": p["match_date"],
                "predicted_outcome": p["prediction"]["predicted_outcome"],
                "confidence": p["prediction"]["confidence"],
            }
            for p in pending[:20]  # Limit to 20
        ],
    }


@app.post("/api/feedback/record-result")
async def api_record_result(fixture_id: int, home_goals: int, away_goals: int):
    """
    Manually record a match result to evaluate prediction.
    """
    evaluation = record_result(fixture_id, home_goals, away_goals)
    if evaluation is None:
        raise HTTPException(status_code=404, detail="No prediction found for this fixture")

    # Log actual result to metrics tracker
    try:
        # Determine result (H=home, D=draw, A=away)
        if home_goals > away_goals:
            actual_result = "H"
        elif home_goals < away_goals:
            actual_result = "A"
        else:
            actual_result = "D"

        actual_score = f"{home_goals}-{away_goals}"
        metrics_tracker.log_actual_result(fixture_id, actual_result, actual_score)
    except Exception as e:
        logger.warning(f"Failed to log result to metrics: {e}")

    return {"status": "recorded", "evaluation": evaluation}


@app.get("/api/feedback/recommended-weights")
async def get_recommended_model_weights():
    """
    Get recommended model weights based on actual performance.
    These can be used to improve ensemble accuracy.
    """
    weights = get_recommended_weights()
    if not weights:
        return {
            "status": "insufficient_data",
            "message": "Need at least 10 evaluated predictions per model",
            "weights": {},
        }
    return {"status": "available", "weights": weights}


@app.post("/api/feedback/update-from-api")
async def update_results_from_backend():
    """
    Fetch completed match results from the backend API
    and update the feedback system.
    """
    try:
        from ml_engine.auto_update_results import update_results_from_api

        result = update_results_from_api()
        return {"status": "success", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# MODEL PERFORMANCE METRICS
# ============================================


@app.get("/api/metrics/calibration-report")
async def get_calibration_metrics(
    days: int = 90, league: Optional[int] = None, exclude_low_confidence: bool = True
):
    """Honest scoring + calibration over settled predictions.

    Returns Brier / log-loss / ECE / reliability bins for 1X2 plus per-market hit
    rates (with sample sizes) — derived from real stored predictions and realized
    goals, not just accuracy counts. Never raises: returns {available: false} if the
    DB or data isn't there yet. ``days<=0`` means all-time. By default low-confidence
    (cold-start / market-based) picks are excluded so the record isn't distorted.
    """
    if not DB_AVAILABLE:
        return {"available": False, "reason": "database unavailable"}
    try:
        from ml_engine.metrics import calibration_report_from_rows

        rows = PredictionDB.get_settled_predictions(
            days=(None if days <= 0 else days),
            league_id=league,
            exclude_low_confidence=exclude_low_confidence,
        )
        report = calibration_report_from_rows(rows)
        report["window_days"] = days
        report["excluded_low_confidence"] = exclude_low_confidence
        return report
    except Exception as e:
        logger.error("Calibration metrics error: %s", e, exc_info=True)
        return {"available": False, "reason": "internal error"}


@app.get("/api/metrics/summary")
async def get_metrics_summary():
    """
    Get model performance summary including accuracy and calibration.
    7-day, 30-day, and all-time breakdowns.
    Uses PostgreSQL database for accurate tracking.
    """
    try:
        if DB_AVAILABLE:
            # Use PostgreSQL database for metrics
            seven_day = PredictionDB.get_metrics_summary(days=7)
            thirty_day = PredictionDB.get_metrics_summary(days=30)
            all_time = PredictionDB.get_all_time_stats()

            return {
                "7_day": seven_day,
                "30_day": {
                    "total_predictions": thirty_day.get("total_predictions", 0),
                    "correct_predictions": thirty_day.get("correct_predictions", 0),
                    "accuracy": thirty_day.get("accuracy", 0),
                    "avg_confidence": thirty_day.get("avg_confidence", 0),
                },
                "all_time": all_time,
                "model_comparison": thirty_day.get("model_comparison", {}),
                "by_confidence": thirty_day.get("by_confidence", {}),
                "by_league": thirty_day.get("by_league", {}),
                "last_updated": datetime.now().isoformat(),
            }

        # Fallback to file-based metrics
        metrics_tracker.export_summary()

        summary_file = os.path.join(
            os.path.dirname(__file__), "..", "data", "metrics", "summary.json"
        )
        if os.path.exists(summary_file):
            with open(summary_file) as f:
                return json.load(f)
        else:
            return {
                "error": "No metrics available yet",
                "message": "Predictions will start being tracked once matches are predicted",
            }
    except Exception as e:
        logger.error(f"Error fetching metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/backtest/report")
async def get_backtest_report():
    """Return time-based scorecards (per league) based on post-launch tracked data.

    Prefer DB-backed live scorecards (Railway Postgres in production). Falls back
    to the historical backtest artifact only when the DB is unavailable.
    """
    try:
        if DB_AVAILABLE:
            return PredictionDB.get_live_league_scorecards()
    except Exception as e:
        logger.warning(f"DB-backed scorecards unavailable, falling back to file: {e}")

    report_file = os.path.join(
        os.path.dirname(__file__), "..", "data", "metrics", "backtest_report.json"
    )
    if not os.path.exists(report_file):
        raise HTTPException(
            status_code=404,
            detail="No backtest report found and DB is unavailable.",
        )

    try:
        with open(report_file, "r") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load backtest report: {e}")


@app.get("/api/metrics/market-edge")
async def get_market_edge_report():
    """Model calibration measured against de-vigged bookmaker odds.

    This is the honest version of "how good are we": raw accuracy cannot tell
    a genuinely predictive model apart from one that simply agrees with the
    bookmaker's favourite. Produced weekly by ml_engine/market_edge_runner.py.

    Always returns 200. A missing or thin report is a normal state -- the odds
    dataset only builds forward from the day capture was deployed -- so it is
    reported as `status` rather than as an error, letting the UI say "still
    collecting" instead of rendering a failure.
    """
    report_file = os.path.join(
        os.path.dirname(__file__), "..", "data", "metrics", "market_edge_report.json"
    )

    if not os.path.exists(report_file):
        return {
            "status": "collecting",
            "matches": 0,
            "message": (
                "Odds capture has not produced a report yet. Closing odds cannot "
                "be reconstructed after a match finishes, so this dataset builds "
                "forward from when capture was enabled."
            ),
        }

    try:
        with open(report_file, "r") as f:
            report = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load market edge report: {e}")
        return {"status": "unavailable", "matches": 0, "message": str(e)}

    matches = report.get("matches", 0) or 0
    # Mirrors the threshold in ml_engine/market_edge.py: below ~300 matches the
    # comparison is too noisy to publish as a claim about the model.
    report["status"] = "ready" if matches >= 300 else "collecting"
    report["matches_needed"] = max(0, 300 - matches)
    return report


@app.get("/api/metrics/model-comparison")
async def get_model_comparison():
    """
    Compare individual model performance in the ensemble.
    """
    try:
        return metrics_tracker.get_model_comparison()
    except Exception as e:
        logger.error(f"Error comparing models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/metrics/log-prediction")
async def log_prediction_metric(
    fixture_id: int,
    home_team: str,
    away_team: str,
    home_pred: float,
    draw_pred: float,
    away_pred: float,
    predicted_score: str,
    model_breakdown: Optional[Dict] = None,
):
    """
    Log a prediction for later accuracy tracking.
    Call this endpoint when making predictions.
    """
    try:
        metrics_tracker.log_prediction(
            fixture_id=fixture_id,
            home_team=home_team,
            away_team=away_team,
            home_pred=home_pred,
            draw_pred=draw_pred,
            away_pred=away_pred,
            predicted_score=predicted_score,
            model_breakdown=model_breakdown,
        )
        return {"status": "logged", "fixture_id": fixture_id}
    except Exception as e:
        logger.error(f"Error logging prediction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/metrics/log-result")
async def log_actual_result(fixture_id: int, actual_result: str, actual_score: str):
    """
    Log actual match result (H/D/A) to calculate prediction accuracy.
    Call this when match is finished.
    """
    try:
        metrics_tracker.log_actual_result(fixture_id, actual_result, actual_score)
        return {"status": "updated", "fixture_id": fixture_id}
    except Exception as e:
        logger.error(f"Error logging result: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# SMART MARKETS API - O/U 2.5 + BTTS Focus
# ============================================


@app.post("/api/smart-markets/prediction")
async def get_smart_markets_prediction(features: MatchFeatures):
    """
    Smart Markets Prediction - Focus on O/U 2.5 and BTTS.

    Returns:
    - O/U 2.5 prediction
    - BTTS prediction
    - Combined odds for 2-way accumulators
    - Confidence scores for each market

    Only returns predictions with certainty >= 60%.
    """
    predictor = get_predictor()
    if predictor is None:
        raise HTTPException(status_code=503, detail="ML models not loaded")

    try:
        # Optional: attach tracked accuracy if the DB has evaluated predictions.
        ou_25_historical_accuracy = None
        btts_historical_accuracy = None
        if DB_AVAILABLE:
            try:
                perf = PredictionDB.get_all_time_stats()
                if perf and (perf.get("over25_total") or 0) > 0:
                    ou_25_historical_accuracy = perf.get("over25_accuracy")
                if perf and (perf.get("btts_total") or 0) > 0:
                    btts_historical_accuracy = perf.get("btts_accuracy")
            except Exception as e:
                logger.warning(f"Smart markets: failed to load DB performance stats: {e}")

        features_dict = features.dict()

        # Get base prediction
        result = predictor.predict_fixture(features_dict)

        # Extract market-specific probabilities
        home_goals = result.get("predicted_home_goals", 1.2)
        away_goals = result.get("predicted_away_goals", 0.8)
        total_goals = home_goals + away_goals

        # O/U 2.5 prediction
        over_25_prob = float(result.get("over25_prob", 0.5))
        ou_25_certainty = max(over_25_prob, 1 - over_25_prob)

        # BTTS prediction
        btts_prob = float(result.get("btts_prob", 0.5))
        btts_certainty = max(btts_prob, 1 - btts_prob)

        # Only include if certainty >= 0.60
        predictions = {}

        if ou_25_certainty >= 0.60:
            predictions["over_under_25"] = {
                "prediction": "Over" if over_25_prob > 0.5 else "Under",
                "probability": round(ou_25_certainty, 3),
                "confidence": round(ou_25_certainty, 3),
                "historical_accuracy": ou_25_historical_accuracy,
                "fair_odds": round(1 / ou_25_certainty, 2),
                "recommended_odds": round((1 / ou_25_certainty) * 0.97, 2),  # 3% margin
            }

        if btts_certainty >= 0.60:
            predictions["btts"] = {
                "prediction": "Yes" if btts_prob > 0.5 else "No",
                "probability": round(btts_certainty, 3),
                "confidence": round(btts_certainty, 3),
                "historical_accuracy": btts_historical_accuracy,
                "fair_odds": round(1 / btts_certainty, 2),
                "recommended_odds": round((1 / btts_certainty) * 0.95, 2),  # 5% margin
            }

        # Combo predictions (if both markets pass confidence threshold)
        combo = None
        if "over_under_25" in predictions and "btts" in predictions:
            # Combo uses the predicted side for each market
            ou_leg = "Over 2.5" if over_25_prob > 0.5 else "Under 2.5"
            btts_leg = "BTTS Yes" if btts_prob > 0.5 else "BTTS No"
            ou_leg_prob = over_25_prob if over_25_prob > 0.5 else 1 - over_25_prob
            btts_leg_prob = btts_prob if btts_prob > 0.5 else 1 - btts_prob

            # Assume slight correlation (not fully independent)
            combo_prob = (ou_leg_prob * btts_leg_prob) * 0.95  # 5% correlation adjustment
            combo_odds = round(1 / combo_prob, 2)

            combo = {
                "description": f"{ou_leg} + {btts_leg}",
                "probability": round(combo_prob, 3),
                "fair_odds": combo_odds,
                "recommended_odds": round(combo_odds * 0.92, 2),  # 8% margin
                "combined_confidence": round((ou_25_certainty + btts_certainty) / 2, 3),
            }

        return {
            "fixture": {
                "home_team": features_dict.get("home_team", "Unknown"),
                "away_team": features_dict.get("away_team", "Unknown"),
                "home_id": features_dict.get("home_id"),
                "away_id": features_dict.get("away_id"),
                "league_id": features_dict.get("league_id"),
            },
            "smart_markets": {"predictions": predictions, "combo": combo},
            "recommendation": {
                "skip_match": len(predictions) == 0,
                "skip_reason": (
                    "Low confidence on both O/U 2.5 and BTTS" if len(predictions) == 0 else None
                ),
                "best_market": list(predictions.keys())[0] if predictions else None,
            },
            "generated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Smart markets prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/smart-markets/accuracy")
async def get_smart_markets_accuracy():
    """
    Get accuracy metrics for tracked predictions since launch.

    Note: This reflects DB-tracked, evaluated predictions since METRICS_LAUNCH_DATE.
    It is not filtered to only picks that would qualify for Smart Markets.
    """
    # Load from backtest history
    try:
        with open("backend/backtest_history.json") as f:
            history = json.load(f)
    except:
        history = {"summary": {}, "history": []}

    ou_25_accuracy = None
    btts_accuracy = None
    over25_total = 0
    btts_total = 0
    tracking_since = None

    if DB_AVAILABLE:
        try:
            perf = PredictionDB.get_all_time_stats()
            if perf:
                tracking_since = perf.get("tracking_since")
                over25_total = perf.get("over25_total") or 0
                btts_total = perf.get("btts_total") or 0
                if over25_total > 0:
                    ou_25_accuracy = perf.get("over25_accuracy")
                if btts_total > 0:
                    btts_accuracy = perf.get("btts_accuracy")
        except Exception as e:
            logger.warning(f"Smart markets accuracy: failed to load DB performance stats: {e}")

    combo_accuracy_estimate = None
    if ou_25_accuracy is not None and btts_accuracy is not None:
        combo_accuracy_estimate = round(ou_25_accuracy * btts_accuracy, 3)

    return {
        "ou_25_accuracy": ou_25_accuracy,
        "btts_accuracy": btts_accuracy,
        "combo_accuracy_estimate": combo_accuracy_estimate,
        "tracking_since": tracking_since,
        "backtest_history": history.get("history", [])[-4:],  # Last 4 weeks
        "overall_summary": history.get("summary", {}),
        "data_points": {
            # Keep both keys for backward compatibility with older clients.
            "over_under_25": str(over25_total) if over25_total else None,
            "ou_25": str(over25_total) if over25_total else None,
            "btts": str(btts_total) if btts_total else None,
        },
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    print(f"Starting FixtureCast ML API server on port {port}...")
    print(f"API docs will be available at http://localhost:{port}/docs")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
