#!/usr/bin/env python3
"""
Daily Results Collector for FixtureCast
Collects FINISHED matches and evaluates predictions for all 3 markets:
- 1X2 (Match Result)
- BTTS (Both Teams To Score)
- Over 2.5 Goals

Run daily to update accuracy metrics.
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List
from zoneinfo import ZoneInfo

import httpx

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import PredictionDB, init_database
from backend.league_catalog import get_featured_league_map, get_league_season

# API URLs
ML_API_URL = os.environ.get("ML_API_URL", "https://ml-api-production-6cfc.up.railway.app")
BACKEND_API_URL = os.environ.get(
    "BACKEND_API_URL", "https://backend-api-production-7b7d.up.railway.app"
)

LEAGUES = list(get_featured_league_map().items())

UK_TZ = ZoneInfo("Europe/London")


def collect_finished_matches(days_back: int = 7) -> Dict:
    """Collect finished matches and evaluate all 3 markets."""
    init_database()

    uk_now = datetime.now(UK_TZ)
    dates = [(uk_now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days_back)]

    stats = {
        "matches": 0,
        "match_result_correct": 0,
        "btts_correct": 0,
        "over25_correct": 0,
        "exact_score_correct": 0,
    }

    print(f"🚀 FixtureCast Results Collector")
    print(f"   Time: {uk_now.strftime('%Y-%m-%d %H:%M:%S')} UK")
    print(f"📊 Collecting FINISHED matches for last {days_back} days...")

    with httpx.Client(timeout=90) as client:
        for check_date in dates:
            print(f"\n📅 {check_date}")

            for league_id, league_name in LEAGUES:
                try:
                    season = get_league_season(league_id, check_date)
                    resp = client.get(
                        f"{BACKEND_API_URL}/api/fixtures",
                        params={"league": league_id, "date": check_date, "season": season},
                        timeout=30,
                    )
                    if resp.status_code != 200:
                        continue

                    fixtures = resp.json().get("response", [])
                    finished = [
                        f
                        for f in fixtures
                        if f["fixture"]["status"]["short"] in ["FT", "AET", "PEN"]
                    ]

                    if not finished:
                        continue

                    print(f"   📍 {league_name}: {len(finished)} finished")

                    for f in finished:
                        fixture_id = f["fixture"]["id"]
                        home = f["teams"]["home"]["name"]
                        away = f["teams"]["away"]["name"]
                        home_id = f["teams"]["home"]["id"]
                        away_id = f["teams"]["away"]["id"]
                        match_date = f["fixture"]["date"]
                        status = f["fixture"]["status"]["short"]
                        home_goals = f["goals"]["home"]
                        away_goals = f["goals"]["away"]

                        # Get prediction
                        try:
                            pred_resp = client.get(
                                f"{ML_API_URL}/api/prediction/{fixture_id}",
                                params={
                                    "league": league_id,
                                    "season": get_league_season(league_id, match_date),
                                },
                                timeout=90,
                            )
                            if pred_resp.status_code != 200:
                                continue

                            pred_data = pred_resp.json()
                            p = pred_data.get("prediction", {})

                            # Log prediction
                            PredictionDB.log_prediction(
                                fixture_id=fixture_id,
                                home_team=home,
                                away_team=away,
                                league_id=league_id,
                                match_date=match_date,
                                prediction={
                                    "home_win_prob": p.get("home_win_prob", 0),
                                    "draw_prob": p.get("draw_prob", 0),
                                    "away_win_prob": p.get("away_win_prob", 0),
                                    "predicted_scoreline": p.get("predicted_scoreline"),
                                    "btts_prob": p.get("btts_prob", 0.5),
                                    "over25_prob": p.get("over25_prob", 0.5),
                                },
                                model_breakdown=p.get("model_breakdown", {}),
                                home_team_id=home_id,
                                away_team_id=away_id,
                                league_name=league_name,
                            )

                            # Record result
                            evaluation = PredictionDB.record_result(
                                fixture_id=fixture_id,
                                home_goals=home_goals,
                                away_goals=away_goals,
                                status=status,
                            )

                            if evaluation:
                                stats["matches"] += 1

                                mr = "✅" if evaluation.get("outcome_correct") else "❌"
                                btts = "✅" if evaluation.get("btts_correct") else "❌"
                                o25 = "✅" if evaluation.get("over25_correct") else "❌"

                                if evaluation.get("outcome_correct"):
                                    stats["match_result_correct"] += 1
                                if evaluation.get("btts_correct"):
                                    stats["btts_correct"] += 1
                                if evaluation.get("over25_correct"):
                                    stats["over25_correct"] += 1
                                if evaluation.get("exact_score"):
                                    stats["exact_score_correct"] += 1

                                print(
                                    f"      {home} {home_goals}-{away_goals} {away} | 1X2:{mr} BTTS:{btts} O2.5:{o25}"
                                )

                        except Exception as e:
                            print(f"      ⚠️ Error: {str(e)[:40]}")

                except Exception as e:
                    continue

    return stats


def print_summary(stats: Dict):
    """Print results summary."""
    print("\n" + "=" * 60)
    print("📊 RESULTS SUMMARY")
    print("=" * 60)

    total = stats["matches"]
    if total > 0:
        print(f"Matches evaluated: {total}")
        print(
            f"\n🎯 1X2 (Match Result): {stats['match_result_correct']}/{total} ({stats['match_result_correct']/total*100:.1f}%)"
        )
        print(f"⚽ BTTS: {stats['btts_correct']}/{total} ({stats['btts_correct']/total*100:.1f}%)")
        print(
            f"📊 Over 2.5: {stats['over25_correct']}/{total} ({stats['over25_correct']/total*100:.1f}%)"
        )
        print(
            f"🎲 Exact Score: {stats['exact_score_correct']}/{total} ({stats['exact_score_correct']/total*100:.1f}%)"
        )

    # Database metrics
    metrics = PredictionDB.get_metrics_summary(days=7)
    print(f"\n📈 7-Day Database Metrics:")
    print(f"   Total evaluated: {metrics.get('total_predictions', 0)}")
    if "match_result" in metrics:
        print(f"   1X2: {metrics['match_result']['accuracy']*100:.1f}%")
    if "btts" in metrics:
        print(f"   BTTS: {metrics['btts']['accuracy']*100:.1f}%")
    if "over25" in metrics:
        print(f"   Over 2.5: {metrics['over25']['accuracy']*100:.1f}%")

    print("\n✅ Collection complete!")


def main():
    stats = collect_finished_matches(days_back=3)
    print_summary(stats)


if __name__ == "__main__":
    main()
