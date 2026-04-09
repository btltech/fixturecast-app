#!/usr/bin/env python3
"""Check Railway database for predictions"""
import requests

ML_API_URL = "https://ml-api-production-6cfc.up.railway.app"

# Check direct query endpoints
print("🔍 Checking Railway database...")

# Try different query approaches
endpoints = [
    ("/api/metrics/summary?days=365", "365-day summary"),
    ("/api/metrics/summary?days=3650", "10-year summary"),
    ("/api/feedback/performance", "feedback performance"),
]

for endpoint, name in endpoints:
    try:
        response = requests.get(f"{ML_API_URL}{endpoint}", timeout=10)
        if response.status_code == 200:
            data = response.json()

            # Extract relevant metrics
            if "365_day" in data:
                total = data["365_day"].get("total_predictions", 0)
                correct = data["365_day"].get("correct_predictions", 0)
                print(f"\n✅ {name}: {total} total, {correct} correct")

                by_league = data.get("by_league", {})
                if by_league:
                    print(f"   Leagues: {len(by_league)}")
                    for league_id in list(by_league.keys())[:3]:
                        league = by_league[league_id]
                        print(
                            f"      {league.get('name', league_id)}: {league.get('total', 0)} matches"
                        )

            elif "overall" in data:
                total = data["overall"].get("total", 0)
                correct = data["overall"].get("correct", 0)
                accuracy = data["overall"].get("accuracy", 0)
                print(
                    f"\n✅ {name}: {total} total, {correct} correct, {accuracy*100:.1f}% accuracy"
                )

                by_league = data.get("by_league", {})
                if by_league:
                    print(f"   Leagues: {len(by_league)}")
                    for league_id in list(by_league.keys())[:3]:
                        league = by_league[league_id]
                        print(
                            f"      {league.get('name', league_id)}: {league.get('total', 0)} matches"
                        )
                else:
                    print(f"   ⚠️  No league breakdown available")
        else:
            print(f"\n❌ {name}: HTTP {response.status_code}")
    except Exception as e:
        print(f"\n❌ {name}: {e}")
