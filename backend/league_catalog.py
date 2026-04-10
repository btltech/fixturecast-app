from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
LEAGUES_PATH = REPO_ROOT / "data" / "leagues.json"
CONFIG_PATH = Path(__file__).resolve().with_name("config.json")


CALENDAR_YEAR_LEAGUE_IDS = frozenset(
    {
        1,
        6,
        8,
        9,
        11,
        13,
        15,
        16,
        17,
        22,
        29,
        30,
        31,
        32,
        34,
        71,
        73,
        98,
        128,
        130,
        169,
        239,
        253,
        255,
        262,
        265,
        278,
        292,
        296,
        340,
    }
)


def _normalize_datetime(date_like=None) -> datetime:
    if isinstance(date_like, datetime):
        return date_like
    if isinstance(date_like, str):
        raw = date_like.strip()
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            try:
                return datetime.strptime(raw[:10], "%Y-%m-%d")
            except ValueError:
                return datetime.now()
    return datetime.now()


def get_cross_year_season(date_like=None) -> int:
    current = _normalize_datetime(date_like)
    return current.year if current.month >= 7 else current.year - 1


def is_calendar_year_league(league_id: int) -> bool:
    try:
        return int(league_id) in CALENDAR_YEAR_LEAGUE_IDS
    except (TypeError, ValueError):
        return False


def get_league_season(league_id: int, date_like=None) -> int:
    current = _normalize_datetime(date_like)
    if is_calendar_year_league(league_id):
        return current.year
    return get_cross_year_season(current)


@lru_cache(maxsize=1)
def _load_allowed_competitions() -> list[int]:
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
            config = json.load(config_file)
        return [int(league_id) for league_id in config.get("allowed_competitions", [])]
    return [row["id"] for row in _load_league_rows()]


@lru_cache(maxsize=1)
def _load_league_rows() -> list[dict]:
    if not LEAGUES_PATH.exists():
        return []
    with LEAGUES_PATH.open("r", encoding="utf-8") as leagues_file:
        rows = json.load(leagues_file)
    return [row for row in rows if isinstance(row, dict) and row.get("id") is not None]


def get_league_rows(
    include_tiers: Iterable[int] | None = None,
    exclude_tiers: Iterable[int] | None = (4,),
) -> list[dict]:
    allowed_ids = set(_load_allowed_competitions())
    include_tiers_set = set(include_tiers) if include_tiers is not None else None
    exclude_tiers_set = set(exclude_tiers or [])
    rows = []
    for row in _load_league_rows():
        league_id = int(row["id"])
        tier = row.get("tier")
        if league_id not in allowed_ids:
            continue
        if include_tiers_set is not None and tier not in include_tiers_set:
            continue
        if tier in exclude_tiers_set:
            continue
        rows.append(row)
    return rows


def get_featured_league_map(
    include_tiers: Iterable[int] | None = None,
    exclude_tiers: Iterable[int] | None = (4,),
) -> dict[int, str]:
    return {int(row["id"]): row["name"] for row in get_league_rows(include_tiers, exclude_tiers)}


def get_featured_league_ids(
    include_tiers: Iterable[int] | None = None,
    exclude_tiers: Iterable[int] | None = (4,),
) -> list[int]:
    return list(get_featured_league_map(include_tiers, exclude_tiers).keys())


def get_training_seasons(league_id: int, start_year: int = 2020, date_like=None) -> list[int]:
    final_season = get_league_season(league_id, date_like)
    if final_season < start_year:
        return [final_season]
    return list(range(start_year, final_season + 1))