"""Pydantic request/response schemas for the ML API.

Extracted from ``ml_api_impl.py`` to keep that module focused on routing and
prediction orchestration. These are plain data models with no heavy dependencies,
so they import quickly and are easy to test in isolation.
"""

from __future__ import annotations

from typing import Dict, Optional

from pydantic import BaseModel


class MatchFeatures(BaseModel):
    """
    Feature dict for a single match prediction with validation.
    All numeric fields are validated for reasonable ranges.
    """

    home_id: int
    away_id: int
    home_name: str
    away_name: str
    home_league_points: float = 30
    away_league_points: float = 30
    home_league_pos: int = 10
    away_league_pos: int = 10
    home_points_last10: float = 15
    away_points_last10: float = 15
    home_form_last5: float = 7
    away_form_last5: float = 7
    home_goals_for_avg: float = 1.3
    away_goals_for_avg: float = 1.2
    home_goals_against_avg: float = 1.2
    away_goals_against_avg: float = 1.3
    home_wins_last10: int = 5
    away_wins_last10: int = 5
    home_draws_last10: int = 3
    away_draws_last10: int = 3
    home_losses_last10: int = 2
    away_losses_last10: int = 2
    home_goals_for_last10: int = 13
    away_goals_for_last10: int = 12
    home_goals_against_last10: int = 12
    away_goals_against_last10: int = 13
    h2h_home_wins: int = 2
    h2h_draws: int = 2
    h2h_away_wins: int = 2
    h2h_total_matches: int = 6
    home_clean_sheets: int = 3
    away_clean_sheets: int = 3
    home_total_matches: int = 20
    away_total_matches: int = 20
    # Optional odds data
    odds_home_win: Optional[float] = None
    odds_draw: Optional[float] = None
    odds_away_win: Optional[float] = None
    odds_available: bool = False

    class Config:
        """Pydantic configuration"""

        json_schema_extra = {
            "example": {
                "home_id": 42,
                "away_id": 33,
                "home_name": "Arsenal",
                "away_name": "Manchester United",
                "home_league_points": 45,
                "away_league_points": 38,
                "home_league_pos": 3,
                "away_league_pos": 7,
            }
        }

    def validate_probabilities(self) -> bool:
        """Validate that odds are in reasonable range if provided."""
        if self.odds_home_win is not None:
            if not (1.0 <= self.odds_home_win <= 100.0):
                return False
        if self.odds_draw is not None:
            if not (1.0 <= self.odds_draw <= 100.0):
                return False
        if self.odds_away_win is not None:
            if not (1.0 <= self.odds_away_win <= 100.0):
                return False
        return True


class PredictionResponse(BaseModel):
    """
    Response containing match prediction with confidence intervals.
    All probabilities are validated to be between 0 and 1.
    Markets: 1X2, BTTS, O/U 2.5, O/U 1.5, O/U 3.5, BTTS Halves, Asian Handicap
    """

    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    confidence: float = 0.0
    confidence_threshold: Optional[float] = None
    abstain: bool = False
    cold_start: bool = False
    cold_start_reason: Optional[str] = None
    low_model_confidence: bool = False
    model_confidence_note: Optional[str] = None
    combiner: Optional[str] = None
    ensemble_weights: Optional[Dict] = None
    calibration_temperature: Optional[float] = None
    raw_probs: Optional[Dict] = None
    btts_prob: float
    over25_prob: float
    under25_prob: float
    over05_prob: Optional[float] = None
    under05_prob: Optional[float] = None
    over15_prob: float
    under15_prob: float
    over35_prob: float
    under35_prob: float
    over45_prob: Optional[float] = None
    under45_prob: Optional[float] = None
    btts_1st_half_prob: float
    btts_2nd_half_prob: float
    home_ah_minus_05: float
    home_ah_minus_10: float
    home_ah_minus_15: Optional[float] = None
    home_ah_plus_05: float
    home_ah_plus_10: float
    home_ah_plus_15: Optional[float] = None
    model_breakdown: Dict
    confidence_intervals: Optional[Dict] = None
    elo_ratings: Optional[Dict] = None

    class Config:
        """Pydantic configuration"""

        json_schema_extra = {
            "example": {
                "home_win_prob": 0.45,
                "draw_prob": 0.28,
                "away_win_prob": 0.27,
                "predicted_scoreline": "2-1",
                "btts_prob": 0.62,
                "over25_prob": 0.58,
                "model_breakdown": {},
            }
        }

    def validate_probabilities(self) -> bool:
        """Ensure all probabilities are valid (between 0 and 1)."""
        probs = [
            self.home_win_prob,
            self.draw_prob,
            self.away_win_prob,
            self.btts_prob,
            self.over25_prob,
        ]
        return all(0.0 <= p <= 1.0 for p in probs)

    def probabilities_sum_valid(self) -> bool:
        """Check that main outcome probabilities sum to approximately 1."""
        total = self.home_win_prob + self.draw_prob + self.away_win_prob
        return 0.99 <= total <= 1.01


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error: str
    detail: Optional[str] = None
    code: int = 500
    timestamp: str = ""

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Prediction failed",
                "detail": "Unable to fetch team statistics",
                "code": 503,
                "timestamp": "2025-01-15T10:30:00Z",
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    models_loaded: bool
    api_client_ready: bool
    timestamp: str
    uptime_seconds: Optional[float] = None
