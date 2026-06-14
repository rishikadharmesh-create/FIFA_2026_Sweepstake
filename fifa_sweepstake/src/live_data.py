"""
Live fixture/result data source: API-Football (via RapidAPI or direct API-Football key).

Sign up at https://www.api-football.com/ or https://rapidapi.com/api-sports/api/api-football
to get a free API key, then set it as an environment variable:

    export API_FOOTBALL_KEY="your_key_here"

This module fetches:
- The 2026 World Cup fixture list (group stage + bracket)
- Completed match results (to update Elo ratings live)

Falls back gracefully (returns empty list) if no key / no network -- the rest
of the pipeline (simulation, dashboard) still works using Elo-only pre-tournament
projections.
"""

import os
import requests

API_KEY = os.environ.get("API_FOOTBALL_KEY", "")
BASE_URL = "https://v3.football.api-sports.io"

# 2026 World Cup competition ID in API-Football (confirm closer to tournament,
# this is a placeholder -- check /leagues endpoint for the correct ID)
WORLD_CUP_LEAGUE_ID = 1
SEASON = 2026


def _headers():
    return {"x-apisports-key": API_KEY}


def fetch_fixtures(status=None):
    """
    Fetch World Cup fixtures.
    status: None for all, or e.g. "FT" (finished), "NS" (not started), "LIVE"
    Returns a list of fixture dicts, or [] on failure.
    """
    if not API_KEY:
        return []

    params = {"league": WORLD_CUP_LEAGUE_ID, "season": SEASON}
    if status:
        params["status"] = status

    try:
        resp = requests.get(f"{BASE_URL}/fixtures", headers=_headers(), params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", [])
    except requests.RequestException:
        return []


def fetch_completed_results():
    """
    Returns a list of completed matches in the form:
    [{"home": "Brazil", "away": "Germany", "home_goals": 2, "away_goals": 1}, ...]
    Empty list if unavailable.
    """
    fixtures = fetch_fixtures(status="FT")
    results = []
    for f in fixtures:
        try:
            results.append({
                "home": f["teams"]["home"]["name"],
                "away": f["teams"]["away"]["name"],
                "home_goals": f["goals"]["home"],
                "away_goals": f["goals"]["away"],
            })
        except (KeyError, TypeError):
            continue
    return results


if __name__ == "__main__":
    results = fetch_completed_results()
    print(f"Fetched {len(results)} completed matches")
    for r in results[:10]:
        print(r)
