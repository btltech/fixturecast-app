#!/usr/bin/env python3
"""
Update historical data with recent match results.
Fetches finished matches from the last N days for all featured leagues.
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta

from typing import Optional

# Add parent path for imports
sys.path.append(os.path.dirname(__file__))

try:
    from .api_client import ApiClient
    from .league_catalog import get_featured_league_map, get_league_season
except ImportError:
    from api_client import ApiClient
    from league_catalog import get_featured_league_map, get_league_season

FEATURED_LEAGUES = get_featured_league_map()

DATA_DIR = os.path.join(os.path.dirname(__file__), "../data/historical")


def load_config():
    """Load API configuration."""
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    with open(config_path) as f:
        return json.load(f)


def get_existing_fixture_ids(league_id: int) -> set:
    """Get set of fixture IDs we already have for a league."""
    filepath = os.path.join(DATA_DIR, f"league_{league_id}_all.json")
    if not os.path.exists(filepath):
        return set()

    try:
        with open(filepath) as f:
            data = json.load(f)
        return {m.get("fixture", {}).get("id") for m in data if isinstance(m, dict)}
    except Exception as e:
        print(f"  Warning: Could not read existing data: {e}")
        return set()


def save_league_data(league_id: int, matches: list):
    """Save matches to the league's combined data file."""
    filepath = os.path.join(DATA_DIR, f"league_{league_id}_all.json")

    # Load existing data
    existing = []
    if os.path.exists(filepath):
        try:
            with open(filepath) as f:
                existing = json.load(f)
        except:
            pass

    # Get existing fixture IDs
    existing_ids = {m.get("fixture", {}).get("id") for m in existing if isinstance(m, dict)}

    # Add new matches
    new_count = 0
    for match in matches:
        fixture_id = match.get("fixture", {}).get("id")
        if fixture_id and fixture_id not in existing_ids:
            existing.append(match)
            existing_ids.add(fixture_id)
            new_count += 1

    # Sort by date
    existing.sort(key=lambda x: x.get("fixture", {}).get("date", ""), reverse=True)

    # Save
    with open(filepath, "w") as f:
        json.dump(existing, f, indent=2)

    return new_count


def update_combined_file():
    """Update the all_leagues_combined.json file."""
    combined = []

    for league_id in FEATURED_LEAGUES.keys():
        filepath = os.path.join(DATA_DIR, f"league_{league_id}_all.json")
        if os.path.exists(filepath):
            try:
                with open(filepath) as f:
                    data = json.load(f)
                combined.extend(data)
            except:
                pass

    # Sort by date
    combined.sort(key=lambda x: x.get("fixture", {}).get("date", ""), reverse=True)

    # Save
    filepath = os.path.join(DATA_DIR, "all_leagues_combined.json")
    with open(filepath, "w") as f:
        json.dump(combined, f, indent=2)

    return len(combined)


def collect_recent_results(days: int = 14, season: Optional[int] = None):
    """Collect recent finished matches for all featured leagues."""

    print(f"🔄 Starting data collection for {len(FEATURED_LEAGUES)} leagues...")
    season_label = season if season is not None else "dynamic per league"
    print(f"   Looking for matches from the last {days} days (season {season_label})")
    print()

    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)

    # Initialize API Client
    config = load_config()
    client = ApiClient(config)

    total_new = 0

    for league_id, league_name in FEATURED_LEAGUES.items():
        print(f"📊 {league_name} (ID: {league_id})...")

        try:
            resolved_season = season if season is not None else get_league_season(league_id)
            # Fetch finished matches for the current season
            params = {
                "league": league_id,
                "season": resolved_season,
                "status": "FT",  # Finished matches only
            }

            response = client._call_api("fixtures", params, "long")

            if not response or "response" not in response:
                print(f"   ❌ Failed to fetch data")
                continue

            matches = response["response"]

            if not matches:
                print(f"   ⚠️ No finished matches found")
                continue

            # Save to league file and count new matches
            new_count = save_league_data(league_id, matches)
            total_new += new_count

            # Find latest date
            dates = [
                m.get("fixture", {}).get("date", "")[:10]
                for m in matches
                if m.get("fixture", {}).get("date")
            ]
            latest = max(dates) if dates else "N/A"

            print(f"   ✅ {len(matches)} matches found, {new_count} new, latest: {latest}")

        except Exception as e:
            print(f"   ❌ Error: {e}")

        # Rate limiting
        time.sleep(0.5)

    # Update combined file
    print()
    print("📦 Updating combined data file...")
    total_combined = update_combined_file()

    print()
    print("=" * 50)
    print(f"✅ Collection complete!")
    print(f"   New matches added: {total_new}")
    print(f"   Total matches in combined file: {total_combined}")
    print("=" * 50)

    return total_new


def collect_full_season(season: Optional[int] = None):
    """Collect full season data for all leagues."""
    print(f"🔄 Collecting FULL season {season} data for all leagues...")
    return collect_recent_results(days=365, season=season)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Update historical match data")
    parser.add_argument("--days", type=int, default=14, help="Number of days to look back")
    parser.add_argument(
        "--season", type=int, default=None, help="Season to collect (defaults to the active season for each league)"
    )
    parser.add_argument("--full", action="store_true", help="Collect full season data")

    args = parser.parse_args()

    if args.full:
        collect_full_season(args.season)
    else:
        collect_recent_results(args.days, args.season)
