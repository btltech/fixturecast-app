"""
Calibration Layer for FixtureCast.

Provides conservative probability estimation using historical calibration records,
market-implied probability banding, smooth neighborhood weighting, and Wilson score
lower bound confidence intervals.

Prevents false-edge claims where a high model confidence contradicts market consensus
without sufficient empirical backing in that specific odds/confidence profile.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class CalibratedEstimate:
    conservative_probability: float | None
    observed_hit_rate: float | None
    sample_size: int
    confidence_band: str
    implied_band: str
    hierarchy_level: str  # "league_specific" | "cross_league_price_matched" | "cross_league_unmatched" | "insufficient_data"
    raw_probability: float
    implied_probability: float | None


def wilson_lower_bound(hits: int | float, total: int | float, z: float = 1.645) -> float:
    """
    Computes the lower bound of the Wilson score interval for a Bernoulli parameter.
    
    Default z = 1.645 corresponds to a 90% one-tailed (or 90% coverage two-tailed ~95%)
    conservative confidence level.
    """
    if total <= 0:
        return 0.0
    
    hits = max(0.0, min(float(hits), float(total)))
    n = float(total)
    p_hat = hits / n
    z2 = z * z
    
    denominator = 1.0 + (z2 / n)
    center = p_hat + (z2 / (2.0 * n))
    spread = z * math.sqrt((p_hat * (1.0 - p_hat) / n) + (z2 / (4.0 * n * n)))
    
    lower = (center - spread) / denominator
    return max(0.0, min(1.0, lower))


def get_confidence_band(prob: float) -> str:
    """Classifies model probability into a standardized bucket."""
    p = max(0.0, min(1.0, float(prob)))
    if p < 0.50:
        return "<0.50"
    elif p < 0.55:
        return "0.50-0.55"
    elif p < 0.60:
        return "0.55-0.60"
    elif p < 0.65:
        return "0.60-0.65"
    elif p < 0.70:
        return "0.65-0.70"
    elif p < 0.75:
        return "0.70-0.75"
    elif p < 0.80:
        return "0.75-0.80"
    else:
        return "0.80+"


def get_implied_band(implied_prob: float | None) -> str:
    """Classifies market-implied probability into a standardized price bucket."""
    if implied_prob is None:
        return "none"
    p = max(0.0, min(1.0, float(implied_prob)))
    if p < 0.25:
        return "<0.25"
    elif p < 0.35:
        return "0.25-0.35"
    elif p < 0.45:
        return "0.35-0.45"
    elif p < 0.55:
        return "0.45-0.55"
    elif p < 0.65:
        return "0.55-0.65"
    elif p < 0.75:
        return "0.65-0.75"
    else:
        return "0.75+"


def smooth_bucket_statistics(
    buckets: List[Dict[str, Any]],
    target_raw_prob: float,
    target_implied_prob: float | None,
    bandwidth_conf: float = 0.08,
    bandwidth_implied: float = 0.10,
) -> Tuple[float, int]:
    """
    Computes smoothed effective hits and effective sample size across calibration observations
    using Gaussian kernel distance weights to avoid hard bin cliffs.
    
    Each bucket in `buckets` is expected to have:
    - raw_prob_center (or raw_prob): float
    - implied_prob_center (or implied_prob): float | None
    - hits: int | float
    - total: int
    """
    total_effective_weight = 0.0
    effective_hits = 0.0
    raw_sample_count = 0

    for b in buckets:
        n = b.get("total", 0)
        if n <= 0:
            continue
        raw_sample_count += n
        h = b.get("hits", 0)
        p_center = b.get("raw_prob_center", b.get("raw_prob", target_raw_prob))
        
        # Distance on confidence dimension
        d_conf = (p_center - target_raw_prob) / bandwidth_conf
        w = math.exp(-0.5 * (d_conf * d_conf))
        
        # Distance on market-implied dimension if both target and bucket provide price context
        imp_center = b.get("implied_prob_center", b.get("implied_prob", None))
        if target_implied_prob is not None and imp_center is not None:
            d_imp = (imp_center - target_implied_prob) / bandwidth_implied
            w *= math.exp(-0.5 * (d_imp * d_imp))
        
        effective_weight = w * n
        total_effective_weight += effective_weight
        effective_hits += w * h

    if total_effective_weight <= 0:
        return 0.0, 0

    smoothed_hit_rate = effective_hits / total_effective_weight
    return smoothed_hit_rate, raw_sample_count


class CalibrationLayer:
    """
    Queries and manages historical prediction calibration records.
    Supports in-memory test fixtures and live DB connections with caching.
    """

    def __init__(self, db_records: Optional[List[Dict[str, Any]]] = None, cache_ttl_seconds: float = 300.0):
        self._custom_records = db_records
        self._cache: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
        self._cache_ttl = cache_ttl_seconds

    def query_calibration_records(
        self,
        market_type: str,
        league_id: Optional[int] = None,
        db_conn: Any = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves resolved prediction records with actual hit/miss outcomes.
        Returns a list of dicts: [{'raw_prob': float, 'implied_prob': float, 'hit': int, 'league_id': int}]
        """
        import time

        if self._custom_records is not None:
            records = self._custom_records
            filtered = [r for r in records if r.get("market_type") == market_type]
            if league_id is not None:
                filtered_league = [r for r in filtered if r.get("league_id") == league_id]
                if len(filtered_league) >= 15:
                    return filtered_league
            return filtered

        # Check in-memory cache for market_type
        now = time.time()
        if market_type in self._cache:
            cache_time, cached_records = self._cache[market_type]
            if (now - cache_time) < self._cache_ttl:
                if league_id is not None:
                    filtered_league = [r for r in cached_records if r.get("league_id") == league_id]
                    if len(filtered_league) >= 15:
                        return filtered_league
                return cached_records

        # Live DB query
        try:
            try:
                from backend.database import USE_POSTGRES, get_db
            except ImportError:
                from database import USE_POSTGRES, get_db

            conn_context = None
            if db_conn is None:
                conn_context = get_db()
                conn = conn_context.__enter__()
            else:
                conn = db_conn

            cursor = conn.cursor()
            
            # Map market_type to prediction column and odds column
            if market_type in ("home_win", "draw", "away_win", "1x2"):
                # Query 1X2 evaluated rows
                cursor.execute(
                    """
                    SELECT home_win_prob, draw_prob, away_win_prob,
                           odds_home_win, odds_draw, odds_away_win,
                           predicted_outcome, actual_outcome, league_id
                    FROM predictions
                    WHERE evaluated = 1 AND actual_outcome IS NOT NULL
                      AND odds_home_win > 0 AND odds_draw > 0 AND odds_away_win > 0
                    """
                )
                rows = cursor.fetchall()
                results = []
                for row in rows:
                    def _get_val(r, key, idx):
                        return r[key] if isinstance(r, dict) or hasattr(r, "keys") else r[idx]
                    
                    actual = _get_val(row, "actual_outcome", 7)
                    lid = _get_val(row, "league_id", 8)
                    oh = float(_get_val(row, "odds_home_win", 3) or 0)
                    od = float(_get_val(row, "odds_draw", 4) or 0)
                    oa = float(_get_val(row, "odds_away_win", 5) or 0)
                    
                    if oh <= 1.0 or od <= 1.0 or oa <= 1.0:
                        continue
                    
                    margin = (1.0 / oh) + (1.0 / od) + (1.0 / oa)
                    if margin <= 0:
                        continue
                    
                    imp_h = (1.0 / oh) / margin
                    imp_d = (1.0 / od) / margin
                    imp_a = (1.0 / oa) / margin
                    
                    ph = float(_get_val(row, "home_win_prob", 0) or 0)
                    pd = float(_get_val(row, "draw_prob", 1) or 0)
                    pa = float(_get_val(row, "away_win_prob", 2) or 0)
                    
                    if market_type in ("home_win", "1x2"):
                        results.append({
                            "raw_prob": ph,
                            "implied_prob": imp_h,
                            "hit": 1 if actual in ("HOME_WIN", "home", "1") else 0,
                            "league_id": lid,
                        })
                    elif market_type == "draw":
                        results.append({
                            "raw_prob": pd,
                            "implied_prob": imp_d,
                            "hit": 1 if actual in ("DRAW", "draw", "X") else 0,
                            "league_id": lid,
                        })
                    elif market_type == "away_win":
                        results.append({
                            "raw_prob": pa,
                            "implied_prob": imp_a,
                            "hit": 1 if actual in ("AWAY_WIN", "away", "2") else 0,
                            "league_id": lid,
                        })
                
                if conn_context:
                    conn_context.__exit__(None, None, None)
                self._cache[market_type] = (now, results)
                if league_id is not None:
                    filtered_league = [r for r in results if r.get("league_id") == league_id]
                    if len(filtered_league) >= 15:
                        return filtered_league
                return results

            elif market_type in ("over25", "under25"):
                cursor.execute(
                    """
                    SELECT over25_prob, odds_over_25, odds_under_25,
                           actual_home_goals, actual_away_goals, league_id
                    FROM predictions
                    WHERE evaluated = 1 AND actual_home_goals IS NOT NULL AND actual_away_goals IS NOT NULL
                      AND odds_over_25 > 0 AND odds_under_25 > 0
                    """
                )
                rows = cursor.fetchall()
                results = []
                for row in rows:
                    def _get_val(r, key, idx):
                        return r[key] if isinstance(r, dict) or hasattr(r, "keys") else r[idx]
                    
                    hg = _get_val(row, "actual_home_goals", 3)
                    ag = _get_val(row, "actual_away_goals", 4)
                    lid = _get_val(row, "league_id", 5)
                    o_over = float(_get_val(row, "odds_over_25", 1) or 0)
                    o_under = float(_get_val(row, "odds_under_25", 2) or 0)
                    
                    if o_over <= 1.0 or o_under <= 1.0:
                        continue
                    
                    margin = (1.0 / o_over) + (1.0 / o_under)
                    imp_over = (1.0 / o_over) / margin
                    prob_over = float(_get_val(row, "over25_prob", 0) or 0)
                    is_over = 1 if (hg + ag) > 2.5 else 0
                    
                    if market_type == "over25":
                        results.append({
                            "raw_prob": prob_over,
                            "implied_prob": imp_over,
                            "hit": is_over,
                            "league_id": lid,
                        })
                    else:
                        results.append({
                            "raw_prob": 1.0 - prob_over,
                            "implied_prob": 1.0 - imp_over,
                            "hit": 1 - is_over,
                            "league_id": lid,
                        })
                
                if conn_context:
                    conn_context.__exit__(None, None, None)
                self._cache[market_type] = (now, results)
                if league_id is not None:
                    filtered_league = [r for r in results if r.get("league_id") == league_id]
                    if len(filtered_league) >= 15:
                        return filtered_league
                return results

            elif market_type == "btts":
                cursor.execute(
                    """
                    SELECT btts_prob, odds_btts_yes, odds_btts_no,
                           actual_home_goals, actual_away_goals, league_id
                    FROM predictions
                    WHERE evaluated = 1 AND actual_home_goals IS NOT NULL AND actual_away_goals IS NOT NULL
                      AND odds_btts_yes > 0 AND odds_btts_no > 0
                    """
                )
                rows = cursor.fetchall()
                results = []
                for row in rows:
                    def _get_val(r, key, idx):
                        return r[key] if isinstance(r, dict) or hasattr(r, "keys") else r[idx]
                    
                    hg = _get_val(row, "actual_home_goals", 3)
                    ag = _get_val(row, "actual_away_goals", 4)
                    lid = _get_val(row, "league_id", 5)
                    o_yes = float(_get_val(row, "odds_btts_yes", 1) or 0)
                    o_no = float(_get_val(row, "odds_btts_no", 2) or 0)
                    
                    if o_yes <= 1.0 or o_no <= 1.0:
                        continue
                    
                    margin = (1.0 / o_yes) + (1.0 / o_no)
                    imp_yes = (1.0 / o_yes) / margin
                    prob_btts = float(_get_val(row, "btts_prob", 0) or 0)
                    is_btts = 1 if (hg > 0 and ag > 0) else 0
                    
                    results.append({
                        "raw_prob": prob_btts,
                        "implied_prob": imp_yes,
                        "hit": is_btts,
                        "league_id": lid,
                    })
                
                if conn_context:
                    conn_context.__exit__(None, None, None)
                self._cache[market_type] = (now, results)
                if league_id is not None:
                    filtered_league = [r for r in results if r.get("league_id") == league_id]
                    if len(filtered_league) >= 15:
                        return filtered_league
                return results

        except Exception as e:
            # If DB unavailable or empty, fail gracefully
            pass

        return []

    def get_conservative_estimate(
        self,
        raw_prob: float,
        implied_prob: Optional[float],
        market_type: str,
        league_id: Optional[int] = None,
        min_sample_size: int = 30,
        db_conn: Any = None,
    ) -> CalibratedEstimate:
        """
        Calculates the conservative probability using the 4-level hierarchical fallback:
        
        1. (market, conf_band, implied_band, league_id) [>= min_sample_size]
        2. (market, conf_band, implied_band)           [>= min_sample_size]
        3. (market, conf_band)                         [>= min_sample_size]
        4. Insufficient sample -> conservative_probability = None
        """
        conf_band = get_confidence_band(raw_prob)
        imp_band = get_implied_band(implied_prob)

        records = self.query_calibration_records(market_type, league_id=league_id, db_conn=db_conn)

        if not records:
            return CalibratedEstimate(
                conservative_probability=None,
                observed_hit_rate=None,
                sample_size=0,
                confidence_band=conf_band,
                implied_band=imp_band,
                hierarchy_level="insufficient_data",
                raw_probability=raw_prob,
                implied_probability=implied_prob,
            )

        # Hierarchy Level 1: League + Market + Implied Band Matched
        if league_id is not None and implied_prob is not None:
            l1_records = [
                r for r in records
                if r.get("league_id") == league_id
                and abs(r.get("implied_prob", 0) - implied_prob) <= 0.15
            ]
            if len(l1_records) >= min_sample_size:
                hit_rate, sample_n = smooth_bucket_statistics(
                    [{"raw_prob": r["raw_prob"], "implied_prob": r["implied_prob"], "hits": r["hit"], "total": 1} for r in l1_records],
                    target_raw_prob=raw_prob,
                    target_implied_prob=implied_prob,
                )
                conservative_p = wilson_lower_bound(hit_rate * sample_n, sample_n)
                return CalibratedEstimate(
                    conservative_probability=round(conservative_p, 4),
                    observed_hit_rate=round(hit_rate, 4),
                    sample_size=sample_n,
                    confidence_band=conf_band,
                    implied_band=imp_band,
                    hierarchy_level="league_specific",
                    raw_probability=raw_prob,
                    implied_probability=implied_prob,
                )

        # Hierarchy Level 2: Cross-League + Price-Matched (Implied Band)
        if implied_prob is not None:
            l2_records = [
                r for r in records
                if abs(r.get("implied_prob", 0) - implied_prob) <= 0.15
            ]
            if len(l2_records) >= min_sample_size:
                hit_rate, sample_n = smooth_bucket_statistics(
                    [{"raw_prob": r["raw_prob"], "implied_prob": r["implied_prob"], "hits": r["hit"], "total": 1} for r in l2_records],
                    target_raw_prob=raw_prob,
                    target_implied_prob=implied_prob,
                )
                conservative_p = wilson_lower_bound(hit_rate * sample_n, sample_n)
                return CalibratedEstimate(
                    conservative_probability=round(conservative_p, 4),
                    observed_hit_rate=round(hit_rate, 4),
                    sample_size=sample_n,
                    confidence_band=conf_band,
                    implied_band=imp_band,
                    hierarchy_level="cross_league_price_matched",
                    raw_probability=raw_prob,
                    implied_probability=implied_prob,
                )

        # Hierarchy Level 3: Cross-League + Confidence Band only
        l3_records = [
            r for r in records
            if abs(r.get("raw_prob", 0) - raw_prob) <= 0.10
        ]
        if len(l3_records) >= min_sample_size:
            hit_rate, sample_n = smooth_bucket_statistics(
                [{"raw_prob": r["raw_prob"], "implied_prob": r.get("implied_prob"), "hits": r["hit"], "total": 1} for r in l3_records],
                target_raw_prob=raw_prob,
                target_implied_prob=implied_prob,
            )
            conservative_p = wilson_lower_bound(hit_rate * sample_n, sample_n)
            return CalibratedEstimate(
                conservative_probability=round(conservative_p, 4),
                observed_hit_rate=round(hit_rate, 4),
                sample_size=sample_n,
                confidence_band=conf_band,
                implied_band=imp_band,
                hierarchy_level="cross_league_unmatched",
                raw_probability=raw_prob,
                implied_probability=implied_prob,
            )

        # Level 4: Insufficient sample across all levels -> Fail-Closed
        return CalibratedEstimate(
            conservative_probability=None,
            observed_hit_rate=None,
            sample_size=len(records),
            confidence_band=conf_band,
            implied_band=imp_band,
            hierarchy_level="insufficient_data",
            raw_probability=raw_prob,
            implied_probability=implied_prob,
        )


_default_calibration_layer: Optional[CalibrationLayer] = None


def get_calibration_layer() -> CalibrationLayer:
    """Returns singleton CalibrationLayer instance."""
    global _default_calibration_layer
    if _default_calibration_layer is None:
        _default_calibration_layer = CalibrationLayer()
    return _default_calibration_layer
