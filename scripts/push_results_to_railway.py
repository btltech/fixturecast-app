#!/usr/bin/env python3
"""
Push local database results to Railway ML API
"""
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import get_db

ML_API_URL = "https://ml-api-production-6cfc.up.railway.app"


def push_results():
    """Push evaluated results from local DB to Railway."""

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT fixture_id, result_home_goals, result_away_goals, match_status
            FROM predictions
            WHERE evaluated = 1
            AND result_home_goals IS NOT NULL
        """
        )

        results = []
        for row in cursor.fetchall():
            results.append(
                {
                    "fixture_id": row[0],
                    "home_goals": row[1],
                    "away_goals": row[2],
                    "status": row[3] or "FT",
                }
            )

    if not results:
        print("No results to push")
        return

    print(f"📤 Pushing {len(results)} results to Railway...")

    try:
        response = requests.post(
            f"{ML_API_URL}/api/metrics/record-results-bulk", json={"results": results}, timeout=120
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Successfully pushed!")
            print(f"   Processed: {data.get('processed', 0)}")
            print(f"   Evaluated: {data.get('evaluated', 0)}")
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"   {response.text[:200]}")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    push_results()
