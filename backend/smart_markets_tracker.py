"""
Smart Markets Performance Tracker
Monitors accuracy of high-confidence predictions with market edge.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from database import USE_POSTGRES, PredictionDB, get_db


class SmartMarketsTracker:
    """Track and monitor Smart Markets prediction performance."""

    EDGE_MARGIN = 0.02  # 2% edge threshold
    CONFIDENCE_THRESHOLD = 0.60  # 60% confidence threshold

    @staticmethod
    def twoWayImplied(oddsA: float, oddsB: float) -> Optional[Dict]:
        """Calculate two-way implied probabilities removing bookmaker margin."""
        if not oddsA or not oddsB or oddsA <= 1 or oddsB <= 1:
            return None
        impliedA = 1 / oddsA
        impliedB = 1 / oddsB
        total = impliedA + impliedB
        if total <= 0:
            return None
        return {"a": impliedA / total, "b": impliedB / total}

    @staticmethod
    def tag_smart_market_predictions():
        """
        Scan all untagged predictions and mark Smart Markets qualifying ones.
        Adds 'smart_market_ou' and 'smart_market_btts' flags.
        """
        SmartMarketsTracker._ensure_columns()

        with get_db() as conn:
            cursor = conn.cursor()
            ph = "%s" if USE_POSTGRES else "?"

            # Get predictions with odds data that haven't been checked yet
            cursor.execute(
                f"""
                SELECT fixture_id, over25_prob, btts_prob,
                       odds_over_25, odds_under_25, odds_btts_yes, odds_btts_no
                FROM predictions
                WHERE evaluated = 0
                  AND odds_over_25 > 0
                  AND odds_under_25 > 0
                """
            )

            rows = cursor.fetchall()
            tagged = {"ou": 0, "btts": 0, "total": 0}

            for row in rows:
                if USE_POSTGRES:
                    fixture_id = row["fixture_id"]
                    over25_prob = row["over25_prob"] or 0
                    btts_prob = row["btts_prob"] or 0
                    over_odds = row["odds_over_25"] or 0
                    under_odds = row["odds_under_25"] or 0
                    btts_yes_odds = row["odds_btts_yes"] or 0
                    btts_no_odds = row["odds_btts_no"] or 0
                else:
                    fixture_id = row[0]
                    over25_prob = row[1] or 0
                    btts_prob = row[2] or 0
                    over_odds = row[3] or 0
                    under_odds = row[4] or 0
                    btts_yes_odds = row[5] or 0
                    btts_no_odds = row[6] or 0

                # Check Over/Under 2.5
                ou_qualifies = False
                if over25_prob >= SmartMarketsTracker.CONFIDENCE_THRESHOLD:
                    implied = SmartMarketsTracker.twoWayImplied(over_odds, under_odds)
                    if implied:
                        bookmaker_implied = implied["a"]  # Over probability
                        edge = over25_prob - bookmaker_implied
                        if edge >= SmartMarketsTracker.EDGE_MARGIN:
                            ou_qualifies = True
                            tagged["ou"] += 1

                # Check BTTS
                btts_qualifies = False
                if btts_prob >= SmartMarketsTracker.CONFIDENCE_THRESHOLD:
                    implied = SmartMarketsTracker.twoWayImplied(btts_yes_odds, btts_no_odds)
                    if implied:
                        bookmaker_implied = implied["a"]  # BTTS Yes probability
                        edge = btts_prob - bookmaker_implied
                        if edge >= SmartMarketsTracker.EDGE_MARGIN:
                            btts_qualifies = True
                            tagged["btts"] += 1

                # Tag in database if qualifies
                if ou_qualifies or btts_qualifies:
                    cursor.execute(
                        f"""
                        UPDATE predictions
                        SET smart_market_ou = {ph}, smart_market_btts = {ph}
                        WHERE fixture_id = {ph}
                        """,
                        (1 if ou_qualifies else 0, 1 if btts_qualifies else 0, fixture_id),
                    )
                    tagged["total"] += 1

            conn.commit()
            return tagged

    @staticmethod
    def _ensure_columns():
        """Ensure smart_market columns exist in predictions table."""
        with get_db() as conn:
            cursor = conn.cursor()
            try:
                if USE_POSTGRES:
                    cursor.execute(
                        "ALTER TABLE predictions ADD COLUMN IF NOT EXISTS smart_market_ou INTEGER DEFAULT 0"
                    )
                    cursor.execute(
                        "ALTER TABLE predictions ADD COLUMN IF NOT EXISTS smart_market_btts INTEGER DEFAULT 0"
                    )
                else:
                    try:
                        cursor.execute(
                            "ALTER TABLE predictions ADD COLUMN smart_market_ou INTEGER DEFAULT 0"
                        )
                    except:
                        pass
                    try:
                        cursor.execute(
                            "ALTER TABLE predictions ADD COLUMN smart_market_btts INTEGER DEFAULT 0"
                        )
                    except:
                        pass
                conn.commit()
            except Exception as e:
                pass  # Columns already exist

    @staticmethod
    def get_smart_markets_performance(days: int = 30) -> Dict:
        """
        Get Smart Markets accuracy statistics.

        Returns:
            Dict with overall and per-market accuracy
        """
        SmartMarketsTracker._ensure_columns()

        with get_db() as conn:
            cursor = conn.cursor()
            ph = "%s" if USE_POSTGRES else "?"

            cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            # Over/Under performance
            cursor.execute(
                f"""
                SELECT COUNT(*) as total,
                       COALESCE(SUM(CASE WHEN over25_correct = 1 THEN 1 ELSE 0 END), 0) as correct
                FROM predictions
                WHERE smart_market_ou = 1
                  AND evaluated = 1
                  AND match_date >= {ph}
                """,
                (cutoff_date,),
            )
            ou_row = cursor.fetchone()
            if USE_POSTGRES:
                ou_total = ou_row["total"] if ou_row else 0
                ou_correct = ou_row["correct"] if ou_row else 0
            else:
                ou_total = ou_row[0] if ou_row else 0
                ou_correct = ou_row[1] if ou_row else 0

            # BTTS performance
            cursor.execute(
                f"""
                SELECT COUNT(*) as total,
                       COALESCE(SUM(CASE WHEN btts_correct = 1 THEN 1 ELSE 0 END), 0) as correct
                FROM predictions
                WHERE smart_market_btts = 1
                  AND evaluated = 1
                  AND match_date >= {ph}
                """,
                (cutoff_date,),
            )
            btts_row = cursor.fetchone()
            if USE_POSTGRES:
                btts_total = btts_row["total"] if btts_row else 0
                btts_correct = btts_row["correct"] if btts_row else 0
            else:
                btts_total = btts_row[0] if btts_row else 0
                btts_correct = btts_row[1] if btts_row else 0

            # Combined stats
            cursor.execute(
                f"""
                SELECT COUNT(DISTINCT fixture_id) as total_fixtures
                FROM predictions
                WHERE (smart_market_ou = 1 OR smart_market_btts = 1)
                  AND evaluated = 1
                  AND match_date >= {ph}
                """,
                (cutoff_date,),
            )
            total_row = cursor.fetchone()
            if USE_POSTGRES:
                total_fixtures = total_row["total_fixtures"] if total_row else 0
            else:
                total_fixtures = total_row[0] if total_row else 0

            # Recent results (last 10)
            cursor.execute(
                f"""
                SELECT fixture_id, home_team, away_team, match_date,
                       smart_market_ou, smart_market_btts,
                       over25_correct, btts_correct,
                       over25_prob, btts_prob
                FROM predictions
                WHERE (smart_market_ou = 1 OR smart_market_btts = 1)
                  AND evaluated = 1
                  AND match_date >= {ph}
                ORDER BY match_date DESC
                LIMIT 10
                """,
                (cutoff_date,),
            )

            recent = []
            for row in cursor.fetchall():
                if USE_POSTGRES:
                    recent.append(
                        {
                            "fixture_id": row["fixture_id"],
                            "home_team": row["home_team"],
                            "away_team": row["away_team"],
                            "match_date": (
                                row["match_date"].isoformat()
                                if hasattr(row["match_date"], "isoformat")
                                else str(row["match_date"])
                            ),
                            "markets": {
                                "over25": {
                                    "qualified": bool(row["smart_market_ou"]),
                                    "correct": bool(row["over25_correct"]),
                                    "prob": row["over25_prob"],
                                },
                                "btts": {
                                    "qualified": bool(row["smart_market_btts"]),
                                    "correct": bool(row["btts_correct"]),
                                    "prob": row["btts_prob"],
                                },
                            },
                        }
                    )
                else:
                    recent.append(
                        {
                            "fixture_id": row[0],
                            "home_team": row[1],
                            "away_team": row[2],
                            "match_date": (
                                row[3].isoformat() if hasattr(row[3], "isoformat") else str(row[3])
                            ),
                            "markets": {
                                "over25": {
                                    "qualified": bool(row[4]),
                                    "correct": bool(row[6]),
                                    "prob": row[8],
                                },
                                "btts": {
                                    "qualified": bool(row[5]),
                                    "correct": bool(row[7]),
                                    "prob": row[9],
                                },
                            },
                        }
                    )

            return {
                "days": days,
                "overall": {
                    "fixtures": total_fixtures,
                    "over25": {
                        "total": ou_total,
                        "correct": ou_correct,
                        "accuracy": round(ou_correct / ou_total * 100, 1) if ou_total > 0 else 0,
                    },
                    "btts": {
                        "total": btts_total,
                        "correct": btts_correct,
                        "accuracy": (
                            round(btts_correct / btts_total * 100, 1) if btts_total > 0 else 0
                        ),
                    },
                    "combined": {
                        "total": ou_total + btts_total,
                        "correct": ou_correct + btts_correct,
                        "accuracy": (
                            round((ou_correct + btts_correct) / (ou_total + btts_total) * 100, 1)
                            if (ou_total + btts_total) > 0
                            else 0
                        ),
                    },
                },
                "recent": recent,
            }

    @staticmethod
    def get_daily_report() -> Dict:
        """Get today's Smart Markets performance summary."""
        SmartMarketsTracker._ensure_columns()

        today = datetime.now().strftime("%Y-%m-%d")

        with get_db() as conn:
            cursor = conn.cursor()
            ph = "%s" if USE_POSTGRES else "?"

            # Today's Smart Markets
            cursor.execute(
                f"""
                SELECT COUNT(*) FROM predictions
                WHERE (smart_market_ou = 1 OR smart_market_btts = 1)
                  AND DATE(match_date) = {ph}
                """,
                (today,),
            )
            today_count = cursor.fetchone()[0]

            # Today's completed
            cursor.execute(
                f"""
                SELECT COUNT(*) FROM predictions
                WHERE (smart_market_ou = 1 OR smart_market_btts = 1)
                  AND DATE(match_date) = {ph}
                  AND evaluated = 1
                """,
                (today,),
            )
            completed_count = cursor.fetchone()[0]

            return {"date": today, "total_smart_markets": today_count, "completed": completed_count}


# Convenience function
def get_smart_markets_stats(days: int = 30) -> Dict:
    """Get Smart Markets performance stats."""
    return SmartMarketsTracker.get_smart_markets_performance(days)


def tag_predictions():
    """Tag qualifying predictions as Smart Markets."""
    return SmartMarketsTracker.tag_smart_market_predictions()
