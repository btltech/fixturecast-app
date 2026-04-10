#!/usr/bin/env python3
"""
Newsletter Generator for FixtureCast.
Generates top weekend predictions and sends via Kit (ConvertKit) API.
Can be run manually or scheduled via cron/Railway.
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Optional

import httpx

# Add parent path for imports
sys.path.append(os.path.dirname(__file__))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from .league_catalog import get_featured_league_map, get_league_season
except ImportError:
    from league_catalog import get_featured_league_map, get_league_season

# Kit (ConvertKit) Configuration
KIT_API_KEY = os.environ.get("KIT_API_KEY", "")
KIT_API_SECRET = os.environ.get("KIT_API_SECRET", "")
KIT_BROADCAST_TAG = os.environ.get(
    "KIT_BROADCAST_TAG", ""
)  # Optional: tag for broadcast recipients

# ML API for predictions
ML_API_URL = os.environ.get("ML_API_URL", "https://ml-api-production-6cfc.up.railway.app")

FEATURED_LEAGUES = get_featured_league_map()


def load_config():
    """Load configuration from config.json."""
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load config: {e}")
        return {}


def filter_featured_fixtures(fixtures: list) -> list:
    """Filter fixtures to only include featured leagues."""
    filtered = []
    for fixture in fixtures:
        league_id = fixture.get("league", {}).get("id")
        if league_id in FEATURED_LEAGUES:
            filtered.append(fixture)
    logger.info(f"Filtered {len(fixtures)} fixtures to {len(filtered)} from featured leagues")
    return filtered


async def get_weekend_fixtures() -> list:
    """Get fixtures for this weekend (Saturday and Sunday) from featured leagues only."""
    try:
        from .api_client import ApiClient
    except ImportError:
        from api_client import ApiClient

    config = load_config()
    api = ApiClient(config)

    today = datetime.now()
    # Find next Saturday
    days_until_saturday = (5 - today.weekday()) % 7
    if days_until_saturday == 0 and today.hour >= 18:
        days_until_saturday = 7  # Already Saturday evening, get next week

    saturday = today + timedelta(days=days_until_saturday)
    sunday = saturday + timedelta(days=1)

    fixtures = []

    # Get Saturday fixtures (API returns dict with 'response' key containing list)
    sat_result = api.get_fixtures(date=saturday.strftime("%Y-%m-%d"))
    if sat_result and isinstance(sat_result, dict):
        sat_fixtures = sat_result.get("response", [])
        fixtures.extend(sat_fixtures)

    # Get Sunday fixtures
    sun_result = api.get_fixtures(date=sunday.strftime("%Y-%m-%d"))
    if sun_result and isinstance(sun_result, dict):
        sun_fixtures = sun_result.get("response", [])
        fixtures.extend(sun_fixtures)

    # Filter to only featured leagues
    return filter_featured_fixtures(fixtures)


async def get_predictions_for_fixtures(fixtures: list) -> list:
    """Get ML predictions for fixtures."""
    predictions = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for fixture in fixtures[:20]:  # Limit to 20 to avoid too many API calls
            fixture_id = None
            try:
                fixture_id = fixture.get("fixture", {}).get("id")
                league_id = fixture.get("league", {}).get("id") or 39
                season = get_league_season(league_id, fixture.get("fixture", {}).get("date"))
                if not fixture_id:
                    continue

                # Use correct API endpoint: /api/prediction/{fixture_id}
                response = await client.get(
                    f"{ML_API_URL}/api/prediction/{fixture_id}",
                    params={"league": league_id, "season": season},
                )
                if response.status_code == 200:
                    pred_data = response.json()
                    pred_data["fixture_info"] = fixture
                    predictions.append(pred_data)
            except Exception as e:
                logger.warning(f"Failed to get prediction for fixture {fixture_id}: {e}")
                continue

    return predictions


def rank_predictions(predictions: list) -> list:
    """Rank predictions by confidence and value."""
    ranked = []
    edge_margin = float(os.environ.get("EDGE_MARGIN", "0.02"))

    for pred in predictions:
        try:
            # Get fixture details from API response
            fixture_details = pred.get("fixture_details", {})
            teams = fixture_details.get("teams", {})
            home_team = teams.get("home", {}).get("name", "Unknown")
            away_team = teams.get("away", {}).get("name", "Unknown")
            league = fixture_details.get("league", {}).get("name", "Unknown League")
            match_date = fixture_details.get("fixture", {}).get("date", "")

            # Get main prediction probabilities
            main_pred = pred.get("prediction", {})
            home_prob = main_pred.get("home_win_prob", 0) * 100
            draw_prob = main_pred.get("draw_prob", 0) * 100
            away_prob = main_pred.get("away_win_prob", 0) * 100

            # Determine winner prediction
            if home_prob >= away_prob and home_prob >= draw_prob:
                winner = home_team
                confidence = home_prob
                outcome_key = "home"
            elif away_prob >= home_prob and away_prob >= draw_prob:
                winner = away_team
                confidence = away_prob
                outcome_key = "away"
            else:
                winner = "Draw"
                confidence = draw_prob
                outcome_key = "draw"

            # If odds are available, require a probability edge before selecting
            edge_value = None
            odds_info = main_pred.get("odds", {})
            odds_1x2 = odds_info.get("1x2", {}) if isinstance(odds_info, dict) else {}
            odds_available = bool(odds_1x2.get("available"))
            if odds_available:
                odds_home = odds_1x2.get("home", 0)
                odds_draw = odds_1x2.get("draw", 0)
                odds_away = odds_1x2.get("away", 0)
                if odds_home and odds_draw and odds_away:
                    implied_home = 1 / odds_home
                    implied_draw = 1 / odds_draw
                    implied_away = 1 / odds_away
                    total = implied_home + implied_draw + implied_away
                    if total > 0:
                        implied = {
                            "home": implied_home / total,
                            "draw": implied_draw / total,
                            "away": implied_away / total,
                        }
                        model_prob = confidence / 100
                        edge_value = model_prob - implied.get(outcome_key, model_prob)
                        if edge_value <= edge_margin:
                            continue

            # Get market predictions
            btts_prob = main_pred.get("btts_prob", 0) * 100
            over25_prob = main_pred.get("over25_prob", 0) * 100

            ranked.append(
                {
                    "home_team": home_team,
                    "away_team": away_team,
                    "league": league,
                    "date": match_date,
                    "prediction": winner,
                    "confidence": round(confidence, 1),
                    "btts": "Yes" if btts_prob > 50 else "No",
                    "btts_confidence": round(btts_prob, 1),
                    "over_25": "Over" if over25_prob > 50 else "Under",
                    "over_25_confidence": round(over25_prob, 1),
                    "edge": round(edge_value * 100, 1) if edge_value is not None else None,
                }
            )
        except Exception as e:
            logger.warning(f"Error processing prediction: {e}")
            continue

    # Sort by confidence (highest first)
    ranked.sort(key=lambda x: x["confidence"], reverse=True)

    return ranked


def generate_accumulator(top_picks: list) -> dict:
    """Generate an accumulator from top picks."""
    if len(top_picks) < 4:
        return None

    # Take top 4 most confident picks for accumulator
    acca_picks = top_picks[:4]

    # Calculate combined probability (multiply confidences)
    combined_prob = 1.0
    for pick in acca_picks:
        combined_prob *= pick["confidence"] / 100

    # Estimate odds (rough calculation: 1/probability)
    estimated_odds = 1 / combined_prob if combined_prob > 0 else 1

    return {
        "picks": acca_picks,
        "combined_confidence": round(combined_prob * 100, 1),
        "estimated_odds": round(estimated_odds, 2),
    }


def format_email_html(top_picks: list, accumulator: dict) -> str:
    """Format the newsletter as HTML email."""

    # Format date
    today = datetime.now()
    weekend_date = today.strftime("%B %d, %Y")

    # Build picks HTML - each pick as a card for better spacing
    picks_html = ""
    for i, pick in enumerate(top_picks[:8], 1):
        emoji = "🏆" if i <= 3 else "⚽"
        confidence_color = (
            "#10b981"
            if pick["confidence"] >= 65
            else "#f59e0b" if pick["confidence"] >= 55 else "#6b7280"
        )

        # Card style for each pick
        picks_html += f"""
        <div style="background: #1e293b; border-radius: 12px; padding: 20px; margin-bottom: 16px; border-left: 4px solid #06b6d4;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div style="flex: 1;">
                    <div style="font-weight: 700; color: #f8fafc; font-size: 16px; margin-bottom: 6px;">
                        {emoji} {pick['home_team']} vs {pick['away_team']}
                    </div>
                    <div style="font-size: 13px; color: #94a3b8; margin-bottom: 12px;">
                        {pick['league']}
                    </div>
                    <div style="display: inline-block;">
                        <span style="background: linear-gradient(135deg, #06b6d4, #8b5cf6); color: white; padding: 6px 16px; border-radius: 20px; font-weight: 600; font-size: 14px;">
                            {pick['prediction']}
                        </span>
                        <span style="color: {confidence_color}; font-weight: 700; margin-left: 12px; font-size: 15px;">
                            {pick['confidence']}%
                        </span>
                    </div>
                </div>
            </div>
        </div>
        """

    # Build accumulator HTML
    acca_html = ""
    if accumulator:
        acca_picks_html = ""
        for pick in accumulator["picks"]:
            acca_picks_html += f"""
            <div style="padding: 14px 0; border-bottom: 1px solid #334155;">
                <div style="color: #f8fafc; font-size: 14px; margin-bottom: 4px;">
                    {pick['home_team']} vs {pick['away_team']}
                </div>
                <div style="color: #06b6d4; font-weight: 600; font-size: 13px;">
                    → {pick['prediction']} ({pick['confidence']}%)
                </div>
            </div>
            """

        acca_html = f"""
        <div style="margin-top: 40px; background: linear-gradient(135deg, rgba(6, 182, 212, 0.15), rgba(139, 92, 246, 0.15)); border: 2px solid rgba(6, 182, 212, 0.4); border-radius: 16px; padding: 24px;">
            <h2 style="color: #f8fafc; margin: 0 0 20px 0; font-size: 20px; text-align: center;">🎯 Weekend Accumulator</h2>
            {acca_picks_html}
            <div style="margin-top: 24px; text-align: center;">
                <span style="background: linear-gradient(135deg, #06b6d4, #8b5cf6); color: white; padding: 12px 28px; border-radius: 25px; font-weight: 700; font-size: 16px; display: inline-block;">
                    Combined Odds: ~{accumulator['estimated_odds']}x
                </span>
            </div>
        </div>
        """

    # Full email HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; background-color: #0f172a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
        <div style="max-width: 600px; margin: 0 auto; padding: 32px 20px;">

            <!-- Header -->
            <div style="text-align: center; padding: 24px 0 32px 0;">
                <h1 style="margin: 0; font-size: 32px; color: #06b6d4;">
                    🔮 FixtureCast
                </h1>
                <p style="color: #94a3b8; margin: 12px 0 0 0; font-size: 16px;">Weekend Predictions • {weekend_date}</p>
            </div>

            <!-- Intro -->
            <div style="color: #cbd5e1; padding: 0 0 32px 0; text-align: center;">
                <p style="margin: 0; font-size: 15px; line-height: 1.6;">
                    Here are this weekend's top AI-powered predictions<br>from our 8-model ensemble.
                </p>
            </div>

            <!-- Section Title -->
            <div style="margin-bottom: 20px;">
                <h2 style="color: #f8fafc; font-size: 18px; margin: 0; padding-bottom: 12px; border-bottom: 1px solid #334155;">
                    📊 Top 8 Picks
                </h2>
            </div>

            <!-- Top Picks Cards -->
            {picks_html}

            {acca_html}

            <!-- CTA -->
            <div style="text-align: center; padding: 40px 0;">
                <a href="https://fixturecast.com" style="display: inline-block; background: linear-gradient(135deg, #06b6d4, #8b5cf6); color: white; padding: 16px 40px; border-radius: 10px; text-decoration: none; font-weight: 600; font-size: 16px;">
                    View All Predictions →
                </a>
            </div>

            <!-- Footer -->
            <div style="text-align: center; padding: 24px 0; border-top: 1px solid #334155;">
                <p style="color: #64748b; font-size: 13px; margin: 0; line-height: 1.8;">
                    Predictions are for entertainment only. Always bet responsibly.<br><br>
                    <a href="https://fixturecast.com" style="color: #06b6d4; text-decoration: none;">fixturecast.com</a> &nbsp;•&nbsp;
                    <a href="https://x.com/fixturecast" style="color: #06b6d4; text-decoration: none;">@fixturecast</a>
                </p>
            </div>
        </div>
    </body>
    </html>
    """

    return html


def format_email_text(top_picks: list, accumulator: dict) -> str:
    """Format the newsletter as plain text."""

    today = datetime.now()
    weekend_date = today.strftime("%B %d, %Y")

    text = f"""🔮 FixtureCast Weekend Predictions
{weekend_date}

TOP 8 PICKS
{'='*40}

"""

    for i, pick in enumerate(top_picks[:8], 1):
        text += f"{i}. {pick['home_team']} vs {pick['away_team']}\n"
        text += f"   League: {pick['league']}\n"
        text += f"   Pick: {pick['prediction']} ({pick['confidence']}%)\n\n"

    if accumulator:
        text += f"""
🎯 WEEKEND ACCUMULATOR
{'='*40}

"""
        for pick in accumulator["picks"]:
            text += f"• {pick['home_team']} vs {pick['away_team']} - {pick['prediction']}\n"

        text += f"\nCombined Odds: ~{accumulator['estimated_odds']}x\n"

    text += f"""
---
View all predictions: https://fixturecast.com
Follow us: https://x.com/fixturecast

Predictions are for entertainment only. Bet responsibly.
"""

    return text


async def send_broadcast(subject: str, html_content: str, text_content: str) -> dict:
    """Send broadcast email via Kit (ConvertKit) API."""

    # Read env var dynamically (not at module load time)
    kit_api_secret = os.environ.get("KIT_API_SECRET", "")

    if not kit_api_secret:
        logger.error("KIT_API_SECRET not configured")
        return {"sent": False, "error": "KIT_API_SECRET not configured"}

    logger.info(f"Attempting to send broadcast with subject: {subject}")
    logger.info(f"KIT_API_SECRET is set: {bool(kit_api_secret)} (length: {len(kit_api_secret)})")

    async with httpx.AsyncClient() as client:
        try:
            # Create broadcast
            response = await client.post(
                "https://api.convertkit.com/v3/broadcasts",
                json={
                    "api_secret": kit_api_secret,
                    "subject": subject,
                    "content": html_content,
                    "description": "Weekly weekend predictions",
                    "public": False,
                    "published_at": datetime.now().isoformat(),
                },
            )

            logger.info(f"Kit API response: {response.status_code}")

            if response.status_code in [200, 201]:
                broadcast_data = response.json()
                broadcast_id = broadcast_data.get("broadcast", {}).get("id")
                logger.info(f"Broadcast created with ID: {broadcast_id}")
                return {"sent": True, "broadcast_id": broadcast_id}
            else:
                error_msg = f"Kit API error {response.status_code}: {response.text}"
                logger.error(error_msg)
                return {"sent": False, "error": error_msg}

        except Exception as e:
            logger.error(f"Error sending broadcast: {e}")
            return {"sent": False, "error": str(e)}


async def generate_and_send_newsletter() -> dict:
    """Main function to generate and send the weekly newsletter."""

    logger.info("Starting newsletter generation...")

    # Get weekend fixtures
    logger.info("Fetching weekend fixtures...")
    fixtures = await get_weekend_fixtures()
    logger.info(f"Found {len(fixtures)} weekend fixtures")

    if not fixtures:
        return {"success": False, "error": "No weekend fixtures found"}

    # Get predictions
    logger.info("Fetching predictions...")
    predictions = await get_predictions_for_fixtures(fixtures)
    logger.info(f"Got {len(predictions)} predictions")

    if not predictions:
        return {"success": False, "error": "No predictions available"}

    # Rank predictions
    ranked = rank_predictions(predictions)
    top_picks = ranked[:8]

    # Generate accumulator
    accumulator = generate_accumulator(ranked)

    # Format email content
    html_content = format_email_html(top_picks, accumulator)
    text_content = format_email_text(top_picks, accumulator)

    # Generate subject line
    today = datetime.now()
    subject = f"🔮 Weekend Predictions ({today.strftime('%b %d')}): Top 8 AI Picks + Accumulator"

    # Send broadcast
    logger.info("Sending broadcast...")
    success = await send_broadcast(subject, html_content, text_content)

    return {
        "success": success,
        "picks_count": len(top_picks),
        "accumulator": accumulator is not None,
        "subject": subject,
    }


# For manual testing
if __name__ == "__main__":
    import asyncio

    async def test():
        # Just generate content without sending
        fixtures = await get_weekend_fixtures()
        print(f"Found {len(fixtures)} fixtures")

        if fixtures:
            predictions = await get_predictions_for_fixtures(fixtures[:5])
            print(f"Got {len(predictions)} predictions")

            if predictions:
                ranked = rank_predictions(predictions)
                accumulator = generate_accumulator(ranked)

                print("\nTop Picks:")
                for i, pick in enumerate(ranked[:8], 1):
                    print(
                        f"{i}. {pick['home_team']} vs {pick['away_team']} - {pick['prediction']} ({pick['confidence']}%)"
                    )

                if accumulator:
                    print(f"\nAccumulator ({len(accumulator['picks'])} picks):")
                    print(f"Combined odds: ~{accumulator['estimated_odds']}x")

    asyncio.run(test())
