"""
Daily Accumulator Generator
Generates 8-fold, 4-fold, and BTTS accumulators based on ML predictions
"""

import os
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List

try:
    from .league_catalog import get_featured_league_ids
except ImportError:
    from league_catalog import get_featured_league_ids


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _normalize_1x2_outcome(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()

    if text in {"home", "h", "1", "home win", "homewin"}:
        return "home"
    if text in {"away", "a", "2", "away win", "awaywin"}:
        return "away"
    if text in {"draw", "d", "x", "tie"}:
        return "draw"

    return None


def _get_env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return float(default)


def _get_env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return int(default)


def _get_env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return bool(default)
    text = str(value).strip().lower()
    if text in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "f", "no", "n", "off"}:
        return False
    return bool(default)


class AccumulatorGenerator:
    """Generates daily accumulator bets from predictions"""

    EDGE_MARGIN = float(os.getenv("EDGE_MARGIN", "0.02"))

    # Featured leagues for diversity
    FEATURED_LEAGUES = set(get_featured_league_ids())

    # European competitions with less historical data (lower thresholds)
    EUROPEAN_COMPETITIONS = {2, 3, 848}  # Champions League, Europa League, Conference League
    RISK_LEVELS = {
        "8-fold": "high",
        "6-fold": "high",
        "4-fold": "medium",
        "BTTS": "medium",
    }

    def __init__(self):
        self.eight_fold_min_conf = _get_env_float("ACCA_8_FOLD_MIN_CONF", 60.0)
        self.eight_fold_max_conf = _get_env_float("ACCA_8_FOLD_MAX_CONF", 75.0)
        self.six_fold_min_conf = _get_env_float("ACCA_6_FOLD_MIN_CONF", 60.0)
        self.six_fold_max_conf = _get_env_float("ACCA_6_FOLD_MAX_CONF", 75.0)
        self.four_fold_min_conf = _get_env_float("ACCA_4_FOLD_MIN_CONF", 70.0)
        self.four_fold_max_conf = _get_env_float("ACCA_4_FOLD_MAX_CONF", 85.0)
        self.btts_min_prob = _get_env_float("ACCA_BTTS_MIN_PROB", 65.0)
        self.btts_count = max(1, _get_env_int("ACCA_BTTS_COUNT", 5))

        # Improvements
        # Exclude draws by default for 1X2 accumulator legs (more stable than needing a draw).
        self.exclude_draws = _get_env_bool("ACCA_EXCLUDE_DRAWS", True)

        # Adaptive fallback widens confidence band (still requires edge/value) when
        # there are not enough eligible matches to fill an acca.
        self.adaptive_fallback = _get_env_bool("ACCA_ADAPTIVE_FALLBACK", True)
        self.fallback_band_step = _get_env_float("ACCA_FALLBACK_BAND_STEP", 5.0)
        self.fallback_band_floor = _get_env_float("ACCA_FALLBACK_BAND_FLOOR", 50.0)
        self.fallback_band_ceiling = _get_env_float("ACCA_FALLBACK_BAND_CEILING", 90.0)

        if self.eight_fold_min_conf > self.eight_fold_max_conf:
            self.eight_fold_min_conf, self.eight_fold_max_conf = (
                self.eight_fold_max_conf,
                self.eight_fold_min_conf,
            )
        if self.six_fold_min_conf > self.six_fold_max_conf:
            self.six_fold_min_conf, self.six_fold_max_conf = (
                self.six_fold_max_conf,
                self.six_fold_min_conf,
            )
        if self.four_fold_min_conf > self.four_fold_max_conf:
            self.four_fold_min_conf, self.four_fold_max_conf = (
                self.four_fold_max_conf,
                self.four_fold_min_conf,
            )

    def generate_8_fold(self, predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate 8-fold accumulator from solid predictions
        Target: configurable confidence range for balanced odds
        """
        # Filter predictions: confidence range, featured leagues, today's matches
        eligible = self._filter_predictions_adaptive(
            predictions,
            min_confidence=self.eight_fold_min_conf,
            max_confidence=self.eight_fold_max_conf,
            required_count=8,
        )

        # Select 8 matches with diversity (allow up to 3 per league; relax if needed)
        selections = self._select_diverse_matches(eligible, count=8, max_per_league=3)
        if self.adaptive_fallback and len(selections) < 8:
            selections = self._select_diverse_matches(eligible, count=8, max_per_league=4)

        if len(selections) < 8:
            return None

        # Build accumulator
        return self._build_accumulator(selections, acca_type="8-fold")

    def generate_6_fold(self, predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate 6-fold accumulator from solid predictions
        Target: configurable confidence range (fallback if 8-fold unavailable)
        """
        eligible = self._filter_predictions_adaptive(
            predictions,
            min_confidence=self.six_fold_min_conf,
            max_confidence=self.six_fold_max_conf,
            required_count=6,
        )
        selections = self._select_diverse_matches(eligible, count=6, max_per_league=3)
        if self.adaptive_fallback and len(selections) < 6:
            selections = self._select_diverse_matches(eligible, count=6, max_per_league=4)

        if len(selections) < 6:
            return None

        return self._build_accumulator(selections, acca_type="6-fold")

    def generate_4_fold(self, predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate 4-fold accumulator from high confidence predictions
        Target: configurable confidence range
        """
        eligible = self._filter_predictions_adaptive(
            predictions,
            min_confidence=self.four_fold_min_conf,
            max_confidence=self.four_fold_max_conf,
            required_count=4,
        )
        selections = self._select_diverse_matches(eligible, count=4, max_per_league=1)
        if self.adaptive_fallback and len(selections) < 4:
            selections = self._select_diverse_matches(eligible, count=4, max_per_league=2)

        if len(selections) < 4:
            return None

        return self._build_accumulator(selections, acca_type="4-fold")

    def generate_btts(self, predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate BTTS (Both Teams To Score) accumulator
        Target: configurable BTTS probability (all competitions), configurable count
        """
        # Filter for high BTTS probability with league-specific thresholds
        eligible = []
        for p in predictions:
            league_id = p.get("league_id")
            btts_prob = p.get("btts_probability", 0)

            min_threshold = self.btts_min_prob

            if (
                btts_prob > min_threshold
                and league_id in self.FEATURED_LEAGUES
                and self._is_today_or_tomorrow(p.get("match_date"))
                and self._passes_btts_edge(p, btts_prob / 100 if btts_prob > 1 else btts_prob)
            ):
                eligible.append(p)

        # Select requested count of matches
        count = self.btts_count
        selections = self._select_diverse_matches(eligible, count=count, max_per_league=2)

        if len(selections) < count:
            return None

        # Build BTTS selections
        btts_selections = []
        for sel in selections:
            btts_selections.append(
                {
                    "fixture_id": sel["fixture_id"],
                    "home_team": sel["home_team"],
                    "away_team": sel["away_team"],
                    "league_id": sel["league_id"],
                    "league_name": sel["league_name"],
                    "match_date": sel["match_date"],
                    "selection_type": "BTTS",
                    "selection_value": "Yes",
                    "odds": sel.get("btts_odds", 1.85),  # Default BTTS odds
                    "confidence": sel.get("btts_probability", 65),
                }
            )

        return self._build_accumulator(btts_selections, acca_type="BTTS")

    def _filter_predictions(
        self, predictions: List[Dict], min_confidence: float, max_confidence: float
    ) -> List[Dict]:
        """Filter predictions by confidence and league with league-specific thresholds"""
        filtered = []
        for p in predictions:
            confidence = p.get("confidence", 0)
            league_id = p.get("league_id")

            # Decorate / normalize the 1X2 pick once, so downstream selection is consistent.
            decorated = self._decorate_1x2_pick(p)

            if (
                min_confidence <= confidence <= max_confidence
                and league_id in self.FEATURED_LEAGUES
                and self._is_today_or_tomorrow(p.get("match_date"))
                and decorated is not None
                and self._passes_1x2_edge(decorated)
            ):
                filtered.append(decorated)

        return filtered

    def _filter_predictions_adaptive(
        self,
        predictions: List[Dict],
        min_confidence: float,
        max_confidence: float,
        required_count: int,
    ) -> List[Dict]:
        """Try primary confidence band; optionally widen band if not enough eligible picks."""
        eligible = self._filter_predictions(
            predictions,
            min_confidence=min_confidence,
            max_confidence=max_confidence,
        )

        if not self.adaptive_fallback or len(eligible) >= required_count:
            return eligible

        # Widen the band in small steps, but keep within a safe envelope.
        for step in range(1, 4):
            widened_min = max(
                self.fallback_band_floor, min_confidence - (self.fallback_band_step * step)
            )
            widened_max = min(
                self.fallback_band_ceiling, max_confidence + (self.fallback_band_step * step)
            )
            widened = self._filter_predictions(
                predictions,
                min_confidence=widened_min,
                max_confidence=widened_max,
            )
            if len(widened) > len(eligible):
                eligible = widened
            if len(eligible) >= required_count:
                break

        return eligible

    def _extract_1x2_odds(self, pred: Dict[str, Any]):
        odds = pred.get("odds")
        if isinstance(odds, dict):
            if "1x2" in odds and isinstance(odds["1x2"], dict):
                o = odds["1x2"]
                return o.get("home"), o.get("draw"), o.get("away"), bool(o.get("available"))
            if {"home", "draw", "away"}.issubset(odds.keys()):
                return (
                    odds.get("home"),
                    odds.get("draw"),
                    odds.get("away"),
                    bool(odds.get("available", True)),
                )

        return (
            pred.get("odds_home"),
            pred.get("odds_draw"),
            pred.get("odds_away"),
            bool(pred.get("odds_1x2_available") or pred.get("odds_available")),
        )

    def _extract_btts_odds(self, pred: Dict[str, Any]):
        odds = pred.get("odds")
        if isinstance(odds, dict):
            if "btts" in odds and isinstance(odds["btts"], dict):
                o = odds["btts"]
                return o.get("yes"), o.get("no"), bool(o.get("available"))
        return (
            pred.get("btts_odds_yes"),
            pred.get("btts_odds_no"),
            bool(pred.get("odds_btts_available")),
        )

    def _implied_probs_1x2(self, odds_home, odds_draw, odds_away):
        if not all([odds_home, odds_draw, odds_away]):
            return None
        try:
            implied_home = 1 / float(odds_home)
            implied_draw = 1 / float(odds_draw)
            implied_away = 1 / float(odds_away)
        except Exception:
            return None
        total = implied_home + implied_draw + implied_away
        if total <= 0:
            return None
        return {
            "home": implied_home / total,
            "draw": implied_draw / total,
            "away": implied_away / total,
        }

    def _passes_1x2_edge(self, pred: Dict[str, Any]) -> bool:
        odds_home, odds_draw, odds_away, available = self._extract_1x2_odds(pred)
        if not available:
            return False

        implied = self._implied_probs_1x2(odds_home, odds_draw, odds_away)
        if not implied:
            return False

        outcome = _normalize_1x2_outcome(pred.get("predicted_outcome"))
        if outcome is None:
            probs = {
                "home": _to_float(pred.get("home_win_prob"), 0.0),
                "draw": _to_float(pred.get("draw_prob"), 0.0),
                "away": _to_float(pred.get("away_win_prob"), 0.0),
            }
            outcome = max(probs, key=probs.get)

        if self.exclude_draws and outcome == "draw":
            return False

        model_prob = {
            "home": _to_float(pred.get("home_win_prob"), 0.0),
            "draw": _to_float(pred.get("draw_prob"), 0.0),
            "away": _to_float(pred.get("away_win_prob"), 0.0),
        }.get(outcome, 0.0)

        edge = float(model_prob) - float(implied[outcome])

        # Persist value signals for selection ranking & UI/debugging.
        pred["predicted_outcome"] = outcome
        pred["implied_prob"] = float(implied[outcome])
        pred["model_prob"] = float(model_prob)
        pred["edge"] = float(edge)
        pred["value_score"] = float(edge) * float(pred.get("odds") or 0.0)

        return float(model_prob) > float(implied[outcome]) + self.EDGE_MARGIN

    def _decorate_1x2_pick(self, pred: Dict[str, Any]) -> Dict[str, Any] | None:
        """Normalize outcome labels + ensure odds/selection fields exist for 1X2 picks."""
        odds_home, odds_draw, odds_away, available = self._extract_1x2_odds(pred)
        if not available:
            return None

        # Work on the existing object to avoid copying large payloads.
        outcome = _normalize_1x2_outcome(pred.get("predicted_outcome"))
        if outcome is None:
            probs = {
                "home": _to_float(pred.get("home_win_prob"), 0.0),
                "draw": _to_float(pred.get("draw_prob"), 0.0),
                "away": _to_float(pred.get("away_win_prob"), 0.0),
            }
            outcome = max(probs, key=probs.get)

        if self.exclude_draws and outcome == "draw":
            return None

        pred["predicted_outcome"] = outcome
        pred["selection_type"] = pred.get("selection_type") or "Match Winner"
        pred["selection_value"] = pred.get("selection_value") or {
            "home": "Home Win",
            "draw": "Draw",
            "away": "Away Win",
        }.get(outcome, outcome)

        # Ensure per-leg odds matches selected outcome.
        if outcome == "home":
            pred["odds"] = odds_home or pred.get("odds")
        elif outcome == "draw":
            pred["odds"] = odds_draw or pred.get("odds")
        elif outcome == "away":
            pred["odds"] = odds_away or pred.get("odds")

        return pred

    def _passes_btts_edge(self, pred: Dict[str, Any], model_prob: float) -> bool:
        odds_yes, odds_no, available = self._extract_btts_odds(pred)
        if not available:
            return False
        if not odds_yes or not odds_no:
            return False
        try:
            implied_yes = 1 / float(odds_yes)
            implied_no = 1 / float(odds_no)
        except Exception:
            return False

        total = implied_yes + implied_no
        if total <= 0:
            return False

        implied_yes = implied_yes / total
        return float(model_prob) > float(implied_yes) + self.EDGE_MARGIN

    def _is_today_or_tomorrow(self, match_date_input) -> bool:
        """Check if match is today or tomorrow"""
        if not match_date_input:
            return False

        try:
            # Handle both datetime objects and strings
            if isinstance(match_date_input, datetime):
                match_date = match_date_input
            elif isinstance(match_date_input, str):
                match_date = datetime.fromisoformat(match_date_input.replace("Z", "+00:00"))
            else:
                return False

            now = datetime.now()
            tomorrow = now + timedelta(days=1)

            return match_date.date() == now.date() or match_date.date() == tomorrow.date()
        except:
            return False

    def _select_diverse_matches(
        self, predictions: List[Dict], count: int, max_per_league: int
    ) -> List[Dict]:
        """
        Select matches with diversity constraints
        - Max N matches per league
        - Spread across different leagues
        """
        if len(predictions) <= count:
            return predictions

        # Prefer value picks: sort by computed value score (descending), then confidence.
        sorted_preds = sorted(
            predictions,
            key=lambda x: (
                _to_float(x.get("value_score"), -1.0),
                _to_float(x.get("confidence"), 0.0),
            ),
            reverse=True,
        )

        selected = []
        league_counts = {}

        for pred in sorted_preds:
            if len(selected) >= count:
                break

            league_id = pred.get("league_id")
            league_count = league_counts.get(league_id, 0)

            # Check diversity constraint
            if league_count < max_per_league:
                selected.append(pred)
                league_counts[league_id] = league_count + 1

        # If not enough diverse matches, add remaining high confidence ones
        if len(selected) < count:
            for pred in sorted_preds:
                if pred not in selected and len(selected) < count:
                    selected.append(pred)

        return selected[:count]

    def _build_accumulator(self, selections: List[Dict], acca_type: str) -> Dict[str, Any]:
        """Build accumulator object with selections and calculated odds"""
        if not selections:
            return None

        # Calculate total odds
        total_odds = 1.0
        for sel in selections:
            odds = sel.get("odds", 1.8)
            total_odds *= odds

        # Standard stake
        stake = 10.0
        potential_return = total_odds * stake

        return {
            "acca_type": acca_type,
            "total_odds": round(total_odds, 2),
            "stake": stake,
            "potential_return": round(potential_return, 2),
            "selections": selections,
            "created_at": datetime.now().isoformat(),
            "status": "pending",
            "risk_level": self.RISK_LEVELS.get(acca_type, "medium"),
        }

    def generate_all_daily_accumulators(self, predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate all daily accumulators with flexible sizing
        Tries 8-fold first, falls back to 6-fold if insufficient predictions
        Returns dict with main accumulator (8/6-fold), 4-fold, and BTTS
        """
        accumulators = {}

        # Generate main accumulator: Try 8-fold first, fallback to 6-fold
        eight_fold = self.generate_8_fold(predictions)
        if eight_fold:
            accumulators["8-fold"] = eight_fold
        else:
            # Fallback to 6-fold if 8-fold unavailable
            six_fold = self.generate_6_fold(predictions)
            if six_fold:
                accumulators["6-fold"] = six_fold

        # Generate 4-fold
        four_fold = self.generate_4_fold(predictions)
        if four_fold:
            accumulators["4-fold"] = four_fold

        # Generate BTTS
        btts = self.generate_btts(predictions)
        if btts:
            accumulators["BTTS"] = btts

        return accumulators


def save_accumulator_to_db(db, accumulator: Dict[str, Any]) -> int:
    """
    Save accumulator to database
    Returns accumulator ID
    """
    from datetime import date

    # Insert main accumulator record
    acca_id = db.log_accumulator(
        date=date.today(),
        acca_type=accumulator["acca_type"],
        total_odds=accumulator["total_odds"],
        stake=accumulator["stake"],
        potential_return=accumulator["potential_return"],
        status=accumulator["status"],
    )

    # Insert selections
    for sel in accumulator["selections"]:
        db.log_accumulator_selection(
            accumulator_id=acca_id,
            fixture_id=sel["fixture_id"],
            home_team=sel["home_team"],
            away_team=sel["away_team"],
            league_id=sel.get("league_id"),
            league_name=sel.get("league_name"),
            match_date=sel["match_date"],
            selection_type=sel.get("selection_type", "Match Winner"),
            selection_value=sel.get("selection_value", sel.get("predicted_outcome")),
            odds=sel["odds"],
            confidence=sel.get("confidence", 0),
        )

    return acca_id
