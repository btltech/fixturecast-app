"""
Canonical Selection Qualifier for FixtureCast.

Provides a unified qualification gate for all public recommendations:
- Smart Markets (BTTS, Over/Under 2.5, 1X2)
- Daily Singles (+EV Value Bets)
- Qualified Accumulator Legs
- Automated Bot & Social Picks

Enforces empirical calibration, market-price awareness, mandatory edge verification,
and strict risk limits.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple

try:
    from backend.calibration_layer import CalibrationLayer, get_calibration_layer
except ImportError:
    from calibration_layer import CalibrationLayer, get_calibration_layer

MarketType = Literal["home_win", "draw", "away_win", "btts", "over25", "under25", "1x2"]


def _get_env_float(name: str, default: float) -> float:
    try:
        val = os.environ.get(name)
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default


def _get_env_int(name: str, default: int) -> int:
    try:
        val = os.environ.get(name)
        return int(val) if val is not None else default
    except (ValueError, TypeError):
        return default


# Canonical Configurable Thresholds
BASE_MIN_PROB = _get_env_float("QUAL_BASE_MIN_PROB", 0.50)
BASE_MIN_EDGE = _get_env_float("QUAL_BASE_MIN_EDGE", 0.02)
ACCA_4_MIN_PROB = _get_env_float("QUAL_ACCA_4_MIN_PROB", 0.65)
ACCA_MAX_LEGS = _get_env_int("QUAL_ACCA_MAX_LEGS", 4)
MIN_SAMPLE_SIZE = _get_env_int("QUAL_MIN_SAMPLE_SIZE", 20)
MIN_ODDS_FLOOR = _get_env_float("QUAL_MIN_ODDS_FLOOR", 1.45)


@dataclass
class SelectionContext:
    market_type: MarketType
    raw_probability: float
    odds: Optional[float] = None
    all_odds: Optional[Dict[str, float]] = None
    league_id: Optional[int] = None
    abstain: bool = False
    is_acca_leg: bool = False
    acca_size: Optional[int] = None
    conservative_probability: Optional[float] = None
    sample_size: Optional[int] = None
    fixture_id: Optional[int] = None
    match_name: Optional[str] = None


@dataclass
class QualificationResult:
    qualified: bool
    reason: str
    gate: str  # "abstain" | "no_odds" | "odds_floor" | "insufficient_sample" | "min_probability" | "insufficient_edge" | "acca_size_exceeded" | "pass"
    raw_probability: float
    conservative_probability: Optional[float]
    sample_size: int
    implied_probability: Optional[float]
    edge: Optional[float]
    ev: Optional[float] = None
    warnings: List[str] = field(default_factory=list)
    hierarchy_level: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "qualified": self.qualified,
            "reason": self.reason,
            "gate": self.gate,
            "raw_probability": round(self.raw_probability, 4),
            "conservative_probability": round(self.conservative_probability, 4) if self.conservative_probability is not None else None,
            "sample_size": self.sample_size,
            "implied_probability": round(self.implied_probability, 4) if self.implied_probability is not None else None,
            "edge": round(self.edge, 4) if self.edge is not None else None,
            "ev": round(self.ev, 4) if self.ev is not None else None,
            "warnings": self.warnings,
            "hierarchy_level": self.hierarchy_level,
        }


def de_vig_two_way(odds_a: float, odds_b: float) -> Optional[Tuple[float, float]]:
    if odds_a <= 1.0 or odds_b <= 1.0:
        return None
    raw_a = 1.0 / odds_a
    raw_b = 1.0 / odds_b
    margin = raw_a + raw_b
    if margin <= 0:
        return None
    return (raw_a / margin, raw_b / margin)


def de_vig_three_way(odds_home: float, odds_draw: float, odds_away: float) -> Optional[Tuple[float, float, float]]:
    if odds_home <= 1.0 or odds_draw <= 1.0 or odds_away <= 1.0:
        return None
    raw_h = 1.0 / odds_home
    raw_d = 1.0 / odds_draw
    raw_a = 1.0 / odds_away
    margin = raw_h + raw_d + raw_a
    if margin <= 0:
        return None
    return (raw_h / margin, raw_d / margin, raw_a / margin)


def compute_implied_probability(market_type: MarketType, odds: Optional[float], all_odds: Optional[Dict[str, float]]) -> Tuple[Optional[float], List[str]]:
    warnings: List[str] = []
    if odds is None or odds <= 1.0:
        return None, ["Missing or invalid selection odds"]

    if market_type in ("home_win", "draw", "away_win", "1x2"):
        if all_odds and "home" in all_odds and "draw" in all_odds and "away" in all_odds:
            devigged = de_vig_three_way(all_odds["home"], all_odds["draw"], all_odds["away"])
            if devigged:
                if market_type in ("home_win", "1x2"):
                    return devigged[0], warnings
                elif market_type == "draw":
                    return devigged[1], warnings
                elif market_type == "away_win":
                    return devigged[2], warnings
        warnings.append("Three-way odds incomplete; approximated with standard 6% bookmaker margin")
        raw_implied = (1.0 / odds) / 1.06
        return max(0.01, min(0.99, raw_implied)), warnings

    elif market_type == "btts":
        if all_odds and "yes" in all_odds and "no" in all_odds:
            devigged = de_vig_two_way(all_odds["yes"], all_odds["no"])
            if devigged:
                return devigged[0], warnings
        warnings.append("Two-way BTTS odds incomplete; approximated with standard 5% bookmaker margin")
        return max(0.01, min(0.99, (1.0 / odds) / 1.05)), warnings

    elif market_type in ("over25", "under25"):
        if all_odds and "over" in all_odds and "under" in all_odds:
            devigged = de_vig_two_way(all_odds["over"], all_odds["under"])
            if devigged:
                return (devigged[0] if market_type == "over25" else devigged[1]), warnings
        warnings.append("Two-way Over/Under odds incomplete; approximated with standard 5% bookmaker margin")
        return max(0.01, min(0.99, (1.0 / odds) / 1.05)), warnings

    raw_implied = (1.0 / odds) / 1.05
    return max(0.01, min(0.99, raw_implied)), warnings


def qualify_selection(
    context: SelectionContext,
    calibration_layer: Optional[CalibrationLayer] = None,
) -> QualificationResult:
    cal_layer = calibration_layer or get_calibration_layer()

    if context.abstain:
        return QualificationResult(
            qualified=False,
            reason="Prediction engine abstained on this fixture due to high uncertainty or cold start",
            gate="abstain",
            raw_probability=context.raw_probability,
            conservative_probability=None,
            sample_size=0,
            implied_probability=None,
            edge=None,
            hierarchy_level="none",
        )

    if context.odds is None or context.odds <= 1.0:
        return QualificationResult(
            qualified=False,
            reason="Odds missing: selection cannot be recommended without a verifiable market price",
            gate="no_odds",
            raw_probability=context.raw_probability,
            conservative_probability=None,
            sample_size=0,
            implied_probability=None,
            edge=None,
            hierarchy_level="none",
        )

    if not context.is_acca_leg and context.odds < MIN_ODDS_FLOOR:
        return QualificationResult(
            qualified=False,
            reason=f"Odds ({context.odds:.2f}) too short for a single value bet. Staking 1 unit to win < 0.45u risks excessive downside on upsets.",
            gate="odds_floor",
            raw_probability=context.raw_probability,
            conservative_probability=None,
            sample_size=0,
            implied_probability=1.0 / context.odds,
            edge=None,
            hierarchy_level="none",
        )

    implied_prob, odds_warnings = compute_implied_probability(
        context.market_type, context.odds, context.all_odds
    )

    if context.conservative_probability is not None and context.sample_size is not None:
        conservative_prob = context.conservative_probability
        sample_size = context.sample_size
        hierarchy_level = "context_provided"
    else:
        estimate = cal_layer.get_conservative_estimate(
            raw_prob=context.raw_probability,
            implied_prob=implied_prob,
            market_type=context.market_type,
            league_id=context.league_id,
            min_sample_size=MIN_SAMPLE_SIZE,
        )
        conservative_prob = estimate.conservative_probability
        sample_size = estimate.sample_size
        hierarchy_level = estimate.hierarchy_level

    if conservative_prob is None or sample_size < MIN_SAMPLE_SIZE:
        return QualificationResult(
            qualified=False,
            reason=f"Insufficient empirical evidence in calibration history (sample size: {sample_size} < {MIN_SAMPLE_SIZE})",
            gate="insufficient_sample",
            raw_probability=context.raw_probability,
            conservative_probability=None,
            sample_size=sample_size,
            implied_probability=implied_prob,
            edge=None,
            warnings=odds_warnings,
            hierarchy_level=hierarchy_level,
        )

    if context.is_acca_leg and context.acca_size == 4:
        min_prob = ACCA_4_MIN_PROB
    elif context.odds >= 2.05:
        min_prob = 0.46
    elif context.odds >= 1.70:
        min_prob = 0.50
    elif context.odds >= 1.50:
        min_prob = 0.54
    else:
        min_prob = 0.60

    if conservative_prob < min_prob:
        return QualificationResult(
            qualified=False,
            reason=f"Conservative probability ({conservative_prob:.1%}) below required minimum floor ({min_prob:.1%}) for odds {context.odds:.2f}",
            gate="min_probability",
            raw_probability=context.raw_probability,
            conservative_probability=conservative_prob,
            sample_size=sample_size,
            implied_probability=implied_prob,
            edge=(conservative_prob - implied_prob) if implied_prob is not None else None,
            warnings=odds_warnings,
            hierarchy_level=hierarchy_level,
        )

    ev = (conservative_prob * context.odds) - 1.0
    edge = (conservative_prob - implied_prob) if implied_prob is not None else None

    if ev < BASE_MIN_EDGE:
        return QualificationResult(
            qualified=False,
            reason=f"Expected value ({ev:+.1%}) below required +{BASE_MIN_EDGE:.1%} threshold vs market ({implied_prob:.1%})",
            gate="insufficient_edge",
            raw_probability=context.raw_probability,
            conservative_probability=conservative_prob,
            sample_size=sample_size,
            implied_probability=implied_prob,
            edge=edge,
            ev=ev,
            warnings=odds_warnings,
            hierarchy_level=hierarchy_level,
        )

    if context.is_acca_leg and context.acca_size is not None and context.acca_size > ACCA_MAX_LEGS:
        return QualificationResult(
            qualified=False,
            reason=f"Qualified Acca capped at maximum {ACCA_MAX_LEGS} legs (received {context.acca_size}-fold) to prevent compounding variance",
            gate="acca_size_exceeded",
            raw_probability=context.raw_probability,
            conservative_probability=conservative_prob,
            sample_size=sample_size,
            implied_probability=implied_prob,
            edge=edge,
            ev=ev,
            warnings=odds_warnings + [f"Leg passed single-leg qualification but excluded from {context.acca_size}-fold Qualified Acca"],
            hierarchy_level=hierarchy_level,
        )

    return QualificationResult(
        qualified=True,
        reason=f"Qualified recommendation: conservative probability {conservative_prob:.1%} with {ev:+.1%} EV edge at {context.odds:.2f} odds",
        gate="pass",
        raw_probability=context.raw_probability,
        conservative_probability=conservative_prob,
        sample_size=sample_size,
        implied_probability=implied_prob,
        edge=edge,
        ev=ev,
        warnings=odds_warnings,
        hierarchy_level=hierarchy_level,
    )
