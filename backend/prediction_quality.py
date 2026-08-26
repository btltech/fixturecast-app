"""Prediction quality gating: cold-start detection for the ensemble output.

The ensemble's Elo component falls back to a base rating (1500) for teams it has
never seen — most commonly national teams in international competitions (World Cup,
Nations League, continental qualifiers) that are absent from the club-league
training history. In that situation the models effectively run on priors and emit
near-uniform, low-information predictions (e.g. a 0-0 scoreline with ~0.4 lambdas).

The base ensemble already abstains when ``confidence < threshold``, but that only
fires when the calibrated confidence happens to dip below the league threshold. It
does not *explicitly* know the prediction was produced without real team data. This
module detects that condition and forces an abstention with a clear reason so the
API and frontend can say "not enough data for this competition" instead of
presenting a confident-looking but unfounded scoreline.

The detector is a pure function with no heavy dependencies so it is cheap to unit
test in isolation.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# Must match EloGlickoModel.base_rating in ml_engine/elo_model.py.
ELO_BASE_RATING = 1500.0

# Both teams sitting *exactly* on the base rating means neither was found in the
# Elo table — i.e. a genuine cold start, not a coincidence of two average teams.
ELO_DEFAULT_EPSILON = 0.5

# competition_metadata["type"] values that denote national-team competitions where
# the club-trained models have weak coverage. Sourced from backend/config.json, so
# this stays in sync with the project's own catalog instead of hardcoding IDs.
INTERNATIONAL_COMPETITION_TYPES = frozenset({"international", "international_qualifier", "friendly"})


def _both_at_default_elo(
    home_elo: Optional[float],
    away_elo: Optional[float],
    base: float = ELO_BASE_RATING,
    epsilon: float = ELO_DEFAULT_EPSILON,
) -> bool:
    """True when both sides sit on the Elo base rating (unseen teams)."""
    if home_elo is None or away_elo is None:
        return False
    return abs(float(home_elo) - base) <= epsilon and abs(float(away_elo) - base) <= epsilon


def _either_at_default_elo(
    home_elo: Optional[float],
    away_elo: Optional[float],
    base: float = ELO_BASE_RATING,
    epsilon: float = ELO_DEFAULT_EPSILON,
) -> bool:
    """True when at least one side sits on the Elo base rating (unseen team)."""
    if home_elo is None or away_elo is None:
        return True
    return abs(float(home_elo) - base) <= epsilon or abs(float(away_elo) - base) <= epsilon


def detect_cold_start(
    result: Dict[str, Any],
    *,
    competition_type: Optional[str] = None,
    h2h_total_matches: int = 0,
    odds_available: bool = False,
) -> Dict[str, Any]:
    """Inspect an ensemble result and decide how much to trust it.

    Returns a small dict describing the decision. It never raises and never mutates
    the input.

    Two distinct situations are separated:

    * **Blind cold start** — weak team data AND no market signal. There is nothing to
      anchor the prediction to, so abstain (``cold_start`` / ``force_abstain`` True).
    * **Market-based** — the same weak team data BUT bookmaker odds are available. The
      goal markets are anchored to the market (see the Poisson lambda floor), so the
      pick is shown; it is only flagged ``low_model_confidence`` because the *model*
      adds little team-specific edge here (it mostly echoes the market).

    Args:
        result: the dict returned by ``EnsemblePredictor.predict_fixture``.
        competition_type: ``competition_metadata["type"]`` for the league, e.g.
            ``"international"`` for national-team competitions.
        h2h_total_matches: number of head-to-head matches available.
        odds_available: whether 1X2 bookmaker odds were available for this fixture.

    Keys returned:
        cold_start (bool):           True only when blind (no data AND no market).
        reason (str|None):           Explanation when cold_start is True.
        force_abstain (bool):        True when the caller should force abstain.
        low_model_confidence (bool): True when the pick is market-based, not blind.
        model_confidence_note (str|None): Explanation when low_model_confidence is True.
    """
    elo = result.get("elo_ratings") or {}
    home_elo = elo.get("home")
    away_elo = elo.get("away")
    data_quality = (result.get("data_quality") or "").lower()

    default_elo = _both_at_default_elo(home_elo, away_elo)
    either_default_elo = _either_at_default_elo(home_elo, away_elo)
    is_international = (competition_type or "").lower() in INTERNATIONAL_COMPETITION_TYPES
    no_history = h2h_total_matches <= 0

    # 1. Is the team data weak enough to be a concern?
    weak_data = False
    weak_reason: Optional[str] = None
    if default_elo:
        weak_data = True
        weak_reason = (
            "No Elo history for either team — prediction is based on priors only "
            "(common for national-team and newly added competitions)."
        )
    elif is_international and either_default_elo and no_history:
        weak_data = True
        weak_reason = (
            "International fixture with an unrated team and no head-to-head history — "
            "club-trained models have weak coverage here."
        )
    elif is_international and data_quality in {"limited", "partial"} and no_history:
        weak_data = True
        weak_reason = (
            "International fixture with limited/partial data and no head-to-head history — "
            "club-trained models have weak coverage here."
        )

    cold_start = False
    reason: Optional[str] = None
    low_model_confidence = False
    model_confidence_note: Optional[str] = None

    # 2. Decide: blind cold start (abstain) vs market-based (show, but flag).
    if weak_data:
        if odds_available:
            low_model_confidence = True
            model_confidence_note = (
                "Limited team data — this prediction leans on the betting market "
                "rather than model-specific signal."
            )
        else:
            cold_start = True
            reason = weak_reason

    return {
        "cold_start": cold_start,
        "reason": reason,
        "force_abstain": cold_start,
        "low_model_confidence": low_model_confidence,
        "model_confidence_note": model_confidence_note,
    }


def apply_cold_start_gate(
    result: Dict[str, Any],
    *,
    competition_type: Optional[str] = None,
    h2h_total_matches: int = 0,
    odds_available: bool = False,
) -> Dict[str, Any]:
    """Annotate ``result`` in place with cold-start / confidence flags.

    Blind cold start (weak data, no market) → sets ``cold_start`` + ``cold_start_reason``
    and forces ``abstain`` True. Market-based (weak data but odds available) → sets
    ``low_model_confidence`` + ``model_confidence_note`` and leaves ``abstain`` alone, so
    the pick is shown with a transparency note instead of being suppressed. Returns the
    same dict for convenience.
    """
    decision = detect_cold_start(
        result,
        competition_type=competition_type,
        h2h_total_matches=h2h_total_matches,
        odds_available=odds_available,
    )
    result["cold_start"] = decision["cold_start"]
    if decision["cold_start"]:
        result["cold_start_reason"] = decision["reason"]
        if decision["force_abstain"]:
            result["abstain"] = True

    result["low_model_confidence"] = decision["low_model_confidence"]
    if decision["low_model_confidence"]:
        result["model_confidence_note"] = decision["model_confidence_note"]
    return result
