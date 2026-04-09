"""
OG Image Generator
Generates beautiful share cards for social media (Open Graph images)

Features:
- Team logos
- Predicted score
- Win probabilities
- Branded FixtureCast design
- Cached for performance

Requirements:
    pip install pillow requests
"""

import hashlib
import io
import os
from datetime import datetime, timedelta
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

# Configuration
CACHE_DIR = Path("data/og_images")
CACHE_DURATION = timedelta(hours=6)  # Cache images for 6 hours
DEFAULT_WIDTH = 1200
DEFAULT_HEIGHT = 630  # Standard OG image size

# Create cache directory
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Colors (Midnight Sports theme)
COLOR_BG = "#0B0E14"
COLOR_SURFACE = "#151B28"
COLOR_PRIMARY = "#3B82F6"
COLOR_SECONDARY = "#6366F1"
COLOR_ACCENT = "#06b6d4"
COLOR_TEXT = "#FFFFFF"
COLOR_TEXT_SECONDARY = "#94A3B8"


def get_font(size):
    """Get a font with the specified size, trying multiple font options"""
    # Try common font paths in order of preference
    font_paths = [
        # macOS
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSText.ttf",
        "/Library/Fonts/Arial.ttf",
        # Linux (Railway, Ubuntu, etc.)
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        # Windows
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        # Generic
        "arial.ttf",
        "Arial.ttf",
    ]

    for font_path in font_paths:
        try:
            return ImageFont.truetype(font_path, size)
        except (OSError, IOError):
            continue

    # Final fallback - use default font (will be small but readable)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        # Older Pillow versions don't support size parameter
        return ImageFont.load_default()


# Load fonts with fallback
FONT_TITLE = get_font(52)
FONT_SCORE = get_font(72)
FONT_BODY = get_font(32)
FONT_SMALL = get_font(24)


def generate_prediction_og_image(
    fixture_id, home_team, away_team, prediction_data, league_name="League"
):
    """
    Generate OG image for a prediction

    Args:
        fixture_id: Fixture ID for caching
        home_team: Home team name
        away_team: Away team name
        prediction_data: Prediction dictionary
        league_name: League name

    Returns:
        bytes: PNG image data
    """
    # Check cache first
    cache_key = f"prediction_{fixture_id}"
    cached_image = get_cached_image(cache_key)
    if cached_image:
        return cached_image

    # Create base image and draw context
    img = Image.new("RGB", (DEFAULT_WIDTH, DEFAULT_HEIGHT), COLOR_BG)
    draw = ImageDraw.Draw(img)

    # Gradient background
    for y in range(DEFAULT_HEIGHT):
        alpha = y / DEFAULT_HEIGHT
        r = int(11 + (21 - 11) * alpha)
        g = int(14 + (27 - 14) * alpha)
        b = int(20 + (40 - 20) * alpha)
        draw.line([(0, y), (DEFAULT_WIDTH, y)], fill=(r, g, b))

    # Subtle pattern
    draw_pattern(draw, img)

    # Header text block (matches share text vibe)
    header_y = 40
    draw.text(
        (60, header_y),
        "🔮 FixtureCast AI Prediction",
        font=FONT_BODY,
        fill=COLOR_ACCENT,
    )

    # League under header
    draw.text(
        (60, header_y + 50),
        f"🏆 {league_name}",
        font=FONT_SMALL,
        fill=COLOR_TEXT_SECONDARY,
    )

    # Teams row
    teams_y = 150
    draw.text(
        (60, teams_y),
        f"⚽ {home_team} vs {away_team}",
        font=FONT_TITLE,
        fill=COLOR_TEXT,
    )

    # Prediction details box
    box_x = 60
    box_y = teams_y + 140
    box_w = DEFAULT_WIDTH - 120
    box_h = 260

    draw.rounded_rectangle(
        [(box_x, box_y), (box_x + box_w, box_y + box_h)],
        radius=24,
        fill=COLOR_SURFACE,
        outline=COLOR_PRIMARY,
        width=2,
    )

    if prediction_data:
        # Core numbers
        home_p = float(prediction_data.get("home_win_prob", 0) or 0)
        draw_p = float(prediction_data.get("draw_prob", 0) or 0)
        away_p = float(prediction_data.get("away_win_prob", 0) or 0)

        home_prob_str = f"{home_p * 100:.0f}%"
        draw_prob_str = f"{draw_p * 100:.0f}%"
        away_prob_str = f"{away_p * 100:.0f}%"

        score = prediction_data.get("predicted_scoreline", "-:-")

        btts_prob = prediction_data.get("btts_prob")
        over25_prob = prediction_data.get("over25_prob")

        # Match odds section
        odds_y = box_y + 30
        draw.text(
            (box_x + 30, odds_y),
            "📊 Match Odds:",
            font=FONT_BODY,
            fill=COLOR_TEXT,
        )

        odds_line_y = odds_y + 60
        draw.text(
            (box_x + 60, odds_line_y),
            f"{home_team}: {home_prob_str}",
            font=FONT_SMALL,
            fill=COLOR_TEXT,
        )
        draw.text(
            (box_x + 60, odds_line_y + 40),
            f"Draw: {draw_prob_str}",
            font=FONT_SMALL,
            fill=COLOR_TEXT,
        )
        draw.text(
            (box_x + 60, odds_line_y + 80),
            f"{away_team}: {away_prob_str}",
            font=FONT_SMALL,
            fill=COLOR_TEXT,
        )

        # Predicted winner & score on right side of box
        right_x = box_x + box_w - 30
        pred_y = odds_y

        # Pick winner label
        winner_label = None
        winner_prob = None
        if home_p >= draw_p and home_p >= away_p:
            winner_label = home_team
            winner_prob = home_prob_str
        elif away_p >= home_p and away_p >= draw_p:
            winner_label = away_team
            winner_prob = away_prob_str
        else:
            winner_label = "Draw"
            winner_prob = draw_prob_str

        draw.text(
            (right_x, pred_y),
            f"🎯 Prediction: {winner_label} ({winner_prob})",
            font=FONT_SMALL,
            fill=COLOR_TEXT,
            anchor="ra",
        )

        draw.text(
            (right_x, pred_y + 40),
            f"📈 Score: {score}",
            font=FONT_SMALL,
            fill=COLOR_TEXT,
            anchor="ra",
        )

        # BTTS & Over 2.5 row
        markets_y = pred_y + 100
        if btts_prob is not None:
            btts_yes = btts_prob >= 0.5
            btts_str = (
                f"Yes ({btts_prob * 100:.0f}%)" if btts_yes else f"No ({btts_prob * 100:.0f}%)"
            )
            draw.text(
                (box_x + 60, markets_y),
                f"⚽ BTTS: {btts_str}",
                font=FONT_SMALL,
                fill=COLOR_TEXT,
            )

        if over25_prob is not None:
            over25_yes = over25_prob >= 0.5
            over25_str = (
                f"Yes ({over25_prob * 100:.0f}%)"
                if over25_yes
                else f"No ({over25_prob * 100:.0f}%)"
            )
            draw.text(
                (box_x + 60, markets_y + 40),
                f"📊 Over 2.5: {over25_str}",
                font=FONT_SMALL,
                fill=COLOR_TEXT,
            )

    # Footer CTA + hashtags
    footer_y = DEFAULT_HEIGHT - 80
    draw.text(
        (60, footer_y),
        "🤖 Get AI predictions → fixturecast.com",
        font=FONT_SMALL,
        fill=COLOR_TEXT_SECONDARY,
    )

    # League-based hashtags
    league_tag = ""
    ln = (league_name or "").lower()
    if "premier" in ln:
        league_tag = "#PremierLeague"
    elif "la liga" in ln:
        league_tag = "#LaLiga"
    elif "serie a" in ln:
        league_tag = "#SerieA"
    elif "bundesliga" in ln:
        league_tag = "#Bundesliga"
    elif "ligue 1" in ln or "ligue1" in ln:
        league_tag = "#Ligue1"
    elif "eredivisie" in ln:
        league_tag = "#Eredivisie"
    elif "primeira" in ln or "liga portugal" in ln:
        league_tag = "#LigaPortugal"
    elif "champions league" in ln:
        league_tag = "#UCL"
    elif "europa league" in ln:
        league_tag = "#UEL"

    hashtags = "#Football #Predictions"
    if league_tag:
        hashtags = f"{hashtags} {league_tag}"

    draw.text(
        (60, footer_y + 35),
        hashtags,
        font=FONT_SMALL,
        fill=COLOR_TEXT_SECONDARY,
    )

    # Save to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG", optimize=True)
    img_bytes.seek(0)
    image_data = img_bytes.read()

    # Cache the image
    cache_image(cache_key, image_data)

    return image_data


def draw_probability_bar(draw, x, y, width, height, probability, color, label):
    """Draw a probability bar with label"""
    # Background bar (gray)
    draw.rectangle([(x, y), (x + width, y + height)], fill=COLOR_SURFACE)

    # Filled bar (colored)
    fill_width = int(width * probability)
    draw.rectangle([(x, y), (x + fill_width, y + height)], fill=color)

    # Label
    draw.text(
        (x + width + 20, y + height // 2), label, font=FONT_BODY, fill=COLOR_TEXT, anchor="lm"
    )


def draw_pattern(draw, img):
    """Draw subtle background pattern"""
    # Add some circles for visual interest
    for i in range(5):
        x = (i + 1) * (DEFAULT_WIDTH // 6)
        y = DEFAULT_HEIGHT // 2
        radius = 150 + i * 20
        draw.ellipse(
            [(x - radius, y - radius), (x + radius, y + radius)], outline=COLOR_PRIMARY, width=1
        )


def generate_default_og_image(title="FixtureCast", subtitle="AI Football Predictions"):
    """Generate default OG image for non-prediction pages"""
    cache_key = f"default_{hashlib.md5(title.encode()).hexdigest()}"
    cached_image = get_cached_image(cache_key)
    if cached_image:
        return cached_image

    img = Image.new("RGB", (DEFAULT_WIDTH, DEFAULT_HEIGHT), COLOR_BG)
    draw = ImageDraw.Draw(img)

    # Gradient background
    for y in range(DEFAULT_HEIGHT):
        alpha = y / DEFAULT_HEIGHT
        r = int(11 + (21 - 11) * alpha)
        g = int(14 + (27 - 14) * alpha)
        b = int(20 + (40 - 20) * alpha)
        draw.line([(0, y), (DEFAULT_WIDTH, y)], fill=(r, g, b))

    # Large centered title
    title_bbox = draw.textbbox((0, 0), title, font=FONT_SCORE)
    title_width = title_bbox[2] - title_bbox[0]
    title_height = title_bbox[3] - title_bbox[1]

    draw.text(
        (DEFAULT_WIDTH // 2 - title_width // 2, DEFAULT_HEIGHT // 2 - title_height - 40),
        title,
        font=FONT_SCORE,
        fill=COLOR_TEXT,
    )

    # Subtitle
    draw.text(
        (DEFAULT_WIDTH // 2, DEFAULT_HEIGHT // 2 + 40),
        subtitle,
        font=FONT_BODY,
        fill=COLOR_TEXT_SECONDARY,
        anchor="mm",
    )

    # Save
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG", optimize=True)
    img_bytes.seek(0)
    image_data = img_bytes.read()

    cache_image(cache_key, image_data)
    return image_data


def get_cached_image(cache_key):
    """Get image from cache if available and not expired"""
    cache_file = CACHE_DIR / f"{cache_key}.png"

    if cache_file.exists():
        # Check if expired
        file_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
        if file_age < CACHE_DURATION:
            with open(cache_file, "rb") as f:
                return f.read()

    return None


def cache_image(cache_key, image_data):
    """Save image to cache"""
    cache_file = CACHE_DIR / f"{cache_key}.png"
    with open(cache_file, "wb") as f:
        f.write(image_data)


def cleanup_cache():
    """Remove expired cache files"""
    now = datetime.now()
    for cache_file in CACHE_DIR.glob("*.png"):
        file_age = now - datetime.fromtimestamp(cache_file.stat().st_mtime)
        if file_age > CACHE_DURATION:
            cache_file.unlink()
            print(f"Removed expired cache: {cache_file.name}")


if __name__ == "__main__":
    # Test image generation
    print("Testing OG image generation...")

    test_prediction = {
        "predicted_scoreline": "2-1",
        "home_win_prob": 0.58,
        "draw_prob": 0.24,
        "away_win_prob": 0.18,
    }

    image_data = generate_prediction_og_image(
        fixture_id=12345,
        home_team="Arsenal",
        away_team="Chelsea",
        prediction_data=test_prediction,
        league_name="Premier League",
    )

    # Save test image
    with open("test_og_image.png", "wb") as f:
        f.write(image_data)

    print("✅ Test image saved as test_og_image.png")
