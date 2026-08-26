"""
Collect historical data for all supported leagues.
This script fetches match data and team statistics for model training.
"""

import json
import os
import sys
import time

try:
    from .api_client import ApiClient
    from .league_catalog import get_featured_league_map, get_training_seasons
except ImportError:
    from api_client import ApiClient
    from league_catalog import get_featured_league_map, get_training_seasons

LEAGUES = get_featured_league_map()

DATA_DIR = os.path.join(os.path.dirname(__file__), "../data/historical")


def collect_league_data(client, league_id, league_name, seasons):
    """Collect match and stats data for a single league."""
    print(f"\n{'='*60}")
    print(f"Collecting data for {league_name} (ID: {league_id})")
    print(f"Seasons: {seasons}")
    print(f"{'='*60}")

    all_matches = []

    for season in seasons:
        print(f"\n  📅 Season {season}...")

        # Fetch finished matches
        params = {"league": league_id, "season": season, "status": "FT"}

        try:
            response = client._call_api("fixtures", params, "long")

            if not response or "response" not in response:
                print(f"    ⚠️ No data for season {season}")
                continue

            matches = response["response"]
            print(f"    ✅ Found {len(matches)} matches")

            if len(matches) == 0:
                continue

            # Save season data
            season_file = os.path.join(DATA_DIR, f"season_{season}_{league_id}.json")
            with open(season_file, "w") as f:
                json.dump(matches, f, indent=2)

            all_matches.extend(matches)

            # Get unique team IDs
            team_ids = set()
            for m in matches:
                team_ids.add(m["teams"]["home"]["id"])
                team_ids.add(m["teams"]["away"]["id"])

            print(f"    📊 Fetching stats for {len(team_ids)} teams...")

            season_stats = {}
            for team_id in team_ids:
                stats = client.get_team_stats(team_id, league_id, season)
                if stats:
                    season_stats[team_id] = stats
                time.sleep(0.15)  # Rate limiting

            # Save stats
            stats_file = os.path.join(DATA_DIR, f"stats_{season}_{league_id}.json")
            with open(stats_file, "w") as f:
                json.dump(season_stats, f, indent=2)

            print(f"    ✅ Saved {len(season_stats)} team stats")

        except Exception as e:
            print(f"    ❌ Error: {e}")
            continue

        # Small delay between seasons
        time.sleep(0.5)

    return len(all_matches)


def main():
    print("🚀 Historical Data Collection for FixtureCast")
    print("=" * 60)

    # Parse arguments - can specify specific leagues
    if len(sys.argv) > 1:
        target_leagues = [int(x) for x in sys.argv[1:]]
        leagues_to_collect = {k: v for k, v in LEAGUES.items() if k in target_leagues}
    else:
        leagues_to_collect = LEAGUES

    print(f"Collecting data for {len(leagues_to_collect)} leagues")

    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)

    # Initialize API Client
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    with open(config_path) as f:
        config = json.load(f)

    client = ApiClient(config)

    total_matches = 0
    results = {}

    for league_id, league_name in leagues_to_collect.items():
        seasons = get_training_seasons(league_id, start_year=2020)
        match_count = collect_league_data(client, league_id, league_name, seasons)
        total_matches += match_count
        results[league_name] = match_count

        # Delay between leagues to avoid rate limiting
        time.sleep(1)

    # Summary
    print("\n" + "=" * 60)
    print("📊 COLLECTION SUMMARY")
    print("=" * 60)
    for league, count in results.items():
        print(f"  {league}: {count} matches")
    print(f"\n  TOTAL: {total_matches} matches")
    print("=" * 60)


if __name__ == "__main__":
    main()
