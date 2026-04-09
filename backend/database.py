"""
Database module for FixtureCast Performance Monitoring.
Supports both SQLite (local development) and PostgreSQL (production).
Auto-detects based on DATABASE_URL environment variable.
"""

import json
import os
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional


def _get_metrics_launch_date() -> date:
    """Get the UTC launch date for metrics/backtesting.

    This ensures reported accuracy/backtesting reflects only data collected
    since the app went live.
    """

    raw = os.environ.get("METRICS_LAUNCH_DATE", "2025-11-25")
    try:
        # Expect YYYY-MM-DD
        return date.fromisoformat(raw[:10])
    except Exception:
        # Fall back to the agreed launch date if env var is malformed
        return date(2025, 11, 25)


METRICS_LAUNCH_DATE = _get_metrics_launch_date()

# Check for PostgreSQL connection string
DATABASE_URL = os.environ.get("DATABASE_URL")

# Determine which database to use
USE_POSTGRES = DATABASE_URL is not None and DATABASE_URL.startswith(
    ("postgres://", "postgresql://")
)

if USE_POSTGRES:
    import pg8000.dbapi
    import urllib.parse

    print("🐘 Using PostgreSQL database (pg8000)")
else:
    import sqlite3

    # SQLite fallback path
    DB_PATH = os.environ.get(
        "FIXTURECAST_DB_PATH",
        os.path.join(os.path.dirname(__file__), "data", "fixturecast.db"),
    )
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    print(f"📁 Using SQLite database at {DB_PATH}")


def dict_factory(cursor, row):
    """Convert pg8000 tuple row into a dictionary based on column names."""
    if isinstance(row, dict) or hasattr(row, "keys"):
        return dict(row)
    return {col[0]: row[i] for i, col in enumerate(cursor.description)}


if USE_POSTGRES:
    class DictCursorFactory(pg8000.dbapi.Cursor):
        """Custom pg8000 cursor that returns rows as dictionaries."""
        def fetchone(self):
            row = super().fetchone()
            if row is None:
                return None
            return dict_factory(self, row)

        def fetchall(self):
            rows = super().fetchall()
            return [dict_factory(self, row) for row in rows]

        def fetchmany(self, size=None):
            rows = super().fetchmany(size)
            return [dict_factory(self, row) for row in rows]

        def __iter__(self):
            return self

        def __next__(self):
            row = super().__next__()
            return dict_factory(self, row)
else:
    DictCursorFactory = None


def get_db_connection():
    """Get a database connection."""
    if USE_POSTGRES:
        # Parse connection string for pg8000
        parsed = urllib.parse.urlparse(DATABASE_URL)
        pw = urllib.parse.unquote(parsed.password) if parsed.password else None
        
        conn = pg8000.dbapi.connect(
            user=parsed.username,
            password=pw,
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path[1:] # Remove leading slash
        )
        # Apply the dictionary cursor class globally for this connection
        conn.cursor = lambda **kwargs: DictCursorFactory(conn, **kwargs)
        
        return conn
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _get_placeholder():
    """Get the correct placeholder for the database type."""
    return "%s" if USE_POSTGRES else "?"


def _row_to_dict(row) -> Dict:
    """Convert a database row to a dictionary."""
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    try:
        return dict(row)
    except (TypeError, ValueError):
        # Fallback: create a numbered dict if it's a raw tuple
        return {f"col_{i}": val for i, val in enumerate(row)}


def _ensure_prediction_columns(cursor):
    columns = {
        "odds_home_win": "REAL DEFAULT 0",
        "odds_draw": "REAL DEFAULT 0",
        "odds_away_win": "REAL DEFAULT 0",
        "odds_over_25": "REAL DEFAULT 0",
        "odds_under_25": "REAL DEFAULT 0",
        "odds_btts_yes": "REAL DEFAULT 0",
        "odds_btts_no": "REAL DEFAULT 0",
    }

    if USE_POSTGRES:
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'predictions'
            """
        )
        rows = cursor.fetchall()
        
        # Safely extract column_name regardless of if the row is a dict or a native tuple depending on the factory state
        existing = set()
        for row in rows:
            if hasattr(row, "keys"):
                # It's a dict (expected behavior of DictCursorFactory)
                # Lowercase check because pg8000 may lowercase column headers
                for key in row.keys():
                    if str(key).lower() == "column_name":
                        existing.add(row[key])
                        break
            else:
                # Factory dropped, it's a native tuple or list. Use cursor.description
                if hasattr(cursor, 'description') and cursor.description:
                    desc = [d[0].lower() for d in cursor.description]
                    if "column_name" in desc:
                        idx = desc.index("column_name")
                        existing.add(row[idx])

        for name, col_type in columns.items():
            if name not in existing:
                cursor.execute(f"ALTER TABLE predictions ADD COLUMN {name} {col_type}")
    else:
        cursor.execute("PRAGMA table_info(predictions)")
        existing = {row["name"] if isinstance(row, dict) else row[1] for row in cursor.fetchall()}
        for name, col_type in columns.items():
            if name not in existing:
                cursor.execute(f"ALTER TABLE predictions ADD COLUMN {name} {col_type}")


def init_database():
    """Initialize the database schema."""
    with get_db() as conn:
        cursor = conn.cursor()

        if USE_POSTGRES:
            # PostgreSQL schema
            try:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS predictions (
                        id SERIAL PRIMARY KEY,
                        fixture_id INTEGER UNIQUE NOT NULL,
                        home_team TEXT NOT NULL,
                        away_team TEXT NOT NULL,
                        home_team_id INTEGER,
                        away_team_id INTEGER,
                        league_id INTEGER NOT NULL,
                        league_name TEXT,
                        match_date TIMESTAMP NOT NULL,
                        home_win_prob REAL NOT NULL,
                        draw_prob REAL NOT NULL,
                        away_win_prob REAL NOT NULL,
                        predicted_outcome TEXT NOT NULL,
                        confidence REAL NOT NULL,
                        confidence_level TEXT NOT NULL,
                        predicted_scoreline TEXT,
                        btts_prob REAL,
                        over25_prob REAL,
                        odds_home_win REAL DEFAULT 0,
                        odds_draw REAL DEFAULT 0,
                        odds_away_win REAL DEFAULT 0,
                        odds_over_25 REAL DEFAULT 0,
                        odds_under_25 REAL DEFAULT 0,
                        odds_btts_yes REAL DEFAULT 0,
                        odds_btts_no REAL DEFAULT 0,
                        model_breakdown TEXT,
                        result_home_goals INTEGER,
                        result_away_goals INTEGER,
                        actual_outcome TEXT,
                        match_status TEXT,
                        outcome_correct INTEGER,
                        brier_score REAL,
                        btts_correct INTEGER,
                        over25_correct INTEGER,
                        exact_score INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        result_recorded_at TIMESTAMP,
                        evaluated INTEGER DEFAULT 0
                    )
                """
                )
            except Exception as e:
                print(f"FATAL DB: Crash on first predictions execution: {e}", flush=True)
                raise
            
            _ensure_prediction_columns(cursor)

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS model_performance (
                    id SERIAL PRIMARY KEY,
                    model_name TEXT NOT NULL,
                    fixture_id INTEGER NOT NULL,
                    predicted_outcome TEXT NOT NULL,
                    actual_outcome TEXT,
                    is_correct INTEGER,
                    home_prob REAL,
                    draw_prob REAL,
                    away_prob REAL,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS daily_metrics (
                    id SERIAL PRIMARY KEY,
                    date DATE UNIQUE NOT NULL,
                    total_predictions INTEGER DEFAULT 0,
                    correct_predictions INTEGER DEFAULT 0,
                    accuracy REAL DEFAULT 0,
                    avg_confidence REAL DEFAULT 0,
                    avg_brier_score REAL DEFAULT 0,
                    high_conf_correct INTEGER DEFAULT 0,
                    high_conf_total INTEGER DEFAULT 0,
                    medium_conf_correct INTEGER DEFAULT 0,
                    medium_conf_total INTEGER DEFAULT 0,
                    low_conf_correct INTEGER DEFAULT 0,
                    low_conf_total INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS api_logs (
                    id SERIAL PRIMARY KEY,
                    endpoint TEXT NOT NULL,
                    method TEXT NOT NULL,
                    status_code INTEGER,
                    response_time_ms REAL,
                    error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Accumulator tables
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS accumulators (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    acca_type TEXT NOT NULL,
                    total_odds REAL NOT NULL,
                    stake REAL DEFAULT 10,
                    potential_return REAL NOT NULL,
                    status TEXT DEFAULT 'pending',
                    result TEXT,
                    won INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    settled_at TIMESTAMP,
                    UNIQUE(date, acca_type)
                )
            """
            )

            try:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS accumulator_selections (
                        id SERIAL PRIMARY KEY,
                        accumulator_id INTEGER NOT NULL,
                        fixture_id INTEGER NOT NULL,
                        home_team TEXT NOT NULL,
                        away_team TEXT NOT NULL,
                        league_id INTEGER,
                        league_name TEXT NOT NULL,
                        match_date TIMESTAMP NOT NULL,
                        selection_type TEXT NOT NULL,
                        selection_value TEXT NOT NULL,
                        odds REAL NOT NULL,
                        confidence REAL NOT NULL,
                        result TEXT,
                        won INTEGER DEFAULT 0,
                        FOREIGN KEY (accumulator_id) REFERENCES accumulators(id) ON DELETE CASCADE
                    )
                """
                )
            except Exception as e:
                print(f"FATAL DB: Crash on accumulator_selections execution: {e}", flush=True)
                raise

            # PostgreSQL indexes
            # Bypassing PostgreSQL indexes generation to prevent cloud timeout

            print("✅ PostgreSQL database initialized")

        else:
            # SQLite schema
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fixture_id INTEGER UNIQUE NOT NULL,
                    home_team TEXT NOT NULL,
                    away_team TEXT NOT NULL,
                    home_team_id INTEGER,
                    away_team_id INTEGER,
                    league_id INTEGER NOT NULL,
                    league_name TEXT,
                    match_date TIMESTAMP NOT NULL,
                    home_win_prob REAL NOT NULL,
                    draw_prob REAL NOT NULL,
                    away_win_prob REAL NOT NULL,
                    predicted_outcome TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    confidence_level TEXT NOT NULL,
                    predicted_scoreline TEXT,
                    btts_prob REAL,
                    over25_prob REAL,
                    odds_home_win REAL DEFAULT 0,
                    odds_draw REAL DEFAULT 0,
                    odds_away_win REAL DEFAULT 0,
                    odds_over_25 REAL DEFAULT 0,
                    odds_under_25 REAL DEFAULT 0,
                    odds_btts_yes REAL DEFAULT 0,
                    odds_btts_no REAL DEFAULT 0,
                    model_breakdown TEXT,
                    result_home_goals INTEGER,
                    result_away_goals INTEGER,
                    actual_outcome TEXT,
                    match_status TEXT,
                    outcome_correct INTEGER,
                    brier_score REAL,
                    btts_correct INTEGER,
                    over25_correct INTEGER,
                    exact_score INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    result_recorded_at TIMESTAMP,
                    evaluated INTEGER DEFAULT 0
                )
            """
            )
            _ensure_prediction_columns(cursor)

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS model_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT NOT NULL,
                    fixture_id INTEGER NOT NULL,
                    predicted_outcome TEXT NOT NULL,
                    actual_outcome TEXT,
                    is_correct INTEGER,
                    home_prob REAL,
                    draw_prob REAL,
                    away_prob REAL,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS daily_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE UNIQUE NOT NULL,
                    total_predictions INTEGER DEFAULT 0,
                    correct_predictions INTEGER DEFAULT 0,
                    accuracy REAL DEFAULT 0,
                    avg_confidence REAL DEFAULT 0,
                    avg_brier_score REAL DEFAULT 0,
                    high_conf_correct INTEGER DEFAULT 0,
                    high_conf_total INTEGER DEFAULT 0,
                    medium_conf_correct INTEGER DEFAULT 0,
                    medium_conf_total INTEGER DEFAULT 0,
                    low_conf_correct INTEGER DEFAULT 0,
                    low_conf_total INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS api_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint TEXT NOT NULL,
                    method TEXT NOT NULL,
                    status_code INTEGER,
                    response_time_ms REAL,
                    error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Accumulator tables
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS accumulators (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    acca_type TEXT NOT NULL,
                    total_odds REAL NOT NULL,
                    stake REAL DEFAULT 10,
                    potential_return REAL NOT NULL,
                    status TEXT DEFAULT 'pending',
                    result TEXT,
                    won INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    settled_at TIMESTAMP,
                    UNIQUE(date, acca_type)
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS accumulator_selections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    accumulator_id INTEGER NOT NULL,
                    fixture_id INTEGER NOT NULL,
                    home_team TEXT NOT NULL,
                    away_team TEXT NOT NULL,
                    league_id INTEGER,
                    league_name TEXT NOT NULL,
                    match_date TIMESTAMP NOT NULL,
                    selection_type TEXT NOT NULL,
                    selection_value TEXT NOT NULL,
                    odds REAL NOT NULL,
                    confidence REAL NOT NULL,
                    result TEXT,
                    won INTEGER DEFAULT 0,
                    FOREIGN KEY (accumulator_id) REFERENCES accumulators(id) ON DELETE CASCADE
                )
            """
            )

            # SQLite indexes
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_predictions_fixture ON predictions(fixture_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_predictions_date ON predictions(match_date)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_predictions_league ON predictions(league_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_predictions_evaluated ON predictions(evaluated)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_model_perf_model ON model_performance(model_name)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_daily_metrics_date ON daily_metrics(date)"
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_accumulators_date ON accumulators(date)")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_acca_selections_acca ON accumulator_selections(accumulator_id)"
            )

            print(f"✅ SQLite database initialized at {DB_PATH}")


# Alias for convenience
init_db = init_database


class PredictionDB:
    """Database operations for predictions and metrics."""

    @staticmethod
    def log_prediction(
        fixture_id: int,
        home_team: str,
        away_team: str,
        league_id: int,
        match_date: str,
        prediction: Dict,
        model_breakdown: Optional[Dict] = None,
        home_team_id: int = None,
        away_team_id: int = None,
        league_name: str = None,
    ) -> bool:
        """Log a new prediction to the database."""
        try:
            home_prob = prediction.get("home_win_prob", 0)
            draw_prob = prediction.get("draw_prob", 0)
            away_prob = prediction.get("away_win_prob", 0)

            if home_prob >= draw_prob and home_prob >= away_prob:
                predicted_outcome = "home"
            elif away_prob >= draw_prob:
                predicted_outcome = "away"
            else:
                predicted_outcome = "draw"

            max_prob = max(home_prob, draw_prob, away_prob)
            if max_prob >= 0.65:
                confidence_level = "high"
            elif max_prob >= 0.45:
                confidence_level = "medium"
            else:
                confidence_level = "low"

            def _safe_float(value):
                try:
                    return float(value)
                except Exception:
                    return 0.0

            odds = prediction.get("odds", {}) if isinstance(prediction, dict) else {}
            odds_1x2 = odds.get("1x2", {}) if isinstance(odds, dict) else {}
            odds_ou25 = odds.get("over_under_25", {}) if isinstance(odds, dict) else {}
            odds_btts = odds.get("btts", {}) if isinstance(odds, dict) else {}

            odds_home_win = _safe_float(odds_1x2.get("home", 0))
            odds_draw = _safe_float(odds_1x2.get("draw", 0))
            odds_away_win = _safe_float(odds_1x2.get("away", 0))
            odds_over_25 = _safe_float(odds_ou25.get("over", 0))
            odds_under_25 = _safe_float(odds_ou25.get("under", 0))
            odds_btts_yes = _safe_float(odds_btts.get("yes", 0))
            odds_btts_no = _safe_float(odds_btts.get("no", 0))

            with get_db() as conn:
                cursor = conn.cursor()

                if USE_POSTGRES:
                    cursor.execute(
                        """
                        INSERT INTO predictions (
                            fixture_id, home_team, away_team, home_team_id, away_team_id,
                            league_id, league_name, match_date,
                            home_win_prob, draw_prob, away_win_prob,
                            predicted_outcome, confidence, confidence_level,
                            predicted_scoreline, btts_prob, over25_prob,
                            odds_home_win, odds_draw, odds_away_win,
                            odds_over_25, odds_under_25,
                            odds_btts_yes, odds_btts_no,
                            model_breakdown
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (fixture_id) DO UPDATE SET
                            home_win_prob = EXCLUDED.home_win_prob,
                            draw_prob = EXCLUDED.draw_prob,
                            away_win_prob = EXCLUDED.away_win_prob,
                            predicted_outcome = EXCLUDED.predicted_outcome,
                            confidence = EXCLUDED.confidence,
                            odds_home_win = EXCLUDED.odds_home_win,
                            odds_draw = EXCLUDED.odds_draw,
                            odds_away_win = EXCLUDED.odds_away_win,
                            odds_over_25 = EXCLUDED.odds_over_25,
                            odds_under_25 = EXCLUDED.odds_under_25,
                            odds_btts_yes = EXCLUDED.odds_btts_yes,
                            odds_btts_no = EXCLUDED.odds_btts_no,
                            model_breakdown = EXCLUDED.model_breakdown
                    """,
                        (
                            fixture_id,
                            home_team,
                            away_team,
                            home_team_id,
                            away_team_id,
                            league_id,
                            league_name,
                            match_date,
                            home_prob,
                            draw_prob,
                            away_prob,
                            predicted_outcome,
                            max_prob,
                            confidence_level,
                            prediction.get("predicted_scoreline"),
                            prediction.get("btts_prob"),
                            prediction.get("over25_prob"),
                            odds_home_win,
                            odds_draw,
                            odds_away_win,
                            odds_over_25,
                            odds_under_25,
                            odds_btts_yes,
                            odds_btts_no,
                            json.dumps(model_breakdown) if model_breakdown else None,
                        ),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO predictions (
                            fixture_id, home_team, away_team, home_team_id, away_team_id,
                            league_id, league_name, match_date,
                            home_win_prob, draw_prob, away_win_prob,
                            predicted_outcome, confidence, confidence_level,
                            predicted_scoreline, btts_prob, over25_prob,
                            odds_home_win, odds_draw, odds_away_win,
                            odds_over_25, odds_under_25,
                            odds_btts_yes, odds_btts_no,
                            model_breakdown
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            fixture_id,
                            home_team,
                            away_team,
                            home_team_id,
                            away_team_id,
                            league_id,
                            league_name,
                            match_date,
                            home_prob,
                            draw_prob,
                            away_prob,
                            predicted_outcome,
                            max_prob,
                            confidence_level,
                            prediction.get("predicted_scoreline"),
                            prediction.get("btts_prob"),
                            prediction.get("over25_prob"),
                            odds_home_win,
                            odds_draw,
                            odds_away_win,
                            odds_over_25,
                            odds_under_25,
                            odds_btts_yes,
                            odds_btts_no,
                            json.dumps(model_breakdown) if model_breakdown else None,
                        ),
                    )

                # Log individual model predictions
                if model_breakdown:
                    ph = _get_placeholder()
                    for model_name, model_pred in model_breakdown.items():
                        m_home = model_pred.get("home_win", 0)
                        m_draw = model_pred.get("draw", 0)
                        m_away = model_pred.get("away_win", 0)

                        if m_home >= m_draw and m_home >= m_away:
                            m_outcome = "home"
                        elif m_away >= m_draw:
                            m_outcome = "away"
                        else:
                            m_outcome = "draw"

                        cursor.execute(
                            f"""
                            INSERT INTO model_performance (
                                model_name, fixture_id, predicted_outcome,
                                home_prob, draw_prob, away_prob
                            ) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                        """,
                            (model_name, fixture_id, m_outcome, m_home, m_draw, m_away),
                        )

                # Auto-tag Smart Markets predictions
                try:
                    from smart_markets_tracker import SmartMarketsTracker

                    over25_prob = prediction.get("over25_prob", 0) or 0
                    btts_prob = prediction.get("btts_prob", 0) or 0

                    smart_market_ou = 0
                    smart_market_btts = 0

                    # Check Over/Under 2.5 qualification
                    if (
                        over25_prob >= SmartMarketsTracker.CONFIDENCE_THRESHOLD
                        and odds_over_25 > 0
                        and odds_under_25 > 0
                    ):
                        implied = SmartMarketsTracker.twoWayImplied(odds_over_25, odds_under_25)
                        if implied:
                            edge = over25_prob - implied["a"]
                            if edge >= SmartMarketsTracker.EDGE_MARGIN:
                                smart_market_ou = 1

                    # Check BTTS qualification
                    if (
                        btts_prob >= SmartMarketsTracker.CONFIDENCE_THRESHOLD
                        and odds_btts_yes > 0
                        and odds_btts_no > 0
                    ):
                        implied = SmartMarketsTracker.twoWayImplied(odds_btts_yes, odds_btts_no)
                        if implied:
                            edge = btts_prob - implied["a"]
                            if edge >= SmartMarketsTracker.EDGE_MARGIN:
                                smart_market_btts = 1

                    # Update Smart Markets flags if qualification found
                    if smart_market_ou or smart_market_btts:
                        with get_db() as conn2:
                            cursor2 = conn2.cursor()
                            ph2 = "%s" if USE_POSTGRES else "?"
                            cursor2.execute(
                                f"""
                                UPDATE predictions
                                SET smart_market_ou = {ph2}, smart_market_btts = {ph2}
                                WHERE fixture_id = {ph2}
                                """,
                                (smart_market_ou, smart_market_btts, fixture_id),
                            )
                except Exception as e:
                    # Don't fail entire prediction save if Smart Markets tagging fails
                    print(f"Warning: Smart Markets auto-tagging failed: {e}")

            return True
        except Exception as e:
            print(f"Error logging prediction: {e}")
            return False

    @staticmethod
    def record_result(
        fixture_id: int, home_goals: int, away_goals: int, status: str = "FT"
    ) -> Optional[Dict]:
        """Record match result and evaluate prediction."""
        try:
            if home_goals > away_goals:
                actual_outcome = "home"
            elif away_goals > home_goals:
                actual_outcome = "away"
            else:
                actual_outcome = "draw"

            with get_db() as conn:
                cursor = conn.cursor()
                ph = _get_placeholder()

                cursor.execute(f"SELECT * FROM predictions WHERE fixture_id = {ph}", (fixture_id,))
                row = cursor.fetchone()

                if not row:
                    return None

                pred = _row_to_dict(row)
                outcome_correct = 1 if pred["predicted_outcome"] == actual_outcome else 0

                actual_probs = {"home": 0, "draw": 0, "away": 0}
                actual_probs[actual_outcome] = 1
                brier_score = (
                    (pred["home_win_prob"] - actual_probs["home"]) ** 2
                    + (pred["draw_prob"] - actual_probs["draw"]) ** 2
                    + (pred["away_win_prob"] - actual_probs["away"]) ** 2
                ) / 3

                btts_actual = home_goals > 0 and away_goals > 0
                btts_correct = 1 if ((pred.get("btts_prob", 0.5) >= 0.5) == btts_actual) else 0

                over25_actual = (home_goals + away_goals) > 2.5
                over25_correct = (
                    1 if ((pred.get("over25_prob", 0.5) >= 0.5) == over25_actual) else 0
                )

                exact_score = 0
                if pred.get("predicted_scoreline"):
                    try:
                        pred_home, pred_away = map(int, pred["predicted_scoreline"].split("-"))
                        exact_score = (
                            1 if (pred_home == home_goals and pred_away == away_goals) else 0
                        )
                    except (ValueError, AttributeError):
                        pass

                cursor.execute(
                    f"""
                    UPDATE predictions SET
                        result_home_goals = {ph}, result_away_goals = {ph},
                        actual_outcome = {ph}, match_status = {ph},
                        outcome_correct = {ph}, brier_score = {ph},
                        btts_correct = {ph}, over25_correct = {ph}, exact_score = {ph},
                        result_recorded_at = {ph}, evaluated = 1
                    WHERE fixture_id = {ph}
                """,
                    (
                        home_goals,
                        away_goals,
                        actual_outcome,
                        status,
                        outcome_correct,
                        brier_score,
                        btts_correct,
                        over25_correct,
                        exact_score,
                        datetime.now().isoformat(),
                        fixture_id,
                    ),
                )

                cursor.execute(
                    f"""
                    UPDATE model_performance SET
                        actual_outcome = {ph},
                        is_correct = CASE WHEN predicted_outcome = {ph} THEN 1 ELSE 0 END
                    WHERE fixture_id = {ph}
                """,
                    (actual_outcome, actual_outcome, fixture_id),
                )

                match_date = (
                    pred["match_date"][:10]
                    if isinstance(pred["match_date"], str)
                    else (
                        pred["match_date"].strftime("%Y-%m-%d")
                        if pred["match_date"]
                        else datetime.now().strftime("%Y-%m-%d")
                    )
                )
                PredictionDB._update_daily_metrics(cursor, match_date)

                return {
                    "fixture_id": fixture_id,
                    "outcome_correct": bool(outcome_correct),
                    "brier_score": brier_score,
                    "btts_correct": bool(btts_correct),
                    "over25_correct": bool(over25_correct),
                    "exact_score": bool(exact_score),
                    "predicted": pred["predicted_outcome"],
                    "actual": actual_outcome,
                }

        except Exception as e:
            print(f"Error recording result: {e}")
            return None

    @staticmethod
    def _update_daily_metrics(cursor, date: str):
        """Update aggregated daily metrics."""
        ph = _get_placeholder()

        cursor.execute(
            f"""
            SELECT
                COUNT(*) as total, SUM(outcome_correct) as correct,
                AVG(confidence) as avg_conf, AVG(brier_score) as avg_brier,
                SUM(CASE WHEN confidence_level = 'high' AND outcome_correct = 1 THEN 1 ELSE 0 END) as high_correct,
                SUM(CASE WHEN confidence_level = 'high' THEN 1 ELSE 0 END) as high_total,
                SUM(CASE WHEN confidence_level = 'medium' AND outcome_correct = 1 THEN 1 ELSE 0 END) as med_correct,
                SUM(CASE WHEN confidence_level = 'medium' THEN 1 ELSE 0 END) as med_total,
                SUM(CASE WHEN confidence_level = 'low' AND outcome_correct = 1 THEN 1 ELSE 0 END) as low_correct,
                SUM(CASE WHEN confidence_level = 'low' THEN 1 ELSE 0 END) as low_total
            FROM predictions
            WHERE DATE(match_date) = {ph} AND evaluated = 1
        """,
            (date,),
        )

        stats = _row_to_dict(cursor.fetchone())
        if stats and stats["total"] and stats["total"] > 0:
            accuracy = (stats["correct"] or 0) / stats["total"]

            if USE_POSTGRES:
                cursor.execute(
                    """
                    INSERT INTO daily_metrics (
                        date, total_predictions, correct_predictions, accuracy,
                        avg_confidence, avg_brier_score,
                        high_conf_correct, high_conf_total, medium_conf_correct, medium_conf_total,
                        low_conf_correct, low_conf_total, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (date) DO UPDATE SET
                        total_predictions = EXCLUDED.total_predictions,
                        correct_predictions = EXCLUDED.correct_predictions,
                        accuracy = EXCLUDED.accuracy, updated_at = EXCLUDED.updated_at
                """,
                    (
                        date,
                        stats["total"],
                        stats["correct"] or 0,
                        accuracy,
                        stats["avg_conf"] or 0,
                        stats["avg_brier"] or 0,
                        stats["high_correct"] or 0,
                        stats["high_total"] or 0,
                        stats["med_correct"] or 0,
                        stats["med_total"] or 0,
                        stats["low_correct"] or 0,
                        stats["low_total"] or 0,
                        datetime.now().isoformat(),
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO daily_metrics (
                        date, total_predictions, correct_predictions, accuracy,
                        avg_confidence, avg_brier_score,
                        high_conf_correct, high_conf_total, medium_conf_correct, medium_conf_total,
                        low_conf_correct, low_conf_total, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        date,
                        stats["total"],
                        stats["correct"] or 0,
                        accuracy,
                        stats["avg_conf"] or 0,
                        stats["avg_brier"] or 0,
                        stats["high_correct"] or 0,
                        stats["high_total"] or 0,
                        stats["med_correct"] or 0,
                        stats["med_total"] or 0,
                        stats["low_correct"] or 0,
                        stats["low_total"] or 0,
                        datetime.now().isoformat(),
                    ),
                )

    @staticmethod
    def get_pending_results() -> List[Dict]:
        """Get predictions that haven't been evaluated yet."""
        with get_db() as conn:
            cursor = conn.cursor()
            if USE_POSTGRES:
                cursor.execute(
                    """
                    SELECT fixture_id, home_team, away_team, league_id, match_date
                    FROM predictions WHERE evaluated = 0 AND match_date < NOW()
                    ORDER BY match_date ASC LIMIT 100
                """
                )
            else:
                cursor.execute(
                    """
                    SELECT fixture_id, home_team, away_team, league_id, match_date
                    FROM predictions WHERE evaluated = 0 AND match_date < datetime('now')
                    ORDER BY match_date ASC LIMIT 100
                """
                )
            return [_row_to_dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_metrics_summary(days: int = 7) -> Dict:
        """Get performance metrics summary for the last N days including all 3 markets."""
        with get_db() as conn:
            cursor = conn.cursor()
            # Clamp the window start to the app launch date so metrics only reflect
            # data collected since launch.
            now_utc = datetime.utcnow().date()
            window_start = now_utc - timedelta(days=days)
            cutoff_date = max(window_start, METRICS_LAUNCH_DATE)
            cutoff = cutoff_date.strftime("%Y-%m-%d")
            ph = _get_placeholder()

            # Get main stats including BTTS and Over 2.5
            cursor.execute(
                f"""
                SELECT COUNT(*) as total, SUM(outcome_correct) as correct,
                    SUM(btts_correct) as btts_correct, SUM(over25_correct) as over25_correct,
                    SUM(exact_score) as exact_score,
                    AVG(confidence) as avg_conf, MIN(confidence) as min_conf,
                    MAX(confidence) as max_conf, AVG(brier_score) as avg_brier,
                    AVG(btts_prob) as avg_btts_prob, AVG(over25_prob) as avg_over25_prob
                FROM predictions WHERE evaluated = 1 AND match_date >= {ph}
            """,
                (cutoff,),
            )

            stats = _row_to_dict(cursor.fetchone())
            if not stats or stats["total"] == 0:
                return {
                    "period_days": days,
                    "total_predictions": 0,
                    "accuracy": 0,
                    "message": "No evaluated predictions in this period",
                }

            cursor.execute(
                f"""
                SELECT confidence_level, COUNT(*) as total, SUM(outcome_correct) as correct
                FROM predictions WHERE evaluated = 1 AND match_date >= {ph}
                GROUP BY confidence_level
            """,
                (cutoff,),
            )

            by_confidence = {}
            for row in cursor.fetchall():
                row = _row_to_dict(row)
                by_confidence[row["confidence_level"]] = {
                    "total": row["total"],
                    "correct": row["correct"] or 0,
                    "accuracy": (row["correct"] or 0) / row["total"] if row["total"] > 0 else 0,
                }

            cursor.execute(
                f"""
                SELECT model_name, COUNT(*) as total, SUM(is_correct) as correct
                FROM model_performance mp JOIN predictions p ON mp.fixture_id = p.fixture_id
                WHERE p.evaluated = 1 AND p.match_date >= {ph}
                GROUP BY model_name ORDER BY SUM(is_correct) * 1.0 / COUNT(*) DESC
            """,
                (cutoff,),
            )

            model_comparison = {}
            for row in cursor.fetchall():
                row = _row_to_dict(row)
                model_comparison[row["model_name"]] = {
                    "total": row["total"],
                    "correct": row["correct"] or 0,
                    "accuracy": (row["correct"] or 0) / row["total"] if row["total"] > 0 else 0,
                }

            cursor.execute(
                f"""
                SELECT league_id, league_name, COUNT(*) as total,
                    SUM(outcome_correct) as correct, AVG(brier_score) as avg_brier
                FROM predictions WHERE evaluated = 1 AND match_date >= {ph}
                GROUP BY league_id, league_name ORDER BY COUNT(*) DESC
            """,
                (cutoff,),
            )

            by_league = {}
            for row in cursor.fetchall():
                row = _row_to_dict(row)
                by_league[str(row["league_id"])] = {
                    "name": row["league_name"],
                    "total": row["total"],
                    "correct": row["correct"] or 0,
                    "accuracy": (row["correct"] or 0) / row["total"] if row["total"] > 0 else 0,
                    "avg_brier": row["avg_brier"] or 0,
                }

            total = stats["total"]
            return {
                "period_days": days,
                "tracking_since": METRICS_LAUNCH_DATE.isoformat(),
                "total_predictions": total,
                # 1X2 Market
                "match_result": {
                    "correct": stats["correct"] or 0,
                    "total": total,
                    "accuracy": (stats["correct"] or 0) / total if total > 0 else 0,
                },
                # BTTS Market
                "btts": {
                    "correct": stats["btts_correct"] or 0,
                    "total": total,
                    "accuracy": (stats["btts_correct"] or 0) / total if total > 0 else 0,
                    "avg_prob": stats["avg_btts_prob"] or 0,
                },
                # Over 2.5 Market
                "over25": {
                    "correct": stats["over25_correct"] or 0,
                    "total": total,
                    "accuracy": (stats["over25_correct"] or 0) / total if total > 0 else 0,
                    "avg_prob": stats["avg_over25_prob"] or 0,
                },
                # Exact Score
                "exact_score": {
                    "correct": stats["exact_score"] or 0,
                    "total": total,
                    "accuracy": (stats["exact_score"] or 0) / total if total > 0 else 0,
                },
                # Legacy fields for backwards compatibility
                "correct_predictions": stats["correct"] or 0,
                "accuracy": (stats["correct"] or 0) / total if total > 0 else 0,
                "avg_confidence": stats["avg_conf"] or 0,
                "min_confidence": stats["min_conf"] or 0,
                "max_confidence": stats["max_conf"] or 0,
                "avg_brier_score": stats["avg_brier"] or 0,
                "by_confidence": by_confidence,
                "model_comparison": model_comparison,
                "by_league": by_league,
                "last_updated": datetime.now().isoformat(),
            }

    @staticmethod
    def get_all_time_stats() -> Dict:
        """Get all-time performance statistics."""
        with get_db() as conn:
            cursor = conn.cursor()
            ph = _get_placeholder()
            cutoff = METRICS_LAUNCH_DATE.isoformat()
            cursor.execute(
                f"""
                SELECT COUNT(*) as total, SUM(outcome_correct) as correct,
                    AVG(brier_score) as avg_brier, SUM(btts_correct) as btts_correct,
                    SUM(CASE WHEN btts_prob IS NOT NULL THEN 1 ELSE 0 END) as btts_total,
                    SUM(over25_correct) as over25_correct,
                    SUM(CASE WHEN over25_prob IS NOT NULL THEN 1 ELSE 0 END) as over25_total,
                    SUM(exact_score) as exact_scores
                FROM predictions WHERE evaluated = 1 AND match_date >= {ph}
            """,
                (cutoff,),
            )

            stats = _row_to_dict(cursor.fetchone())
            if not stats or stats["total"] == 0:
                return {
                    "total_predictions": 0,
                    "accuracy": 0,
                    "tracking_since": METRICS_LAUNCH_DATE.isoformat(),
                    "message": "No evaluated predictions yet",
                    "btts_total": 0,
                    "over25_total": 0,
                }

            return {
                "total_predictions": stats["total"],
                "correct_predictions": stats["correct"] or 0,
                "accuracy": (stats["correct"] or 0) / stats["total"],
                "avg_brier_score": stats["avg_brier"] or 0,
                "tracking_since": METRICS_LAUNCH_DATE.isoformat(),
                "btts_total": stats["btts_total"] or 0,
                "over25_total": stats["over25_total"] or 0,
                "btts_accuracy": (
                    (stats["btts_correct"] or 0) / stats["btts_total"] if stats["btts_total"] else 0
                ),
                "over25_accuracy": (
                    (stats["over25_correct"] or 0) / stats["over25_total"]
                    if stats["over25_total"]
                    else 0
                ),
                "exact_score_count": stats["exact_scores"] or 0,
                "exact_score_rate": (stats["exact_scores"] or 0) / stats["total"],
            }

    @staticmethod
    def get_daily_trend(days: int = 30) -> List[Dict]:
        """Get daily accuracy trend."""
        with get_db() as conn:
            cursor = conn.cursor()
            today_utc = datetime.utcnow().date()
            window_start = today_utc - timedelta(days=days)
            cutoff_date = max(window_start, METRICS_LAUNCH_DATE)
            cutoff = cutoff_date.isoformat()
            ph = _get_placeholder()
            cursor.execute(
                f"""
                SELECT date, total_predictions, correct_predictions,
                    accuracy, avg_confidence, avg_brier_score
                FROM daily_metrics
                WHERE date >= {ph}
                ORDER BY date ASC
            """,
                (cutoff,),
            )
            return [_row_to_dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_live_league_scorecards(
        cutoff_date: Optional[str] = None, threshold: float = 0.5
    ) -> Dict:
        """Compute per-league live scorecards from evaluated predictions.

        This is used to power the "Time-Based Backtest Scorecards" UI with
        post-launch, DB-backed data (Railway Postgres in production).
        """

        cutoff = (cutoff_date or METRICS_LAUNCH_DATE.isoformat())[:10]
        with get_db() as conn:
            cursor = conn.cursor()
            ph = _get_placeholder()

            cursor.execute(
                f"""
                SELECT
                    league_id,
                    league_name,
                    COUNT(*) as n,
                    SUM(outcome_correct) as correct_1x2,
                    AVG(confidence) as avg_conf,
                    SUM(CASE WHEN confidence >= {ph} THEN 1 ELSE 0 END) as picked_n,
                    SUM(CASE WHEN confidence >= {ph} THEN outcome_correct ELSE 0 END) as picked_correct,
                    SUM(COALESCE(btts_correct, 0)) as btts_correct,
                    SUM(COALESCE(over25_correct, 0)) as over25_correct
                FROM predictions
                WHERE evaluated = 1 AND match_date >= {ph}
                GROUP BY league_id, league_name
                ORDER BY COUNT(*) DESC
            """,
                (threshold, threshold, cutoff),
            )

            leagues = []
            total_matches = 0

            for row in cursor.fetchall():
                r = _row_to_dict(row)
                n = int(r.get("n") or 0)
                if n <= 0:
                    continue
                total_matches += n

                correct_1x2 = int(r.get("correct_1x2") or 0)
                picked_n = int(r.get("picked_n") or 0)
                picked_correct = int(r.get("picked_correct") or 0)
                btts_correct = int(r.get("btts_correct") or 0)
                over25_correct = int(r.get("over25_correct") or 0)

                leagues.append(
                    {
                        "league_id": (
                            int(r.get("league_id")) if r.get("league_id") is not None else None
                        ),
                        "league_name": r.get("league_name"),
                        "n": n,
                        "threshold": float(threshold),
                        "acc_1x2": correct_1x2 / n,
                        "acc_1x2_picked": (picked_correct / picked_n) if picked_n > 0 else None,
                        "coverage": (picked_n / n) if n > 0 else 0,
                        "avg_conf": float(r.get("avg_conf") or 0),
                        "btts_acc": (btts_correct / n) if n > 0 else 0,
                        "over25_acc": (over25_correct / n) if n > 0 else 0,
                    }
                )

            return {
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "tracking_since": METRICS_LAUNCH_DATE.isoformat(),
                "cutoff": cutoff,
                "threshold": threshold,
                "total_matches": total_matches,
                "leagues": leagues,
            }

    @staticmethod
    def get_recent_predictions(limit: int = 50) -> List[Dict]:
        """Get recent predictions with their evaluations."""
        with get_db() as conn:
            cursor = conn.cursor()
            ph = _get_placeholder()
            cursor.execute(
                f"""
                SELECT fixture_id, home_team, away_team, league_name, match_date,
                    home_win_prob, draw_prob, away_win_prob,
                    predicted_outcome, confidence, confidence_level,
                    predicted_scoreline, btts_prob, over25_prob,
                    result_home_goals, result_away_goals, actual_outcome,
                    outcome_correct, brier_score, btts_correct, over25_correct, evaluated
                FROM predictions ORDER BY match_date DESC LIMIT {ph}
            """,
                (limit,),
            )
            return [_row_to_dict(row) for row in cursor.fetchall()]

    @staticmethod
    def log_accumulator(
        date,
        acca_type: str,
        total_odds: float,
        stake: float,
        potential_return: float,
        status: str = "pending",
        result: str = None,
        won: bool = None,
    ) -> int:
        """Log a new accumulator bet. Returns accumulator ID."""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                ph = _get_placeholder()

                if USE_POSTGRES:
                    cursor.execute(
                        """
                        INSERT INTO accumulators (
                            date, acca_type, total_odds, stake, potential_return, status, result, won
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (date, acca_type) DO UPDATE SET
                            total_odds = EXCLUDED.total_odds,
                            stake = EXCLUDED.stake,
                            potential_return = EXCLUDED.potential_return,
                            status = EXCLUDED.status
                        RETURNING id
                        """,
                        (date, acca_type, total_odds, stake, potential_return, status, result, won),
                    )
                    result_row = cursor.fetchone()
                    acca_id = result_row["id"] if isinstance(result_row, dict) else result_row[0]
                else:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO accumulators (
                            date, acca_type, total_odds, stake, potential_return, status, result, won
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (date, acca_type, total_odds, stake, potential_return, status, result, won),
                    )
                    acca_id = cursor.lastrowid

                return acca_id
        except Exception as e:
            print(f"❌ Error logging accumulator: {e}")
            return None

    @staticmethod
    def log_accumulator_selection(
        accumulator_id: int,
        fixture_id: int,
        home_team: str,
        away_team: str,
        league_id: int,
        league_name: str,
        match_date: str,
        selection_type: str,
        selection_value: str,
        odds: float,
        confidence: float,
        result: str = None,
        won: bool = None,
    ) -> bool:
        """Log an individual selection within an accumulator."""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                ph = _get_placeholder()

                if USE_POSTGRES:
                    cursor.execute(
                        """
                        INSERT INTO accumulator_selections (
                            accumulator_id, fixture_id, home_team, away_team,
                            league_id, league_name, match_date,
                            selection_type, selection_value, odds, confidence, result, won
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            accumulator_id,
                            fixture_id,
                            home_team,
                            away_team,
                            league_id,
                            league_name,
                            match_date,
                            selection_type,
                            selection_value,
                            odds,
                            confidence,
                            result,
                            won,
                        ),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO accumulator_selections (
                            accumulator_id, fixture_id, home_team, away_team,
                            league_id, league_name, match_date,
                            selection_type, selection_value, odds, confidence, result, won
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            accumulator_id,
                            fixture_id,
                            home_team,
                            away_team,
                            league_id,
                            league_name,
                            match_date,
                            selection_type,
                            selection_value,
                            odds,
                            confidence,
                            result,
                            won,
                        ),
                    )

                return True
        except Exception as e:
            print(f"❌ Error logging accumulator selection: {e}")
            return False

    @staticmethod
    def get_today_accumulators() -> List[Dict]:
        """Get today's accumulators with their selections."""
        from datetime import date

        today = date.today()

        try:
            with get_db() as conn:
                cursor = conn.cursor()
                ph = _get_placeholder()

                # Get accumulators
                cursor.execute(
                    f"""
                    SELECT id, date, acca_type, total_odds, stake, potential_return,
                           status, result, won, created_at, settled_at
                    FROM accumulators
                    WHERE date = {ph}
                    ORDER BY acca_type
                    """,
                    (today,),
                )

                accas = []
                for row in cursor.fetchall():
                    acca = _row_to_dict(row)
                    acca_id = acca["id"]

                    # Get selections for this accumulator
                    cursor.execute(
                        f"""
                        SELECT fixture_id, home_team, away_team, league_id, league_name,
                               match_date, selection_type, selection_value, odds, confidence,
                               result, won
                        FROM accumulator_selections
                        WHERE accumulator_id = {ph}
                        ORDER BY match_date
                        """,
                        (acca_id,),
                    )

                    acca["selections"] = [_row_to_dict(sel) for sel in cursor.fetchall()]
                    accas.append(acca)

                return accas
        except Exception as e:
            print(f"❌ Error getting today's accumulators: {e}")
            return []

    @staticmethod
    def get_accumulator_history(days: int = 30) -> List[Dict]:
        """Get accumulator history for the last N days."""
        from datetime import date, timedelta

        cutoff = date.today() - timedelta(days=days)

        try:
            with get_db() as conn:
                cursor = conn.cursor()
                ph = _get_placeholder()

                cursor.execute(
                    f"""
                    SELECT date, acca_type, total_odds, stake, potential_return,
                           status, result, won
                    FROM accumulators
                    WHERE date >= {ph}
                    ORDER BY date DESC, acca_type
                    """,
                    (cutoff,),
                )

                history = [_row_to_dict(row) for row in cursor.fetchall()]
                for acca in history:
                    stake = float(acca.get("stake") or 0)
                    potential_return = float(acca.get("potential_return") or 0)
                    won = acca.get("won")
                    if won is True:
                        profit = potential_return - stake
                        roi = (profit / stake) if stake > 0 else 0
                    elif won is False:
                        profit = -stake
                        roi = -1.0 if stake > 0 else 0
                    else:
                        profit = None
                        roi = None
                    acca["profit"] = profit
                    acca["roi"] = roi

                return history
        except Exception as e:
            print(f"❌ Error getting accumulator history: {e}")
            return []

    @staticmethod
    def update_accumulator_result(accumulator_id: int, status: str, result: str, won: bool) -> bool:
        """Update the result of an accumulator."""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                ph = _get_placeholder()

                cursor.execute(
                    f"""
                    UPDATE accumulators
                    SET status = {ph}, result = {ph}, won = {ph}, settled_at = CURRENT_TIMESTAMP
                    WHERE id = {ph}
                    """,
                    (status, result, won, accumulator_id),
                )

                return True
        except Exception as e:
            print(f"❌ Error updating accumulator result: {e}")
            return False

    @staticmethod
    def update_selection_result(
        accumulator_id: int, fixture_id: int, result: str, won: bool
    ) -> bool:
        """Update the result of an individual selection."""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                ph = _get_placeholder()

                cursor.execute(
                    f"""
                    UPDATE accumulator_selections
                    SET result = {ph}, won = {ph}
                    WHERE accumulator_id = {ph} AND fixture_id = {ph}
                    """,
                    (result, won, accumulator_id, fixture_id),
                )

                return True
        except Exception as e:
            print(f"❌ Error updating selection result: {e}")
            return False

    @staticmethod
    def get_accumulator_stats(days: int = 30) -> Dict:
        """Get accumulator performance statistics."""
        from datetime import date, timedelta

        cutoff = date.today() - timedelta(days=days)

        try:
            with get_db() as conn:
                cursor = conn.cursor()
                ph = _get_placeholder()

                # Overall stats
                cursor.execute(
                    f"""
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN won = 1 THEN 1 ELSE 0 END) as won,
                        SUM(CASE WHEN status = 'settled' THEN 1 ELSE 0 END) as settled,
                        SUM(CASE WHEN won = 1 THEN potential_return ELSE 0 END) as total_returns,
                        SUM(stake) as total_staked
                    FROM accumulators
                    WHERE date >= {ph}
                    """,
                    (cutoff,),
                )

                overall = _row_to_dict(cursor.fetchone())

                # Stats by type
                cursor.execute(
                    f"""
                    SELECT
                        acca_type,
                        COUNT(*) as total,
                        SUM(CASE WHEN won = 1 THEN 1 ELSE 0 END) as won,
                        SUM(CASE WHEN status = 'settled' THEN 1 ELSE 0 END) as settled,
                        AVG(total_odds) as avg_odds,
                        SUM(CASE WHEN won = 1 THEN potential_return ELSE 0 END) as total_returns,
                        SUM(stake) as total_staked
                    FROM accumulators
                    WHERE date >= {ph}
                    GROUP BY acca_type
                    """,
                    (cutoff,),
                )

                by_type = [_row_to_dict(row) for row in cursor.fetchall()]
                for row in by_type:
                    total_returns = float(row.get("total_returns") or 0)
                    total_staked = float(row.get("total_staked") or 0)
                    settled_type = int(row.get("settled") or 0)
                    won_type = int(row.get("won") or 0)
                    profit = total_returns - total_staked
                    row["profit"] = profit
                    row["roi"] = (profit / total_staked) if total_staked > 0 else 0
                    row["hit_rate"] = (won_type / settled_type) if settled_type > 0 else 0

                # Calculate hit rates
                settled = overall.get("settled", 0) or 0
                won = overall.get("won", 0) or 0
                total_returns = overall.get("total_returns", 0) or 0
                total_staked = overall.get("total_staked", 0) or 0

                return {
                    "total_accumulators": overall.get("total", 0) or 0,
                    "settled_accumulators": settled,
                    "won_accumulators": won,
                    "hit_rate": (won / settled) if settled > 0 else 0,
                    "total_returns": total_returns,
                    "total_staked": total_staked,
                    "roi": (
                        ((total_returns - total_staked) / total_staked) if total_staked > 0 else 0
                    ),
                    "by_type": by_type,
                    "tracking_since": cutoff.isoformat(),
                }
        except Exception as e:
            print(f"❌ Error getting accumulator stats: {e}")
            return {
                "total_accumulators": 0,
                "settled_accumulators": 0,
                "won_accumulators": 0,
                "hit_rate": 0,
                "total_returns": 0,
                "total_staked": 0,
                "roi": 0,
                "by_type": [],
            }


# Initialize database on module load
init_database()
