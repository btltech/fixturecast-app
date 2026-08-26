"""
Public Forward Track Record Service for FixtureCast.

Manages the immutable pre-kickoff snapshot store (qualified_picks) and forward settlement.
Strictly forward-recorded in production: no historical backfilling and no post-match recalculation.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

FORWARD_RECORD_LAUNCH_DATE = "2026-08-20"


def _to_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default


def compute_streaks(results: List[bool]) -> Tuple[int, int]:
    """
    Computes (longest_losing_streak, current_streak) where streak is positive for wins,
    negative for losses.
    """
    if not results:
        return 0, 0

    max_losing = 0
    curr_losing = 0

    for r in results:
        if not r:  # Lost
            curr_losing += 1
            if curr_losing > max_losing:
                max_losing = curr_losing
        else:
            curr_losing = 0

    # Current streak (looking from latest backwards)
    latest = results[0]
    curr_streak = 0
    for r in results:
        if r == latest:
            curr_streak += (1 if latest else -1)
        else:
            break

    return max_losing, curr_streak


def record_qualified_pick(
    fixture_id: int,
    match_date: Any,
    home_team: str,
    away_team: str,
    market_type: str,
    selection_label: str,
    odds_at_pick: float,
    qualification_result: Any,  # QualificationResult or Dict
    league_id: Optional[int] = None,
    league_name: Optional[str] = None,
    kind: str = "single",
    stake_units: float = 1.0,
    qualifier_version: str = "v1.0-wilson-market",
    db_conn: Any = None,
) -> bool:
    """
    Records an immutable pre-kickoff snapshot of a qualified recommendation.
    Must be called at recommendation time, strictly prior to match kickoff.
    Refuses any recommendation where qualified != True.
    """
    if odds_at_pick <= 1.0:
        return False

    # Extract fields from QualificationResult or dict
    if hasattr(qualification_result, "to_dict"):
        q_dict = qualification_result.to_dict()
    elif isinstance(qualification_result, dict):
        q_dict = qualification_result
    else:
        return False

    # Strict gate: Only genuinely qualified selections are ever recorded
    if not q_dict.get("qualified"):
        return False

    try:
        from backend.database import USE_POSTGRES, get_db, _ensure_qualified_picks_table
    except ImportError:
        from database import USE_POSTGRES, get_db, _ensure_qualified_picks_table

    raw_prob = _to_float(q_dict.get("raw_probability"), 0.0)
    cons_prob = _to_float(q_dict.get("conservative_probability"), 0.0)
    imp_prob = _to_float(q_dict.get("implied_probability"), 0.0)
    edge = _to_float(q_dict.get("edge"), 0.0)
    sample_size = int(q_dict.get("sample_size") or 0)
    hierarchy_level = str(q_dict.get("hierarchy_level") or "unknown")

    conn_context = None
    if db_conn is None:
        conn_context = get_db()
        conn = conn_context.__enter__()
    else:
        conn = db_conn

    try:
        cursor = conn.cursor()
        _ensure_qualified_picks_table(cursor)

        match_date_str = str(match_date)[:19] if match_date else datetime.utcnow().isoformat()[:19]

        if USE_POSTGRES:
            cursor.execute(
                """
                INSERT INTO qualified_picks (
                    fixture_id, match_date, home_team, away_team, league_id, league_name,
                    kind, market_type, selection_label, odds_at_pick, raw_probability,
                    conservative_probability, implied_probability, edge, sample_size,
                    hierarchy_level, stake_units, qualifier_version, is_settled, result
                ) VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, 0, 'PENDING'
                ) ON CONFLICT (fixture_id, market_type, kind) DO NOTHING
                """,
                (
                    fixture_id, match_date_str, home_team, away_team, league_id, league_name,
                    kind, market_type, selection_label, odds_at_pick, raw_prob,
                    cons_prob, imp_prob, edge, sample_size,
                    hierarchy_level, stake_units, qualifier_version,
                ),
            )
        else:
            cursor.execute(
                """
                INSERT OR IGNORE INTO qualified_picks (
                    fixture_id, match_date, home_team, away_team, league_id, league_name,
                    kind, market_type, selection_label, odds_at_pick, raw_probability,
                    conservative_probability, implied_probability, edge, sample_size,
                    hierarchy_level, stake_units, qualifier_version, is_settled, result
                ) VALUES (
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, 0, 'PENDING'
                )
                """,
                (
                    fixture_id, match_date_str, home_team, away_team, league_id, league_name,
                    kind, market_type, selection_label, odds_at_pick, raw_prob,
                    cons_prob, imp_prob, edge, sample_size,
                    hierarchy_level, stake_units, qualifier_version,
                ),
            )

        return True
    except Exception as e:
        print(f"⚠️ Error recording qualified pick snapshot: {e}", flush=True)
        return False
    finally:
        if conn_context:
            conn_context.__exit__(None, None, None)


def settle_qualified_picks(db_conn: Any = None) -> int:
    """
    Settles pending qualified picks against evaluated match results.
    Computes exact profit/loss using the stored pre-match odds.
    """
    try:
        from backend.database import USE_POSTGRES, get_db, _ensure_qualified_picks_table
    except ImportError:
        from database import USE_POSTGRES, get_db, _ensure_qualified_picks_table

    conn_context = None
    if db_conn is None:
        conn_context = get_db()
        conn = conn_context.__enter__()
    else:
        conn = db_conn

    settled_count = 0
    try:
        cursor = conn.cursor()
        _ensure_qualified_picks_table(cursor)

        # Find unsettled picks where prediction is evaluated
        cursor.execute(
            """
            SELECT q.id, q.fixture_id, q.market_type, q.odds_at_pick,
                   p.actual_outcome, p.result_home_goals, p.result_away_goals,
                   p.over25_correct, p.btts_correct
            FROM qualified_picks q
            JOIN predictions p ON q.fixture_id = p.fixture_id
            WHERE (q.is_settled = 0 OR q.is_settled IS NULL) AND p.evaluated = 1 AND p.actual_outcome IS NOT NULL
            """
        )

        rows = cursor.fetchall()
        for row in rows:
            def _get(r, key, idx):
                return r[key] if isinstance(r, dict) or hasattr(r, "keys") else r[idx]

            pick_id = _get(row, "id", 0)
            market_type = _get(row, "market_type", 2)
            odds_at_pick = _to_float(_get(row, "odds_at_pick", 3), 1.0)
            actual_outcome = str(_get(row, "actual_outcome", 4) or "").lower()
            hg = _to_float(_get(row, "result_home_goals", 5), 0.0)
            ag = _to_float(_get(row, "result_away_goals", 6), 0.0)
            over25_corr = _get(row, "over25_correct", 7)
            btts_corr = _get(row, "btts_correct", 8)

            is_won = False
            if market_type in ("home_win", "1x2"):
                is_won = actual_outcome in ("home_win", "home", "1")
            elif market_type == "draw":
                is_won = actual_outcome in ("draw", "x")
            elif market_type == "away_win":
                is_won = actual_outcome in ("away_win", "away", "2")
            elif market_type == "over25":
                is_won = bool(over25_corr == 1) if over25_corr is not None else ((hg + ag) > 2.5)
            elif market_type == "under25":
                is_won = bool(over25_corr == 0) if over25_corr is not None else ((hg + ag) < 2.5)
            elif market_type == "btts":
                is_won = bool(btts_corr == 1) if btts_corr is not None else (hg > 0 and ag > 0)

            unit_pnl = round((odds_at_pick - 1.0) if is_won else -1.0, 2)
            result_str = "WON" if is_won else "LOST"

            if USE_POSTGRES:
                cursor.execute(
                    """
                    UPDATE qualified_picks
                    SET is_settled = 1, result = %s, unit_pnl = %s, settled_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (result_str, unit_pnl, pick_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE qualified_picks
                    SET is_settled = 1, result = ?, unit_pnl = ?, settled_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (result_str, unit_pnl, pick_id),
                )

            settled_count += 1

        return settled_count
    except Exception as e:
        print(f"⚠️ Error settling qualified picks: {e}", flush=True)
        return settled_count
    finally:
        if conn_context:
            conn_context.__exit__(None, None, None)


def generate_track_record(
    db_conn: Any = None,
    start_date: str = FORWARD_RECORD_LAUNCH_DATE,
) -> Dict[str, Any]:
    """
    Builds the public track record reading STRICTLY from immutable pre-kickoff snapshots.
    No historical backfill: only pre-kickoff qualified snapshots are served.
    """
    try:
        from backend.database import USE_POSTGRES, get_db, _ensure_qualified_picks_table, _ensure_accumulator_columns, _ensure_accumulator_selection_columns
    except ImportError:
        from database import USE_POSTGRES, get_db, _ensure_qualified_picks_table, _ensure_accumulator_columns, _ensure_accumulator_selection_columns

    conn_context = None
    if db_conn is None:
        conn_context = get_db()
        conn = conn_context.__enter__()
    else:
        conn = db_conn

    try:
        cursor = conn.cursor()
        _ensure_qualified_picks_table(cursor)
        _ensure_accumulator_columns(cursor)
        _ensure_accumulator_selection_columns(cursor)

        ph = "%s" if USE_POSTGRES else "?"

        # =========================================================================
        # 1. SINGLES: Read from immutable qualified_picks table
        # =========================================================================
        date_filter = "DATE(match_date) >= " + ph if USE_POSTGRES else "date(match_date) >= " + ph
        cursor.execute(
            f"""
            SELECT id, fixture_id, match_date, home_team, away_team, league_id, league_name,
                   market_type, selection_label, odds_at_pick, raw_probability,
                   conservative_probability, implied_probability, edge, sample_size,
                   hierarchy_level, stake_units, qualifier_version, is_settled, result, unit_pnl
            FROM qualified_picks
            WHERE is_settled = 1 AND kind = 'single'
              AND {date_filter}
            ORDER BY match_date DESC
            """,
            (start_date,),
        )

        rows = cursor.fetchall()
        singles_raw: List[Dict[str, Any]] = []

        for row in rows:
            def _get(r, key, idx):
                return r[key] if isinstance(r, dict) or hasattr(r, "keys") else r[idx]

            pick_id = _get(row, "id", 0)
            fixture_id = _get(row, "fixture_id", 1)
            match_date = str(_get(row, "match_date", 2) or "")[:10]
            home_team = _get(row, "home_team", 3)
            away_team = _get(row, "away_team", 4)
            league_name = _get(row, "league_name", 6) or "League"
            market_type = _get(row, "market_type", 7)
            selection_label = _get(row, "selection_label", 8)
            odds_at_pick = _to_float(_get(row, "odds_at_pick", 9))
            raw_prob = _to_float(_get(row, "raw_probability", 10))
            cons_prob = _to_float(_get(row, "conservative_probability", 11))
            imp_prob = _to_float(_get(row, "implied_probability", 12))
            edge = _to_float(_get(row, "edge", 13))
            sample_size = int(_get(row, "sample_size", 14) or 0)
            hierarchy_level = _get(row, "hierarchy_level", 15)
            result_str = _get(row, "result", 19)
            unit_pnl = _to_float(_get(row, "unit_pnl", 20))
            is_won = (result_str == "WON")

            singles_raw.append({
                "id": pick_id,
                "fixture_id": fixture_id,
                "date": match_date,
                "match": f"{home_team} vs {away_team}",
                "league": league_name,
                "market": market_type,
                "selection": selection_label,
                "odds": round(odds_at_pick, 2),
                "model_probability": round(raw_prob, 3),
                "conservative_probability": round(cons_prob, 3),
                "implied_probability": round(imp_prob, 3),
                "edge": round(edge, 3),
                "sample_size": sample_size,
                "hierarchy_level": hierarchy_level,
                "won": is_won,
                "result": result_str,
                "unit_pnl": round(unit_pnl, 2),
            })

        # Calculate chronological running units for Singles
        singles_chronological = sorted(singles_raw, key=lambda x: (x["date"], x["id"]))
        cum_units = 0.0
        for s in singles_chronological:
            cum_units += s["unit_pnl"]
            s["running_units"] = round(cum_units, 2)

        singles_history = list(reversed(singles_chronological))

        singles_total = len(singles_history)
        singles_won = sum(1 for s in singles_history if s["won"])
        singles_lost = singles_total - singles_won
        singles_profit = round(cum_units, 2)
        singles_roi = round((singles_profit / singles_total) * 100, 1) if singles_total > 0 else 0.0
        singles_avg_odds = round(sum(s["odds"] for s in singles_history) / singles_total, 2) if singles_total > 0 else 0.0
        singles_max_losing, singles_curr_streak = compute_streaks([s["won"] for s in singles_history])

        # =========================================================================
        # 2. ACCUMULATORS: Read STRICTLY from Qualified Accas (is_qualified_acca = 1)
        # =========================================================================
        date_filter_acca = "DATE(date) >= " + ph if USE_POSTGRES else "date(date) >= " + ph
        cursor.execute(
            f"""
            SELECT id, date, acca_type, total_odds, stake, potential_return,
                   status, result, won, is_qualified_acca, qualifier_version
            FROM accumulators
            WHERE status = 'settled' AND is_qualified_acca = 1
              AND {date_filter_acca}
            ORDER BY date DESC
            """,
            (start_date,),
        )

        acca_rows = cursor.fetchall()
        accas_raw: List[Dict[str, Any]] = []

        for row in acca_rows:
            def _get_a(r, key, idx):
                return r[key] if isinstance(r, dict) or hasattr(r, "keys") else r[idx]

            acca_id = _get_a(row, "id", 0)
            acca_date = str(_get_a(row, "date", 1))
            acca_type = _get_a(row, "acca_type", 2)
            total_odds = _to_float(_get_a(row, "total_odds", 3), 1.0)
            is_won = bool(_get_a(row, "won", 8) or 0)
            qualifier_ver = _get_a(row, "qualifier_version", 10) or "v1.0-wilson-market"

            # Query legs for this qualified accumulator with full audit evidence
            cursor.execute(
                """
                SELECT fixture_id, home_team, away_team, league_name, selection_type,
                       selection_value, odds, confidence, result, won,
                       raw_probability, conservative_probability, implied_probability,
                       edge, sample_size, hierarchy_level, qualifier_version
                FROM accumulator_selections
                WHERE accumulator_id = %s
                """ if USE_POSTGRES else
                """
                SELECT fixture_id, home_team, away_team, league_name, selection_type,
                       selection_value, odds, confidence, result, won,
                       raw_probability, conservative_probability, implied_probability,
                       edge, sample_size, hierarchy_level, qualifier_version
                FROM accumulator_selections
                WHERE accumulator_id = ?
                """,
                (acca_id,),
            )
            sel_rows = cursor.fetchall()
            legs = []
            for sel in sel_rows:
                def _get_s(r, key, idx):
                    return r[key] if isinstance(r, dict) or hasattr(r, "keys") else r[idx]

                raw_p = _get_s(sel, "raw_probability", 10)
                cons_p = _get_s(sel, "conservative_probability", 11)
                imp_p = _get_s(sel, "implied_probability", 12)
                edg = _get_s(sel, "edge", 13)
                ss = _get_s(sel, "sample_size", 14)
                hier = _get_s(sel, "hierarchy_level", 15)

                legs.append({
                    "match": f"{_get_s(sel, 'home_team', 1)} vs {_get_s(sel, 'away_team', 2)}",
                    "league": _get_s(sel, "league_name", 3),
                    "selection": f"{_get_s(sel, 'selection_type', 4)}: {_get_s(sel, 'selection_value', 5)}",
                    "odds": round(_to_float(_get_s(sel, "odds", 6)), 2),
                    "model_probability": round(_to_float(raw_p or _get_s(sel, "confidence", 7)), 3) if (raw_p is not None or _get_s(sel, "confidence", 7) is not None) else None,
                    "conservative_probability": round(_to_float(cons_p), 3) if cons_p is not None else None,
                    "implied_probability": round(_to_float(imp_p), 3) if imp_p is not None else None,
                    "edge": round(_to_float(edg), 3) if edg is not None else None,
                    "sample_size": int(ss) if ss is not None else None,
                    "hierarchy_level": hier,
                    "won": bool(_get_s(sel, "won", 9) or 0),
                })

            unit_pnl = (total_odds - 1.0) if is_won else -1.0
            accas_raw.append({
                "id": acca_id,
                "date": acca_date,
                "acca_type": acca_type,
                "total_odds": round(total_odds, 2),
                "qualifier_version": qualifier_ver,
                "legs_count": len(legs),
                "legs": legs,
                "won": is_won,
                "result": "WON" if is_won else "LOST",
                "unit_pnl": round(unit_pnl, 2),
            })

        # Calculate running units for Accas
        accas_chronological = sorted(accas_raw, key=lambda x: (x["date"], x["id"]))
        cum_acca_units = 0.0
        for a in accas_chronological:
            cum_acca_units += a["unit_pnl"]
            a["running_units"] = round(cum_acca_units, 2)

        accas_history = list(reversed(accas_chronological))

        acca_total = len(accas_history)
        acca_won = sum(1 for a in accas_history if a["won"])
        acca_lost = acca_total - acca_won
        acca_profit = round(cum_acca_units, 2)
        acca_roi = round((acca_profit / acca_total) * 100, 1) if acca_total > 0 else 0.0
        acca_avg_odds = round(sum(a["total_odds"] for a in accas_history) / acca_total, 2) if acca_total > 0 else 0.0
        acca_max_losing, acca_curr_streak = compute_streaks([a["won"] for a in accas_history])

        # Overall Combined Metrics
        total_bets = singles_total + acca_total
        total_won = singles_won + acca_won
        total_profit = round(singles_profit + acca_profit, 2)
        total_roi = round((total_profit / total_bets) * 100, 1) if total_bets > 0 else 0.0

        return {
            "launch_date": start_date,
            "disclaimer": {
                "start_note": f"Record started {datetime.fromisoformat(start_date).strftime('%d %b %Y')}",
                "backfill_policy": "Strictly forward-recorded from immutable pre-kickoff snapshots. Zero historical backfill.",
                "transparency_note": "Every pre-kickoff qualified recommendation is included regardless of outcome.",
                "legal": "Past performance does not guarantee future results. Please gamble responsibly.",
            },
            "summary": {
                "total_bets": total_bets,
                "won": total_won,
                "lost": total_bets - total_won,
                "win_rate_pct": round((total_won / total_bets) * 100, 1) if total_bets > 0 else 0.0,
                "staked_units": total_bets,
                "profit_units": total_profit,
                "roi_pct": total_roi,
            },
            "singles": {
                "summary": {
                    "total_bets": singles_total,
                    "won": singles_won,
                    "lost": singles_lost,
                    "win_rate_pct": round((singles_won / singles_total) * 100, 1) if singles_total > 0 else 0.0,
                    "staked_units": singles_total,
                    "profit_units": singles_profit,
                    "roi_pct": singles_roi,
                    "avg_odds": singles_avg_odds,
                    "longest_losing_streak": singles_max_losing,
                    "current_streak": singles_curr_streak,
                },
                "history": singles_history,
            },
            "accas": {
                "summary": {
                    "total_bets": acca_total,
                    "won": acca_won,
                    "lost": acca_lost,
                    "win_rate_pct": round((acca_won / acca_total) * 100, 1) if acca_total > 0 else 0.0,
                    "staked_units": acca_total,
                    "profit_units": acca_profit,
                    "roi_pct": acca_roi,
                    "avg_odds": acca_avg_odds,
                    "longest_losing_streak": acca_max_losing,
                    "current_streak": acca_curr_streak,
                },
                "history": accas_history,
            },
        }
    finally:
        if conn_context:
            conn_context.__exit__(None, None, None)
