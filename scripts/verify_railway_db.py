#!/usr/bin/env python3
"""
Verify Railway database and re-push data if needed
"""
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import get_db

ML_API_URL = "https://ml-api-production-6cfc.up.railway.app"


def verify_and_fix():
    """Verify Railway DB has data and re-push if needed."""

    # Check Railway database
    print("🔍 Checking Railway database...")
    try:
        response = requests.get(f"{ML_API_URL}/api/feedback/performance", timeout=10)

        if response.status_code == 200:
            data = response.json()
            total = data.get("overall", {}).get("total", 0)

            if total > 0:
                print(f"✅ Railway database has {total} predictions")
                print(f"   Accuracy: {data.get('overall', {}).get('accuracy_pct', '0%')}")

                # Show by_league breakdown
                by_league = data.get("by_league", {})
                if by_league:
                    print(f"\n📊 League breakdown: {len(by_league)} leagues")
                    for league_id, stats in sorted(
                        by_league.items(), key=lambda x: x[1].get("total", 0), reverse=True
                    )[:5]:
                        print(
                            f"   {stats.get('name', league_id)}: {stats.get('accuracy', 0)*100:.1f}% ({stats.get('total', 0)} matches)"
                        )
                return True
            else:
                print("⚠️  Railway database is empty, re-pushing data...")
        else:
            print(f"❌ Failed to check Railway: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Error checking Railway: {e}")
        return False

    # Get data from local database
    with get_db() as conn:
        cursor = conn.cursor()

        # First, get all predictions with their full data
        cursor.execute(
            """
            SELECT
                fixture_id, home_team, away_team, home_team_id, away_team_id,
                league_id, league_name, match_date,
                home_win_prob, draw_prob, away_win_prob,
                predicted_outcome, confidence, confidence_level,
                predicted_scoreline, btts_prob, over25_prob,
                result_home_goals, result_away_goals, match_status
            FROM predictions
            WHERE evaluated = 1
            AND result_home_goals IS NOT NULL
        """
        )

        predictions = []
        results = []

        for row in cursor.fetchall():
            fixture_id = row[0]

            # Add prediction data
            predictions.append(
                {
                    "fixture_id": fixture_id,
                    "home_team": row[1],
                    "away_team": row[2],
                    "home_team_id": row[3],
                    "away_team_id": row[4],
                    "league_id": row[5],
                    "league_name": row[6],
                    "match_date": row[7],
                    "prediction": {
                        "home_win_prob": row[8],
                        "draw_prob": row[9],
                        "away_win_prob": row[10],
                        "predicted_outcome": row[11],
                        "confidence": row[12],
                        "btts_prob": row[15],
                        "over25_prob": row[16],
                    },
                }
            )

            # Add result data
            results.append(
                {
                    "fixture_id": fixture_id,
                    "home_goals": row[17],
                    "away_goals": row[18],
                    "status": row[19] or "FT",
                }
            )

    if not predictions:
        print("❌ No local data to push")
        return False

    print(f"\n📤 Pushing {len(predictions)} predictions to Railway...")

    # Push predictions first (so Railway knows about them)
    for pred in predictions:
        try:
            # Flatten the prediction data to match PredictionLog schema
            payload = {
                "fixture_id": pred["fixture_id"],
                "home_team": pred["home_team"],
                "away_team": pred["away_team"],
                "home_team_id": pred["home_team_id"],
                "away_team_id": pred["away_team_id"],
                "league_id": pred["league_id"],
                "league_name": pred["league_name"],
                "match_date": pred["match_date"],
                "home_win_prob": pred["prediction"]["home_win_prob"] or 0.33,
                "draw_prob": pred["prediction"]["draw_prob"] or 0.33,
                "away_win_prob": pred["prediction"]["away_win_prob"] or 0.33,
                "btts_prob": pred["prediction"]["btts_prob"],
                "over25_prob": pred["prediction"]["over25_prob"],
            }

            resp = requests.post(
                f"{ML_API_URL}/api/metrics/log-prediction", json=payload, timeout=5
            )
            if resp.status_code != 200:
                print(f"⚠️  Failed to log prediction {pred['fixture_id']}: {resp.status_code}")
        except Exception as e:
            print(f"⚠️  Error logging {pred['fixture_id']}: {e}")

    print(f"\n📤 Pushing {len(results)} results...")

    # Push results in bulk
    try:
        response = requests.post(
            f"{ML_API_URL}/api/metrics/record-results-bulk", json={"results": results}, timeout=120
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Successfully pushed!")
            print(f"   Processed: {data.get('processed', 0)}")
            print(f"   Evaluated: {data.get('evaluated', 0)}")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"   {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    verify_and_fix()
