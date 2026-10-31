"""
Cache lifetimes by what the data is: a finished match never changes, a future date's list rarely does, today's list carries
live scores. Before this every fixtures answer lived 60 seconds, so visitor-triggered lookups (results, match pages,
head-to-head) were almost never served from cache and each page view cost an API call.
"""
from datetime import datetime, timedelta

import pytest

import backend.api_client as ac


def _fx(status, fid=1):
    return {"fixture": {"id": fid, "status": {"short": status}}, "goals": {"home": 1, "away": 0}, "teams": {"home": {"id": 1}, "away": {"id": 2}}}


class _Resp:
    status_code = 200
    headers = {}
    def __init__(self, rows): self.rows = rows
    def json(self): return {"errors": [], "results": len(self.rows), "response": self.rows}


@pytest.fixture
def client(monkeypatch):
    c = ac.ApiClient({"api_key": "k", "api_base_url": "https://v3.football.api-sports.io"})
    stored = []
    monkeypatch.setattr(c, "_get_from_cache", lambda key: None)
    monkeypatch.setattr(c, "_set_cache", lambda key, data, ttl_type, ttl_override=None: stored.append(ttl_override))
    monkeypatch.setattr(c, "_wait_for_rate_limit", lambda: None)
    c.stored = stored
    return c


def _serve(monkeypatch, rows):
    monkeypatch.setattr(ac.requests, "get", lambda *a, **k: _Resp(rows))


def test_a_finished_match_is_cached_for_a_day(client, monkeypatch):
    _serve(monkeypatch, [_fx("FT")])
    client.get_fixture_details(1)
    assert client.stored[-1] == ac.FINISHED_TTL_SECONDS == 86400


@pytest.mark.parametrize("status", ["FT", "AET", "PEN"])
def test_every_final_status_counts(client, monkeypatch, status):
    _serve(monkeypatch, [_fx(status)])
    client.get_fixture_details(1)
    assert client.stored[-1] == 86400


@pytest.mark.parametrize("status", ["NS", "1H", "HT", "2H", "PST", "SUSP", "LIVE"])
def test_a_match_that_is_not_over_keeps_the_short_lifetime(client, monkeypatch, status):
    _serve(monkeypatch, [_fx(status)])
    client.get_fixture_details(1)
    assert client.stored[-1] == ac.FIXTURE_DETAIL_TTL_SECONDS == 120


def test_one_unfinished_match_in_a_list_keeps_the_whole_list_short(client, monkeypatch):
    _serve(monkeypatch, [_fx("FT", 1), _fx("NS", 2)])
    client.get_fixture_details(1)
    assert client.stored[-1] == 120


def test_an_empty_answer_is_never_cached_for_a_day(client, monkeypatch):
    _serve(monkeypatch, [])
    client.get_fixture_details(1)
    assert client.stored[-1] == 120


def test_lists_by_date_future_today_past(client, monkeypatch):
    today = datetime.utcnow().date()
    _serve(monkeypatch, [_fx("NS")])
    client.get_fixtures(league_id=39, season=2026, date=(today + timedelta(days=2)).isoformat())
    assert client.stored[-1] == ac.UPCOMING_LIST_TTL_SECONDS == 600
    client.get_fixtures(league_id=39, season=2026, date=today.isoformat())
    assert client.stored[-1] == ac.TODAY_LIST_TTL_SECONDS == 120
    _serve(monkeypatch, [_fx("NS")])
    client.get_fixtures(league_id=39, season=2026, date=(today - timedelta(days=2)).isoformat())
    assert client.stored[-1] == 60, "a past date with an unfinished fixture keeps the base lifetime"
    _serve(monkeypatch, [_fx("FT")])
    client.get_fixtures(league_id=39, season=2026, date=(today - timedelta(days=2)).isoformat())
    assert client.stored[-1] == 86400, "a past date where everything finished is cached for a day"


def test_head_to_head_is_cached_for_hours(client, monkeypatch):
    _serve(monkeypatch, [_fx("FT")])
    client.get_h2h(1, 2)
    assert client.stored[-1] == ac.H2H_TTL_SECONDS == 21600     # head-to-head has its own endpoint and its own lifetime
    _serve(monkeypatch, [_fx("FT"), _fx("NS", 2)])
    client.get_h2h(1, 2)
    assert client.stored[-1] == 21600


def test_live_fixtures_are_not_lengthened(client, monkeypatch):
    _serve(monkeypatch, [_fx("1H")])
    client.get_live_fixtures()
    assert client.stored[-1] == 60


def test_an_error_answer_is_never_cached(client, monkeypatch):
    class Err(_Resp):
        def json(self): return {"errors": {"requests": "You have reached the request limit for the day"}, "response": []}
    monkeypatch.setattr(ac.requests, "get", lambda *a, **k: Err([]))
    client.get_fixture_details(1)
    assert client.stored == []
