"""
Today's FixtureCast — Daily Qualified Picks & Distribution Service.

Separates QUALIFIED candidates from the FROZEN DAILY PICK:
- Candidate qualification runs continuously via canonical Wilson 90% qualifier.
- Scheduled agent/job runs `freeze_daily_featured_picks()` to formally designate
  exactly ONE Daily Single and ONE Daily Acca before kickoff.
- Kickoff guard: ONLY future fixtures (kickoff > selection time) that are unsettled can be selected.
- Public `GET /api/recommendations/today` is 100% READ-ONLY (no mutation).
- Once frozen in `daily_featured_picks` with UNIQUE(date, kind), the selection can NEVER change.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional


def _to_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default


def _parse_datetime(dt_val: Any) -> Optional[datetime]:
    if not dt_val:
        return None
    if isinstance(dt_val, datetime):
        return dt_val
    try:
        s = str(dt_val)[:19]
        if "T" in s:
            return datetime.fromisoformat(s)
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def freeze_daily_featured_picks(
    target_date: Optional[str] = None,
    current_time: Optional[datetime] = None,
    db_conn: Any = None,
) -> Dict[str, Any]:
    """
    Evaluates pre-kickoff qualified candidates and freezes today's official Daily Single
    and Daily Acca in `daily_featured_picks`.
    
    STRICT GUARDS:
    - Fixture kickoff must be in the future (kickoff > current_time).
    - Fixture must not be settled.
    - If already frozen for (date, kind), existing frozen pick is preserved (zero mutation).
    """
    try:
        from backend.database import (
            USE_POSTGRES,
            get_db,
            _ensure_qualified_picks_table,
            _ensure_accumulator_columns,
            _ensure_accumulator_selection_columns,
            _ensure_daily_featured_picks_table,
        )
    except ImportError:
        from database import (
            USE_POSTGRES,
            get_db,
            _ensure_qualified_picks_table,
            _ensure_accumulator_columns,
            _ensure_accumulator_selection_columns,
            _ensure_daily_featured_picks_table,
        )

    today_str = target_date or date.today().isoformat()
    now_utc = current_time or datetime.utcnow()

    conn_context = None
    if db_conn is None:
        conn_context = get_db()
        conn = conn_context.__enter__()
    else:
        conn = db_conn

    frozen_single_id = None
    frozen_acca_id = None

    try:
        cursor = conn.cursor()
        _ensure_qualified_picks_table(cursor)
        _ensure_accumulator_columns(cursor)
        _ensure_accumulator_selection_columns(cursor)
        _ensure_daily_featured_picks_table(cursor)

        ph = "%s" if USE_POSTGRES else "?"
        date_filter_feat = "DATE(date) = " + ph if USE_POSTGRES else "substr(date, 1, 10) = " + ph

        # =========================================================================
        # 1. FREEZE DAILY SINGLE (IF NOT ALREADY FROZEN)
        # =========================================================================
        cursor.execute(
            f"""
            SELECT id, qualified_pick_id, fixture_id, status
            FROM daily_featured_picks
            WHERE {date_filter_feat} AND kind = 'single'
            LIMIT 1
            """,
            (today_str,),
        )
        existing_single = cursor.fetchone()

        if existing_single:
            def _get_es(r, key, idx):
                return r[key] if isinstance(r, dict) or hasattr(r, "keys") else r[idx]
            frozen_single_id = _get_es(existing_single, "qualified_pick_id", 1)
        else:
            # Query candidate qualified singles for today
            date_filter_qp = "DATE(match_date) = " + ph if USE_POSTGRES else "substr(match_date, 1, 10) = " + ph
            cursor.execute(
                f"""
                SELECT id, fixture_id, match_date, home_team, away_team, edge, odds_at_pick
                FROM qualified_picks
                WHERE kind = 'single' AND (is_settled = 0 OR is_settled IS NULL) AND {date_filter_qp}
                ORDER BY edge DESC, odds_at_pick DESC
                """,
                (today_str,),
            )
            candidate_singles = cursor.fetchall()

            for cand in candidate_singles:
                def _get_c(r, key, idx):
                    return r[key] if isinstance(r, dict) or hasattr(r, "keys") else r[idx]
                c_id = _get_c(cand, "id", 0)
                c_fix_id = _get_c(cand, "fixture_id", 1)
                c_match_date = _get_c(cand, "match_date", 2)
                kickoff_dt = _parse_datetime(c_match_date)

                # STRICT KICKOFF GUARD: Only future, unstarted fixtures can be selected
                if kickoff_dt and kickoff_dt > now_utc:
                    try:
                        if USE_POSTGRES:
                            cursor.execute(
                                """
                                INSERT INTO daily_featured_picks (date, kind, qualified_pick_id, fixture_id, status)
                                VALUES (%s, 'single', %s, %s, 'selected')
                                ON CONFLICT (date, kind) DO NOTHING
                                """,
                                (today_str, c_id, c_fix_id),
                            )
                        else:
                            cursor.execute(
                                """
                                INSERT OR IGNORE INTO daily_featured_picks (date, kind, qualified_pick_id, fixture_id, status)
                                VALUES (?, 'single', ?, ?, 'selected')
                                """,
                                (today_str, c_id, c_fix_id),
                            )
                        try:
                            conn.commit()
                        except Exception:
                            pass
                        frozen_single_id = c_id
                        break
                    except Exception as err:
                        print(f"⚠️ Error freezing single pick: {err}")

            # If no candidate qualified or none was eligible, record explicit no_pick status
            if frozen_single_id is None:
                try:
                    if USE_POSTGRES:
                        cursor.execute(
                            """
                            INSERT INTO daily_featured_picks (date, kind, qualified_pick_id, fixture_id, status)
                            VALUES (%s, 'single', NULL, NULL, 'no_pick')
                            ON CONFLICT (date, kind) DO NOTHING
                            """,
                            (today_str,),
                        )
                    else:
                        cursor.execute(
                            """
                            INSERT OR IGNORE INTO daily_featured_picks (date, kind, qualified_pick_id, fixture_id, status)
                            VALUES (?, 'single', NULL, NULL, 'no_pick')
                            """,
                            (today_str,),
                        )
                    try:
                        conn.commit()
                    except Exception:
                        pass
                except Exception as err:
                    print(f"⚠️ Error recording single no_pick freeze: {err}")

        # =========================================================================
        # 2. FREEZE DAILY ACCA (IF NOT ALREADY FROZEN)
        # =========================================================================
        cursor.execute(
            f"""
            SELECT id, accumulator_id, status
            FROM daily_featured_picks
            WHERE {date_filter_feat} AND kind = 'acca'
            LIMIT 1
            """,
            (today_str,),
        )
        existing_acca = cursor.fetchone()

        if existing_acca:
            def _get_ea(r, key, idx):
                return r[key] if isinstance(r, dict) or hasattr(r, "keys") else r[idx]
            frozen_acca_id = _get_ea(existing_acca, "accumulator_id", 1)
        else:
            date_filter_acca = "DATE(date) = " + ph if USE_POSTGRES else "substr(date, 1, 10) = " + ph
            cursor.execute(
                f"""
                SELECT id, date, total_odds, status
                FROM accumulators
                WHERE (is_qualified_acca = 1) AND status != 'settled' AND {date_filter_acca}
                ORDER BY total_odds DESC
                """,
                (today_str,),
            )
            candidate_accas = cursor.fetchall()

            for cand_a in candidate_accas:
                def _get_ca(r, key, idx):
                    return r[key] if isinstance(r, dict) or hasattr(r, "keys") else r[idx]
                a_id = _get_ca(cand_a, "id", 0)

                # Query legs to ensure ALL legs have kickoff in the future
                cursor.execute(
                    """
                    SELECT match_date
                    FROM accumulator_selections
                    WHERE accumulator_id = %s
                    """ if USE_POSTGRES else
                    """
                    SELECT match_date
                    FROM accumulator_selections
                    WHERE accumulator_id = ?
                    """,
                    (a_id,),
                )
                leg_rows = cursor.fetchall()
                all_legs_future = True
                for lr in leg_rows:
                    l_dt = _parse_datetime(lr[0] if isinstance(lr, (list, tuple)) else lr["match_date"])
                    if not l_dt or l_dt <= now_utc:
                        all_legs_future = False
                        break

                # STRICT KICKOFF GUARD FOR ACCAS
                if all_legs_future and leg_rows:
                    try:
                        if USE_POSTGRES:
                            cursor.execute(
                                """
                                INSERT INTO daily_featured_picks (date, kind, accumulator_id, status)
                                VALUES (%s, 'acca', %s, 'selected')
                                ON CONFLICT (date, kind) DO NOTHING
                                """,
                                (today_str, a_id),
                            )
                        else:
                            cursor.execute(
                                """
                                INSERT OR IGNORE INTO daily_featured_picks (date, kind, accumulator_id, status)
                                VALUES (?, 'acca', ?, 'selected')
                                """,
                                (today_str, a_id),
                            )
                        try:
                            conn.commit()
                        except Exception:
                            pass
                        frozen_acca_id = a_id
                        break
                    except Exception as err:
                        print(f"⚠️ Error freezing acca pick: {err}")

            # If no acca qualified or none was eligible, record explicit no_pick status
            if frozen_acca_id is None:
                try:
                    if USE_POSTGRES:
                        cursor.execute(
                            """
                            INSERT INTO daily_featured_picks (date, kind, accumulator_id, status)
                            VALUES (%s, 'acca', NULL, 'no_pick')
                            ON CONFLICT (date, kind) DO NOTHING
                            """,
                            (today_str,),
                        )
                    else:
                        cursor.execute(
                            """
                            INSERT OR IGNORE INTO daily_featured_picks (date, kind, accumulator_id, status)
                            VALUES (?, 'acca', NULL, 'no_pick')
                            """,
                            (today_str,),
                        )
                    try:
                        conn.commit()
                    except Exception:
                        pass
                except Exception as err:
                    print(f"⚠️ Error recording acca no_pick freeze: {err}")

        return {
            "date": today_str,
            "freeze_status": "completed",
            "frozen_at": now_utc.isoformat() + "Z",
            "frozen_single_id": frozen_single_id,
            "frozen_acca_id": frozen_acca_id,
        }
    finally:
        if conn_context:
            conn_context.__exit__(None, None, None)


def get_todays_fixturecast(
    target_date: Optional[str] = None,
    db_conn: Any = None,
) -> Dict[str, Any]:
    """
    100% READ-ONLY API endpoint for Today's FixtureCast.
    Reads strictly from the pre-frozen `daily_featured_picks` table.
    Zero mutation / zero on-the-fly selection.
    """
    try:
        from backend.database import (
            USE_POSTGRES,
            get_db,
            _ensure_qualified_picks_table,
            _ensure_accumulator_columns,
            _ensure_accumulator_selection_columns,
            _ensure_daily_featured_picks_table,
        )
        from backend.track_record_service import generate_track_record
    except ImportError:
        from database import (
            USE_POSTGRES,
            get_db,
            _ensure_qualified_picks_table,
            _ensure_accumulator_columns,
            _ensure_accumulator_selection_columns,
            _ensure_daily_featured_picks_table,
        )
        from track_record_service import generate_track_record

    today_str = target_date or date.today().isoformat()
    now_utc = datetime.utcnow()

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
        _ensure_daily_featured_picks_table(cursor)

        ph = "%s" if USE_POSTGRES else "?"
        date_filter_feat = "DATE(date) = " + ph if USE_POSTGRES else "substr(date, 1, 10) = " + ph

        # =========================================================================
        # 1. READ FROZEN DAILY SINGLE (READ-ONLY)
        # =========================================================================
        cursor.execute(
            f"""
            SELECT qualified_pick_id, fixture_id, selected_at, status
            FROM daily_featured_picks
            WHERE {date_filter_feat} AND kind = 'single'
            LIMIT 1
            """,
            (today_str,),
        )
        featured_single = cursor.fetchone()

        freeze_status = "pending" if featured_single is None else "completed"
        qualified_single = None

        if featured_single:
            def _get_fs(r, key, idx):
                return r[key] if isinstance(r, dict) or hasattr(r, "keys") else r[idx]
            q_pick_id = _get_fs(featured_single, "qualified_pick_id", 0)
            selected_at_str = str(_get_fs(featured_single, "selected_at", 2))

            if q_pick_id:
                cursor.execute(
                    """
                    SELECT id, fixture_id, match_date, home_team, away_team, league_id, league_name,
                           market_type, selection_label, odds_at_pick, raw_probability,
                           conservative_probability, implied_probability, edge, sample_size,
                           hierarchy_level, stake_units, qualifier_version, is_settled, result, unit_pnl
                    FROM qualified_picks
                    WHERE id = %s
                    """ if USE_POSTGRES else
                    """
                    SELECT id, fixture_id, match_date, home_team, away_team, league_id, league_name,
                           market_type, selection_label, odds_at_pick, raw_probability,
                           conservative_probability, implied_probability, edge, sample_size,
                           hierarchy_level, stake_units, qualifier_version, is_settled, result, unit_pnl
                    FROM qualified_picks
                    WHERE id = ?
                    """,
                    (q_pick_id,),
                )
                single_row = cursor.fetchone()
                if single_row:
                    def _get(r, key, idx):
                        return r[key] if isinstance(r, dict) or hasattr(r, "keys") else r[idx]

                    fixture_id = _get(single_row, "fixture_id", 1)
                    match_date_raw = _get(single_row, "match_date", 2)
                    home_team = _get(single_row, "home_team", 3)
                    away_team = _get(single_row, "away_team", 4)
                    league_name = _get(single_row, "league_name", 6) or "League"
                    market_type = _get(single_row, "market_type", 7)
                    selection_label = _get(single_row, "selection_label", 8)
                    odds = _to_float(_get(single_row, "odds_at_pick", 9))
                    raw_prob = _to_float(_get(single_row, "raw_probability", 10))
                    cons_prob = _to_float(_get(single_row, "conservative_probability", 11))
                    imp_prob = _to_float(_get(single_row, "implied_probability", 12))
                    edge = _to_float(_get(single_row, "edge", 13))
                    sample_size = int(_get(single_row, "sample_size", 14) or 0)
                    hier = _get(single_row, "hierarchy_level", 15)
                    is_settled = bool(_get(single_row, "is_settled", 18) or 0)
                    res_str = _get(single_row, "result", 19)
                    unit_pnl = _to_float(_get(single_row, "unit_pnl", 20))

                    kickoff_dt = _parse_datetime(match_date_raw)
                    if is_settled:
                        match_phase = "SETTLED"
                    elif kickoff_dt and kickoff_dt <= now_utc:
                        match_phase = "LIVE"
                    else:
                        match_phase = "UPCOMING"

                    qualified_single = {
                        "has_pick": True,
                        "daily_pick_frozen": True,
                        "selected_at": selected_at_str,
                        "fixture_id": fixture_id,
                        "date": today_str,
                        "kickoff": str(match_date_raw)[:19] if match_date_raw else None,
                        "match_phase": match_phase,
                        "match": f"{home_team} vs {away_team}",
                        "home_team": home_team,
                        "away_team": away_team,
                        "league": league_name,
                        "market": market_type,
                        "selection": selection_label,
                        "odds": round(odds, 2),
                        "model_probability": round(raw_prob, 3),
                        "conservative_probability": round(cons_prob, 3),
                        "calibration_method": "wilson_lower_bound",
                        "confidence_level": 0.90,
                        "implied_probability": round(imp_prob, 3),
                        "conservative_edge": round(edge, 3),
                        "edge_pct": round(edge * 100, 1),
                        "sample_size": sample_size,
                        "hierarchy_level": hier,
                        "is_settled": is_settled,
                        "result": res_str,
                        "unit_pnl": unit_pnl if is_settled else None,
                        "analysis_url": f"https://fixturecast.com/match/{fixture_id}",
                        "rationale": f"Cleared conservative probability ({round(cons_prob * 100, 1)}%) and edge criteria (+{round(edge * 100, 1)}%) vs market ({round(imp_prob * 100, 1)}%). Sample size: {sample_size} historical observations.",
                    }

        if not qualified_single:
            if freeze_status == "pending":
                qualified_single = {
                    "has_pick": False,
                    "date": today_str,
                    "reason": "Today's pre-kickoff qualification freeze is pending.",
                }
            else:
                qualified_single = {
                    "has_pick": False,
                    "date": today_str,
                    "reason": "No single selection cleared our conservative probability and edge qualification criteria.",
                }

        # =========================================================================
        # 2. READ FROZEN DAILY ACCA (READ-ONLY)
        # =========================================================================
        cursor.execute(
            f"""
            SELECT accumulator_id, selected_at, status
            FROM daily_featured_picks
            WHERE {date_filter_feat} AND kind = 'acca'
            LIMIT 1
            """,
            (today_str,),
        )
        featured_acca = cursor.fetchone()

        qualified_acca = None
        if featured_acca:
            def _get_fa(r, key, idx):
                return r[key] if isinstance(r, dict) or hasattr(r, "keys") else r[idx]
            frozen_a_id = _get_fa(featured_acca, "accumulator_id", 0)

            if frozen_a_id:
                cursor.execute(
                    """
                    SELECT id, date, acca_type, total_odds, stake, potential_return,
                           status, result, won, is_qualified_acca, qualifier_version
                    FROM accumulators
                    WHERE id = %s
                    """ if USE_POSTGRES else
                    """
                    SELECT id, date, acca_type, total_odds, stake, potential_return,
                           status, result, won, is_qualified_acca, qualifier_version
                    FROM accumulators
                    WHERE id = ?
                    """,
                    (frozen_a_id,),
                )
                acca_row = cursor.fetchone()
                if acca_row:
                    def _get_a(r, key, idx):
                        return r[key] if isinstance(r, dict) or hasattr(r, "keys") else r[idx]

                    acca_id = _get_a(acca_row, "id", 0)
                    acca_date = str(_get_a(acca_row, "date", 1))
                    acca_type = _get_a(acca_row, "acca_type", 2)
                    total_odds = _to_float(_get_a(acca_row, "total_odds", 3), 1.0)
                    status = _get_a(acca_row, "status", 6)
                    is_won = bool(_get_a(acca_row, "won", 8) or 0)
                    qualifier_ver = _get_a(acca_row, "qualifier_version", 10) or "v1.0-wilson-market"

                    # Query legs
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
                            "fixture_id": _get_s(sel, "fixture_id", 0),
                            "match": f"{_get_s(sel, 'home_team', 1)} vs {_get_s(sel, 'away_team', 2)}",
                            "league": _get_s(sel, "league_name", 3),
                            "selection": f"{_get_s(sel, 'selection_type', 4)}: {_get_s(sel, 'selection_value', 5)}",
                            "odds": round(_to_float(_get_s(sel, "odds", 6)), 2),
                            "model_probability": round(_to_float(raw_p or _get_s(sel, "confidence", 7)), 3) if (raw_p is not None or _get_s(sel, "confidence", 7) is not None) else None,
                            "conservative_probability": round(_to_float(cons_p), 3) if cons_p is not None else None,
                            "calibration_method": "wilson_lower_bound",
                            "confidence_level": 0.90,
                            "implied_probability": round(_to_float(imp_p), 3) if imp_p is not None else None,
                            "conservative_edge": round(_to_float(edg), 3) if edg is not None else None,
                            "sample_size": int(ss) if ss is not None else None,
                            "hierarchy_level": hier,
                            "won": bool(_get_s(sel, "won", 9) or 0) if status == "settled" else None,
                        })

                    qualified_acca = {
                        "has_pick": True,
                        "daily_acca_frozen": True,
                        "id": acca_id,
                        "date": acca_date,
                        "acca_type": acca_type,
                        "total_odds": round(total_odds, 2),
                        "legs_count": len(legs),
                        "legs": legs,
                        "qualifier_version": qualifier_ver,
                        "status": status,
                        "is_settled": status == "settled",
                        "result": "WON" if is_won else ("LOST" if status == "settled" else "PENDING"),
                    }

        if not qualified_acca:
            if freeze_status == "pending":
                qualified_acca = {
                    "has_pick": False,
                    "date": today_str,
                    "reason": "Today's pre-kickoff accumulator freeze is pending.",
                }
            else:
                qualified_acca = {
                    "has_pick": False,
                    "date": today_str,
                    "reason": "No 4-fold accumulator passed all individual leg checks and combined qualification criteria.",
                }

        # =========================================================================
        # 3. VERIFIED TRACK RECORD SUMMARY
        # =========================================================================
        track_record = generate_track_record(db_conn=conn, start_date="2026-08-20")
        tr_summary = track_record.get("summary", {})

        # =========================================================================
        # 4. LIFECYCLE-AWARE SOCIAL CONTENT DRAFTS (READ-ONLY)
        # =========================================================================
        social_drafts = _generate_social_content_drafts(
            today_str=today_str,
            freeze_status=freeze_status,
            single=qualified_single,
            acca=qualified_acca,
            track_record=track_record,
        )

        return {
            "date": today_str,
            "freeze_status": freeze_status,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "publishing_approval_required": True,
            "single": qualified_single,
            "acca": qualified_acca,
            "track_record_summary": {
                "launch_date": "2026-08-20",
                "total_bets": tr_summary.get("total_bets", 0),
                "win_rate_pct": tr_summary.get("win_rate_pct", 0.0),
                "profit_units": tr_summary.get("profit_units", 0.0),
                "roi_pct": tr_summary.get("roi_pct", 0.0),
                "verified_url": "https://fixturecast.com/track-record",
            },
            "social_drafts": social_drafts,
        }
    finally:
        if conn_context:
            conn_context.__exit__(None, None, None)


def _generate_social_content_drafts(
    today_str: str,
    freeze_status: str,
    single: Dict[str, Any],
    acca: Dict[str, Any],
    track_record: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Builds lifecycle-aware social copy, platform-specific UTM links with Content IDs,
    and structured props for the existing Remotion renderer.
    """
    date_clean = today_str.replace("-", "")
    tr_sum = track_record.get("summary", {})
    tr_units = tr_sum.get("profit_units", 0.0)
    tr_roi = tr_sum.get("roi_pct", 0.0)
    tr_wins = tr_sum.get("won", 0)
    tr_total = tr_sum.get("total_bets", 0)

    has_pick = single.get("has_pick")
    phase = "PENDING_FREEZE" if freeze_status == "pending" else (single.get("match_phase") if has_pick else "NO_PICK")

    # Content IDs
    cid_single = f"fc_{date_clean}_single_v1"
    cid_acca = f"fc_{date_clean}_acca_v1"
    cid_nopick = f"fc_{date_clean}_nopick_v1"
    cid_result = f"fc_{date_clean}_result_v1"
    cid_active = cid_single if (has_pick and phase == "UPCOMING") else (cid_result if (has_pick and phase == "SETTLED") else cid_nopick)

    # Build platform-specific trackable links
    def _utm_link(platform: str, medium: str, content_id: str) -> str:
        return f"https://fixturecast.com/today?utm_source={platform}&utm_medium={medium}&utm_campaign=daily_pick&utm_content={content_id}"

    platform_links = {
        "tiktok": _utm_link("tiktok", "video", cid_active),
        "instagram": _utm_link("instagram", "reels", cid_active),
        "youtube": _utm_link("youtube", "profile", cid_active),
        "x": _utm_link("x", "post", cid_active),
    }

    pre_match_post = None
    result_post = None
    video_prompt_data = None
    remotion_video_props = None
    posts_by_platform = {}
    no_pick_post = None

    if freeze_status == "pending":
        # Freeze has not yet executed for today: suppress marketing and abstention copy
        pre_match_post = None
        posts_by_platform = {}
        video_prompt_data = None
        remotion_video_props = None

    elif has_pick:
        match_name = single["match"]
        selection = single["selection"]
        odds = single["odds"]
        edge_pct = single["edge_pct"]
        cons_pct = round(single["conservative_probability"] * 100, 1)
        raw_prob_pct = round((single.get("model_probability") or 0.5) * 100, 1)
        league = single.get("league", "Football")

        if phase == "UPCOMING":
            posts_by_platform = {
                "x": (
                    f"🎯 Today's Qualified Single ({today_str})\n\n"
                    f"⚽ {match_name} ({league})\n"
                    f"📌 Selection: {selection} @ {odds}\n"
                    f"📊 Conservative Probability: {cons_pct}%\n"
                    f"⚡ Conservative Edge: +{edge_pct}%\n\n"
                    f"Logged pre-kickoff with zero backfill.\n"
                    f"Today's pick & verified record: {platform_links['x']}\n\n"
                    f"#FootballPredictions #ValueBetting #FixtureCast #SmartMarkets"
                ),
                "tiktok": (
                    f"Today's Qualified Single: {match_name} ⚽\n"
                    f"Selection: {selection} @ {odds}\n"
                    f"Conservative Edge: +{edge_pct}%\n\n"
                    f"Logged pre-kickoff on our public ledger. Zero backfill.\n"
                    f"🔗 Full match breakdown & live track record in bio!\n\n"
                    f"#footballbetting #sportsanalytics #fixturecast #valuebetting"
                ),
                "instagram": (
                    f"🎯 Today's Qualified Single ({today_str})\n\n"
                    f"⚽ {match_name} ({league})\n"
                    f"📌 Selection: {selection} @ {odds}\n"
                    f"📊 Conservative Model Estimate: {cons_pct}%\n"
                    f"⚡ Conservative Edge: +{edge_pct}%\n\n"
                    f"Logged pre-kickoff with zero backfill.\n"
                    f"🔗 Link in bio to audit our verified forward ledger.\n\n"
                    f"#FootballTips #SportsAnalytics #ValueBetting #FixtureCast"
                ),
                "youtube": (
                    f"Today's Qualified Single: {match_name} ({selection} @ {odds})\n\n"
                    f"Conservative Probability: {cons_pct}%\n"
                    f"Model-Market Conservative Edge: +{edge_pct}%\n\n"
                    f"🔗 Full breakdown and verified forward record via the channel link.\n\n"
                    f"#Shorts #FootballPredictions #FixtureCast"
                ),
            }
            pre_match_post = posts_by_platform["x"]

            video_prompt_data = {
                "aspect_ratio": "9:16",
                "template": "FixturecastDailyPick",
                "content_id": cid_single,
                "theme": "dark_modern",
                "title": "Today's Qualified Single",
                "date": today_str,
                "badge": "IMMUTABLE PRE-KICKOFF RECORD",
                "match": match_name,
                "league": league,
                "selection": selection,
                "odds": odds,
                "edge": f"+{edge_pct}%",
                "conservative_prob": f"{cons_pct}%",
                "track_record_badge": f"Verified Record: {tr_units:+.2f}u ({tr_roi:+.1f}% ROI)",
                "cta_url": "fixturecast.com/today",
            }

            remotion_video_props = {
                "template": "FixturecastDailyPick",
                "durationInSeconds": 15,
                "props": {
                    "date": today_str,
                    "contentId": cid_single,
                    "match": match_name,
                    "league": league,
                    "selection": selection,
                    "odds": odds,
                    "conservativeProb": cons_pct,
                    "rawProb": raw_prob_pct,
                    "conservativeEdge": edge_pct,
                    "sampleSize": single.get("sample_size", 0),
                    "trackRecordBadge": f"{tr_units:+.2f}u ({tr_roi:+.1f}% ROI)",
                    "cta": "fixturecast.com/today",
                },
            }
        elif phase == "SETTLED":
            res_str = single.get("result", "SETTLED")
            unit_pnl = single.get("unit_pnl", 0.0)
            pnl_symbol = "+" if unit_pnl >= 0 else ""
            posts_by_platform = {
                "x": (
                    f"📊 Result Update: Today's Qualified Single ({today_str})\n\n"
                    f"⚽ {match_name}\n"
                    f"📌 Selection: {selection} @ {odds}\n"
                    f"🏁 Outcome: {res_str} ({pnl_symbol}{unit_pnl:.2f}u)\n\n"
                    f"Updated Forward Record: {tr_total} bets | {tr_units:+.2f}u ({tr_roi:+.1f}% ROI)\n"
                    f"Full public ledger: {platform_links['x']}\n\n"
                    f"#FixtureCast #TransparentRecord #SportsAnalytics"
                ),
                "tiktok": (
                    f"Result Update: {match_name} 🏁\n"
                    f"Selection: {selection} @ {odds} → {res_str} ({pnl_symbol}{unit_pnl:.2f}u)\n\n"
                    f"Cumulative Record: {tr_units:+.2f}u ({tr_roi:+.1f}% ROI)\n"
                    f"🔗 Full public track record in bio!\n\n"
                    f"#footballbetting #fixturecast #sportsanalytics"
                ),
                "instagram": (
                    f"📊 Pick Result Update ({today_str})\n\n"
                    f"⚽ {match_name}\n"
                    f"📌 {selection} @ {odds} → {res_str} ({pnl_symbol}{unit_pnl:.2f}u)\n\n"
                    f"Updated Ledger: {tr_total} bets | {tr_units:+.2f}u ({tr_roi:+.1f}% ROI)\n"
                    f"🔗 Link in bio to audit our forward record.\n\n"
                    f"#FixtureCast #TransparentRecord"
                ),
                "youtube": (
                    f"Pick Result: {match_name} → {res_str} ({pnl_symbol}{unit_pnl:.2f}u)\n\n"
                    f"Updated Forward Record: {tr_total} bets | {tr_units:+.2f}u ({tr_roi:+.1f}% ROI)\n"
                    f"🔗 Full ledger via the channel link."
                ),
            }
            result_post = posts_by_platform["x"]
            remotion_video_props = {
                "template": "FixturecastResult",
                "durationInSeconds": 12,
                "props": {
                    "date": today_str,
                    "contentId": cid_result,
                    "match": match_name,
                    "selection": selection,
                    "odds": odds,
                    "outcome": res_str,
                    "unitPnl": f"{pnl_symbol}{unit_pnl:.2f}u",
                    "totalPnl": f"{tr_units:+.2f}u",
                    "roi": f"{tr_roi:+.1f}%",
                    "cta": "fixturecast.com/today",
                },
            }
        elif phase == "LIVE":
            posts_by_platform = {}
            pre_match_post = None

    else:
        # Explicit Completed Abstention / No-Pick State
        posts_by_platform = {
            "x": (
                f"🛡️ FixtureCast Daily Update ({today_str})\n\n"
                f"No selection cleared today's qualification criteria. We abstain rather than force a pick.\n\n"
                f"Verified forward record: {platform_links['x']}\n\n"
                f"#FixtureCast #DisciplinedBetting #Transparency"
            ),
            "tiktok": (
                f"🛡️ FixtureCast Daily Update ({today_str})\n\n"
                f"No selection cleared today's qualification criteria. We abstain rather than force a pick.\n\n"
                f"🔗 Audit our verified forward record in bio!\n\n"
                f"#sportsanalytics #footballbetting #fixturecast"
            ),
            "instagram": (
                f"🛡️ FixtureCast Daily Update ({today_str})\n\n"
                f"No selection cleared today's qualification criteria. We abstain rather than force a pick.\n\n"
                f"🔗 Link in bio to audit our verified forward ledger.\n\n"
                f"#FixtureCast #DisciplinedBetting #SportsAnalytics"
            ),
            "youtube": (
                f"🛡️ FixtureCast Daily Update: No Selection Today ({today_str})\n\n"
                f"No selection cleared today's qualification criteria. We abstain rather than force a pick.\n\n"
                f"🔗 Full verified forward record via the channel link."
            ),
        }
        pre_match_post = posts_by_platform["x"]
        video_prompt_data = {
            "aspect_ratio": "9:16",
            "template": "FixturecastNoPick",
            "content_id": cid_nopick,
            "theme": "dark_modern",
            "title": "Disciplined Value: No Selection Today",
            "date": today_str,
            "badge": "DISCIPLINED SELECTION",
            "match": "Board Scanned: No Qualified Pick",
            "selection": "Abstain",
            "odds": None,
            "edge": "0.0%",
            "conservative_prob": None,
            "track_record_badge": f"Verified Record: {tr_units:+.2f}u ({tr_roi:+.1f}% ROI)",
            "cta_url": "fixturecast.com/today",
        }
        remotion_video_props = {
            "template": "FixturecastNoPick",
            "durationInSeconds": 12,
            "props": {
                "date": today_str,
                "contentId": cid_nopick,
                "headline": "No Selection Today",
                "explanation": "No selection cleared today's qualification criteria. We abstain rather than force a pick.",
                "trackRecordBadge": f"{tr_units:+.2f}u ({tr_roi:+.1f}% ROI)",
                "cta": "fixturecast.com/today",
            },
        }

        no_pick_post = (
            f"Why FixtureCast says 'No Pick Today' ({today_str}):\n\n"
            f"No selection cleared today's qualification criteria. We abstain rather than force a pick.\n\n"
            f"100% transparent forward record: {platform_links['x']}"
        )

    weekly_recap_post = (
        f"📈 FixtureCast Verified Forward Record Update\n\n"
        f"• Tracking Since: 20 Aug 2026\n"
        f"• Settled Picks: {tr_total}\n"
        f"• Wins: {tr_wins}\n"
        f"• Cumulative P&L: {tr_units:+.2f} units\n"
        f"• Yield / ROI: {tr_roi:+.1f}%\n\n"
        f"Every pre-kickoff pick is recorded and public. No deletions, no backfilling.\n\n"
        f"Full ledger: {platform_links['x']}"
    )

    bio_links = {
        "tiktok": "https://fixturecast.com/today?utm_source=tiktok&utm_medium=bio&utm_campaign=daily_pick",
        "instagram": "https://fixturecast.com/today?utm_source=instagram&utm_medium=bio&utm_campaign=daily_pick",
        "youtube": "https://fixturecast.com/today?utm_source=youtube&utm_medium=profile&utm_campaign=daily_pick",
    }

    return {
        "match_phase": phase,
        "content_id": cid_active,
        "content_ids": {
            "single": cid_single,
            "acca": cid_acca,
            "no_pick": cid_nopick,
            "result": cid_result,
        },
        "platform_links": platform_links,
        "bio_links": bio_links,
        "posts_by_platform": posts_by_platform,
        "pre_match_post": pre_match_post,
        "result_post": result_post,
        "no_pick_post": no_pick_post,
        "weekly_recap_post": weekly_recap_post,
        "video_prompt_data": video_prompt_data,
        "remotion_video_props": remotion_video_props,
        "cta_url": f"https://fixturecast.com/today?utm_content={cid_active}",
    }
