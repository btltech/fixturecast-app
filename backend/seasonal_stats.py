import os
import re
import json

# ============================================
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "historical")


def load_all_seasonal_stats():
    """
    Load team statistics from stats files for enhanced predictions.
    Returns: {season: {team_id: team_stats}}
    """
    all_stats = {}

    try:
        filenames = os.listdir(DATA_DIR)
    except Exception:
        filenames = []

    years = set()
    pattern = re.compile(r"^stats_(\d{4})(?:_\d+)?\.json$")
    for name in filenames:
        m = pattern.match(name)
        if m:
            try:
                years.add(int(m.group(1)))
            except ValueError:
                continue

    for year in sorted(years):
        combined_path = os.path.join(DATA_DIR, f"stats_{year}.json")
        paths = []
        if os.path.exists(combined_path):
            paths = [combined_path]
        else:
            paths = [
                os.path.join(DATA_DIR, name)
                for name in filenames
                if name.startswith(f"stats_{year}_") and name.endswith(".json")
            ]

        if not paths:
            continue

        stats_by_team = {}
        for filepath in sorted(paths):
            try:
                with open(filepath) as f:
                    season_stats = json.load(f)

                for team_id, data in season_stats.items():
                    try:
                        team_data = data.get("response", data)  # Handle both formats
                        if isinstance(team_data, dict):
                            stats_by_team[int(team_id)] = {
                                "form": team_data.get("form", ""),
                                "fixtures": team_data.get("fixtures", {}),
                                "goals_for": team_data.get("goals", {}).get("for", {}),
                                "goals_against": team_data.get("goals", {}).get("against", {}),
                                "biggest": team_data.get("biggest", {}),
                                "clean_sheet": team_data.get("clean_sheet", {}),
                                "failed_to_score": team_data.get("failed_to_score", {}),
                                "penalty": team_data.get("penalty", {}),
                                "lineups": team_data.get("lineups", []),
                                "cards": team_data.get("cards", {}),
                            }
                    except (KeyError, TypeError, ValueError):
                        continue
            except Exception as e:
                print(f"  Warning: Failed to load {os.path.basename(filepath)}: {e}")

        if stats_by_team:
            all_stats[year] = stats_by_team
            print(f"  Loaded stats for {len(stats_by_team)} teams from {year}")

    return all_stats


def extract_seasonal_features(team_stats, prefix="home"):
    """
    Extract all features from team seasonal stats.
    Returns a dict of numeric features with prefix (home_ or away_).
    """
    features = {}

    if not team_stats:
        # Return default neutral features
        defaults = {
            f"{prefix}_stat_home_win_rate": 0.4,
            f"{prefix}_stat_away_win_rate": 0.3,
            f"{prefix}_stat_home_draw_rate": 0.3,
            f"{prefix}_stat_away_draw_rate": 0.3,
            f"{prefix}_stat_goals_for_home_avg": 1.3,
            f"{prefix}_stat_goals_for_away_avg": 1.0,
            f"{prefix}_stat_goals_against_home_avg": 1.0,
            f"{prefix}_stat_goals_against_away_avg": 1.3,
            f"{prefix}_stat_clean_sheet_home_rate": 0.3,
            f"{prefix}_stat_clean_sheet_away_rate": 0.2,
            f"{prefix}_stat_failed_to_score_home_rate": 0.2,
            f"{prefix}_stat_failed_to_score_away_rate": 0.3,
            f"{prefix}_stat_penalty_success_rate": 0.75,
            f"{prefix}_stat_biggest_win_streak": 3,
            f"{prefix}_stat_biggest_lose_streak": 2,
            f"{prefix}_stat_goals_0_15_pct": 0.1,
            f"{prefix}_stat_goals_16_30_pct": 0.15,
            f"{prefix}_stat_goals_31_45_pct": 0.15,
            f"{prefix}_stat_goals_46_60_pct": 0.2,
            f"{prefix}_stat_goals_61_75_pct": 0.2,
            f"{prefix}_stat_goals_76_90_pct": 0.2,
            f"{prefix}_stat_conceded_0_15_pct": 0.1,
            f"{prefix}_stat_conceded_46_60_pct": 0.2,
            f"{prefix}_stat_conceded_76_90_pct": 0.2,
            f"{prefix}_stat_yellow_cards_per_game": 2.0,
            f"{prefix}_stat_red_cards_per_game": 0.1,
            f"{prefix}_stat_primary_formation": 0,
            f"{prefix}_stat_form_win_pct": 0.4,
        }
        return defaults

    # FIXTURES DATA
    fixtures = team_stats.get("fixtures", {})
    played = fixtures.get("played", {})
    wins = fixtures.get("wins", {})
    draws = fixtures.get("draws", {})
    loses = fixtures.get("loses", {})

    total_played = played.get("total", 38) or 38
    home_played = played.get("home", 19) or 19
    away_played = played.get("away", 19) or 19

    # Win/draw/loss rates by venue
    features[f"{prefix}_stat_home_win_rate"] = (wins.get("home", 0) or 0) / home_played
    features[f"{prefix}_stat_away_win_rate"] = (wins.get("away", 0) or 0) / away_played
    features[f"{prefix}_stat_home_draw_rate"] = (draws.get("home", 0) or 0) / home_played
    features[f"{prefix}_stat_away_draw_rate"] = (draws.get("away", 0) or 0) / away_played
    features[f"{prefix}_stat_home_loss_rate"] = (loses.get("home", 0) or 0) / home_played
    features[f"{prefix}_stat_away_loss_rate"] = (loses.get("away", 0) or 0) / away_played
    features[f"{prefix}_stat_total_wins"] = wins.get("total", 0) or 0
    features[f"{prefix}_stat_total_draws"] = draws.get("total", 0) or 0
    features[f"{prefix}_stat_total_losses"] = loses.get("total", 0) or 0

    # GOALS FOR DATA
    goals_for = team_stats.get("goals_for", {})
    gf_avg = goals_for.get("average", {})
    gf_minute = goals_for.get("minute", {})
    gf_total = goals_for.get("total", {})

    features[f"{prefix}_stat_goals_for_home_avg"] = float(gf_avg.get("home", "1.3") or "1.3")
    features[f"{prefix}_stat_goals_for_away_avg"] = float(gf_avg.get("away", "1.0") or "1.0")
    features[f"{prefix}_stat_goals_for_total"] = gf_total.get("total", 50) or 50

    # Goals by minute period
    for period in ["0-15", "16-30", "31-45", "46-60", "61-75", "76-90", "91-105"]:
        period_data = gf_minute.get(period, {})
        pct_str = period_data.get("percentage", "0%") or "0%"
        try:
            pct = float(pct_str.replace("%", "")) / 100
        except (ValueError, AttributeError):
            pct = 0
        period_key = period.replace("-", "_")
        features[f"{prefix}_stat_goals_{period_key}_pct"] = pct

    # GOALS AGAINST DATA
    goals_against = team_stats.get("goals_against", {})
    ga_avg = goals_against.get("average", {})
    ga_minute = goals_against.get("minute", {})
    ga_total = goals_against.get("total", {})

    features[f"{prefix}_stat_goals_against_home_avg"] = float(ga_avg.get("home", "1.0") or "1.0")
    features[f"{prefix}_stat_goals_against_away_avg"] = float(ga_avg.get("away", "1.3") or "1.3")
    features[f"{prefix}_stat_goals_against_total"] = ga_total.get("total", 50) or 50

    # Conceded by minute period
    for period in ["0-15", "46-60", "76-90"]:
        period_data = ga_minute.get(period, {})
        pct_str = period_data.get("percentage", "0%") or "0%"
        try:
            pct = float(pct_str.replace("%", "")) / 100
        except (ValueError, AttributeError):
            pct = 0
        period_key = period.replace("-", "_")
        features[f"{prefix}_stat_conceded_{period_key}_pct"] = pct

    # BIGGEST WINS/LOSSES
    biggest = team_stats.get("biggest", {})
    streak = biggest.get("streak", {})

    features[f"{prefix}_stat_biggest_win_streak"] = streak.get("wins", 1) or 1
    features[f"{prefix}_stat_biggest_lose_streak"] = streak.get("loses", 1) or 1
    features[f"{prefix}_stat_biggest_draw_streak"] = streak.get("draws", 1) or 1

    # CLEAN SHEET DATA
    clean_sheet = team_stats.get("clean_sheet", {})
    features[f"{prefix}_stat_clean_sheet_home_rate"] = (
        clean_sheet.get("home", 0) or 0
    ) / home_played
    features[f"{prefix}_stat_clean_sheet_away_rate"] = (
        clean_sheet.get("away", 0) or 0
    ) / away_played
    features[f"{prefix}_stat_clean_sheet_total"] = clean_sheet.get("total", 10) or 10

    # FAILED TO SCORE DATA
    fts = team_stats.get("failed_to_score", {})
    features[f"{prefix}_stat_failed_to_score_home_rate"] = (fts.get("home", 0) or 0) / home_played
    features[f"{prefix}_stat_failed_to_score_away_rate"] = (fts.get("away", 0) or 0) / away_played
    features[f"{prefix}_stat_failed_to_score_total"] = fts.get("total", 8) or 8

    # PENALTY DATA
    penalty = team_stats.get("penalty", {})
    scored = penalty.get("scored", {})
    missed = penalty.get("missed", {})
    pen_scored = scored.get("total", 0) or 0
    pen_missed = missed.get("total", 0) or 0
    if pen_scored + pen_missed > 0:
        features[f"{prefix}_stat_penalty_success_rate"] = pen_scored / (pen_scored + pen_missed)
    else:
        features[f"{prefix}_stat_penalty_success_rate"] = 0.75

    # LINEUPS/FORMATIONS
    lineups = team_stats.get("lineups", [])
    if lineups:
        formation_map = {
            "4-3-3": 1,
            "4-4-2": 2,
            "3-4-3": 3,
            "4-2-3-1": 4,
            "3-5-2": 5,
            "4-1-4-1": 6,
            "5-3-2": 7,
            "3-4-2-1": 8,
            "4-5-1": 9,
            "5-4-1": 10,
        }
        primary_formation = lineups[0].get("formation", "4-3-3") if lineups else "4-3-3"
        features[f"{prefix}_stat_primary_formation"] = formation_map.get(primary_formation, 0)
        features[f"{prefix}_stat_formation_consistency"] = (
            lineups[0].get("played", 20) / total_played if lineups else 0.5
        )
    else:
        features[f"{prefix}_stat_primary_formation"] = 0
        features[f"{prefix}_stat_formation_consistency"] = 0.5

    # CARDS DATA
    cards = team_stats.get("cards", {})
    yellow = cards.get("yellow", {})
    red = cards.get("red", {})

    yellow_total = sum(
        (yellow.get(period, {}).get("total", 0) or 0)
        for period in ["0-15", "16-30", "31-45", "46-60", "61-75", "76-90", "91-105"]
    )
    red_total = sum(
        (red.get(period, {}).get("total", 0) or 0)
        for period in ["0-15", "16-30", "31-45", "46-60", "61-75", "76-90", "91-105"]
    )
    features[f"{prefix}_stat_yellow_cards_per_game"] = yellow_total / total_played
    features[f"{prefix}_stat_red_cards_per_game"] = red_total / total_played

    # FORM DATA
    form_str = team_stats.get("form", "")
    if form_str:
        form_wins = form_str.count("W")
        form_draws = form_str.count("D")
        form_len = len(form_str) or 1
        features[f"{prefix}_stat_form_win_pct"] = form_wins / form_len
        features[f"{prefix}_stat_form_draw_pct"] = form_draws / form_len
        # Recent 5 games
        recent = form_str[-5:]
        features[f"{prefix}_stat_recent_form_win_pct"] = (
            recent.count("W") / len(recent) if recent else 0.4
        )
    else:
        features[f"{prefix}_stat_form_win_pct"] = 0.4
        features[f"{prefix}_stat_form_draw_pct"] = 0.3
        features[f"{prefix}_stat_recent_form_win_pct"] = 0.4

    return features


def enrich_features_with_seasonal_stats(features, home_id, away_id, seasonal_stats):
    """
    Enrich feature dict with seasonal statistics for both teams.
    Uses most recent available season data.

    CRITICAL: This function must add features with the EXACT names that
    the trained models expect (home_win_rate, home_ppg, etc.)
    """
    enhanced = dict(features)  # Copy original

    # Find best available stats for each team (most recent season)
    home_stats = None
    away_stats = None

    for year in sorted(seasonal_stats.keys(), reverse=True):
        if home_id in seasonal_stats.get(year, {}) and not home_stats:
            home_stats = seasonal_stats[year][home_id]
        if away_id in seasonal_stats.get(year, {}) and not away_stats:
            away_stats = seasonal_stats[year][away_id]
        if home_stats and away_stats:
            break

    # Extract and add features with correct prefixes
    home_features = extract_seasonal_features(home_stats, prefix="home")
    away_features = extract_seasonal_features(away_stats, prefix="away")

    enhanced.update(home_features)
    enhanced.update(away_features)

    # ============================================================
    # CRITICAL: Add derived features with EXACT names models expect
    # These are the 50+ features the trained models need
    # ============================================================

    # Get base values from existing features or defaults
    home_pos = enhanced.get("home_league_pos", 10)
    away_pos = enhanced.get("away_league_pos", 10)
    home_pts = enhanced.get("home_league_points", 30)
    away_pts = enhanced.get("away_league_points", 30)
    home_matches = enhanced.get("home_total_matches", 20)
    away_matches = enhanced.get("away_total_matches", 20)

    # Form stats
    home_wins_10 = enhanced.get("home_wins_last10", 5)
    home_draws_10 = enhanced.get("home_draws_last10", 3)
    home_losses_10 = enhanced.get("home_losses_last10", 2)
    away_wins_10 = enhanced.get("away_wins_last10", 5)
    away_draws_10 = enhanced.get("away_draws_last10", 3)
    away_losses_10 = enhanced.get("away_losses_last10", 2)

    home_gf_10 = enhanced.get("home_goals_for_last10", 13)
    home_ga_10 = enhanced.get("home_goals_against_last10", 10)
    away_gf_10 = enhanced.get("away_goals_for_last10", 12)
    away_ga_10 = enhanced.get("away_goals_against_last10", 11)

    home_gf_avg = enhanced.get("home_goals_for_avg", 1.3)
    home_ga_avg = enhanced.get("home_goals_against_avg", 1.0)
    away_gf_avg = enhanced.get("away_goals_for_avg", 1.2)
    away_ga_avg = enhanced.get("away_goals_against_avg", 1.3)

    # 1. Position and Points differences
    enhanced["position_diff"] = away_pos - home_pos  # Positive = home is better
    enhanced["points_diff"] = home_pts - away_pts

    # 2. Points Per Game (PPG)
    enhanced["home_ppg"] = home_pts / max(home_matches, 1)
    enhanced["away_ppg"] = away_pts / max(away_matches, 1)

    # PPG at specific venue (using seasonal stats if available)
    home_home_win_rate = home_features.get("home_stat_home_win_rate", 0.5)
    away_away_win_rate = away_features.get("away_stat_away_win_rate", 0.3)
    home_home_draw_rate = home_features.get("home_stat_home_draw_rate", 0.25)
    away_away_draw_rate = away_features.get("away_stat_away_draw_rate", 0.25)

    enhanced["home_ppg_home"] = home_home_win_rate * 3 + home_home_draw_rate * 1
    enhanced["away_ppg_away"] = away_away_win_rate * 3 + away_away_draw_rate * 1

    # 3. Form last 5 (already have last 10)
    enhanced["home_form_last5"] = enhanced.get("home_form_last5", home_wins_10 * 3 // 2)
    enhanced["away_form_last5"] = enhanced.get("away_form_last5", away_wins_10 * 3 // 2)
    enhanced["home_wins_last5"] = min(home_wins_10, 5)
    enhanced["away_wins_last5"] = min(away_wins_10, 5)

    # 4. Goals at specific venue
    enhanced["home_gf_home_avg"] = home_features.get("home_stat_goals_for_home_avg", home_gf_avg)
    enhanced["home_ga_home_avg"] = home_features.get(
        "home_stat_goals_against_home_avg", home_ga_avg
    )
    enhanced["away_gf_away_avg"] = away_features.get("away_stat_goals_for_away_avg", away_gf_avg)
    enhanced["away_ga_away_avg"] = away_features.get(
        "away_stat_goals_against_away_avg", away_ga_avg
    )

    # 5. Goal difference
    enhanced["home_gd"] = home_gf_10 - home_ga_10
    enhanced["away_gd"] = away_gf_10 - away_ga_10
    enhanced["home_gd_per_game"] = home_gf_avg - home_ga_avg
    enhanced["away_gd_per_game"] = away_gf_avg - away_ga_avg

    # 6. Goals last 5 (estimate from last 10)
    enhanced["home_goals_for_last5"] = home_gf_10 // 2
    enhanced["away_goals_for_last5"] = away_gf_10 // 2
    enhanced["home_goals_against_last5"] = home_ga_10 // 2
    enhanced["away_goals_against_last5"] = away_ga_10 // 2

    # 7. Win rates - CRITICAL for Bayesian model
    total_home_games = home_wins_10 + home_draws_10 + home_losses_10
    total_away_games = away_wins_10 + away_draws_10 + away_losses_10

    enhanced["home_win_rate"] = home_wins_10 / max(total_home_games, 1)
    enhanced["away_win_rate"] = away_wins_10 / max(total_away_games, 1)
    enhanced["home_home_win_rate"] = home_home_win_rate
    enhanced["away_away_win_rate"] = away_away_win_rate

    # 8. Clean sheet rates
    enhanced["home_clean_sheet_rate"] = home_features.get(
        "home_stat_clean_sheet_home_rate", 0.3 if home_ga_avg < 1.0 else 0.2
    )
    enhanced["away_clean_sheet_rate"] = away_features.get(
        "away_stat_clean_sheet_away_rate", 0.2 if away_ga_avg < 1.0 else 0.15
    )
    enhanced["home_cs_home_rate"] = enhanced["home_clean_sheet_rate"]
    enhanced["away_cs_away_rate"] = enhanced["away_clean_sheet_rate"]

    # 9. Failed to score rates
    enhanced["home_fts_rate"] = home_features.get(
        "home_stat_failed_to_score_home_rate", 0.2 if home_gf_avg > 1.0 else 0.35
    )
    enhanced["away_fts_rate"] = away_features.get(
        "away_stat_failed_to_score_away_rate", 0.3 if away_gf_avg > 1.0 else 0.4
    )

    # 10. BTTS and Over 2.5 rates
    # Calculate from goals averages
    home_btts_likely = home_gf_avg >= 1.0 and home_ga_avg >= 1.0
    away_btts_likely = away_gf_avg >= 1.0 and away_ga_avg >= 1.0
    enhanced["home_btts_rate"] = 0.55 if home_btts_likely else 0.40
    enhanced["away_btts_rate"] = 0.50 if away_btts_likely else 0.35

    enhanced["home_over25_rate"] = 0.55 if (home_gf_avg + home_ga_avg) > 2.5 else 0.40
    enhanced["away_over25_rate"] = 0.50 if (away_gf_avg + away_ga_avg) > 2.5 else 0.35

    # 11. Streak data (estimate from recent form)
    enhanced["home_win_streak"] = min(home_wins_10 // 2, 5)
    enhanced["away_win_streak"] = min(away_wins_10 // 2, 5)
    enhanced["home_loss_streak"] = 0 if home_wins_10 > 3 else min(home_losses_10 // 2, 3)
    enhanced["away_loss_streak"] = 0 if away_wins_10 > 3 else min(away_losses_10 // 2, 3)
    enhanced["home_unbeaten_streak"] = (home_wins_10 + home_draws_10) // 2
    enhanced["away_unbeaten_streak"] = (away_wins_10 + away_draws_10) // 2

    # 12. Match counts at venue
    enhanced["home_home_matches"] = home_matches // 2
    enhanced["away_away_matches"] = away_matches // 2

    return enhanced


# Load seasonal stats once at module load
print("Loading seasonal team statistics for enhanced predictions...")
SEASONAL_STATS = load_all_seasonal_stats()
print(f"Loaded stats for {sum(len(s) for s in SEASONAL_STATS.values())} total team-seasons")


