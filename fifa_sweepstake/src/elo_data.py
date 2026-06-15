"""
Elo rating data source.

Primary source (online): http://api.clubelo.com / eloratings.net style data.
eloratings.net exposes a JSON-ish endpoint at:
    https://eloratings.net/en/api/ratings/<date>  (unofficial, may change)

Since this isn't guaranteed stable, we provide:
1. fetch_live_elo() -- attempts to pull current ratings via World Football Elo API
2. SEED_ELO -- a hand-curated fallback snapshot (approx ratings, mid-2026 form)
   so the rest of the pipeline always works offline.

Name normalization maps team names from sweepstake_participants.py to the naming
convention used by the Elo source.
"""

import requests

# Fallback / seed Elo ratings (approximate, illustrative).
# Update these periodically from https://www.eloratings.net before the tournament.
SEED_ELO = {
    "Brazil": 2010, "Argentina": 2005, "France": 1995, "Spain": 1990,
    "England": 1975, "Portugal": 1965, "Netherlands": 1960, "Belgium": 1930,
    "Germany": 1928, "Croatia": 1900, "Colombia": 1895, "Morocco": 1890,
    "USA": 1880, "Uruguay": 1878, "Switzerland": 1865, "Mexico": 1850,
    "Senegal": 1845, "Japan": 1840, "Denmark": 1838, "Italy": 1835,
    "Korea Republic": 1820, "Australia": 1800, "Ecuador": 1798, "Iran": 1795,
    "Canada": 1790, "Egypt": 1785, "Austria": 1780, "Algeria": 1775,
    "Tunisia": 1760, "Norway": 1755, "Sweden": 1750, "Turkiye": 1748,
    "Ghana": 1740, "Cote d'Ivoire": 1735, "Saudi Arabia": 1720,
    "Paraguay": 1715, "Qatar": 1700, "Panama": 1695, "South Africa": 1690,
    "Scotland": 1730, "Czechia": 1745, "Uzbekistan": 1680, "Jordan": 1660,
    "Cabo Verde": 1655, "New Zealand": 1640, "Iraq": 1670, "Haiti": 1620,
    "Curacao": 1610, "DR Congo": 1650, "Bosnia and Herzegovina": 1770,
}

# Default rating for any team not found above
DEFAULT_ELO = 1650

# Map participant team names -> eloratings.net naming (where different)
NAME_MAP = {
    "USA": "USA",
    "Korea Republic": "South Korea",
    "Turkiye": "Turkey",
    "Cote d'Ivoire": "Ivory Coast",
    "Czechia": "Czech Republic",
    "Curacao": "Curacao",
    "DR Congo": "DR Congo",
}


def fetch_live_elo():
    """
    Attempt to fetch current Elo ratings from eloratings.net.
    Returns a dict {team_name: elo} on success, or None on failure
    (e.g. no network access) -- caller should fall back to SEED_ELO.
    """
    url = "https://api.clubelo.com/Ranking"  # club-level; placeholder for national team source
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        # Parsing logic depends on actual response format -- adapt as needed.
        # This is a stub; real implementation should parse eloratings.net's
        # national team JSON once an endpoint is confirmed.
        return None
    except requests.RequestException:
        return None


def get_elo_ratings():
    """
    Return a dict of {team_name (as in participants.py): elo_rating},
    using live data if available, falling back to SEED_ELO otherwise.
    """
    live = fetch_live_elo()
    ratings = dict(SEED_ELO)
    if live:
        for team, elo in live.items():
            ratings[team] = elo
    return ratings


def get_team_elo(team_name, ratings=None):
    """Get Elo for a single team, applying name mapping and default fallback."""
    if ratings is None:
        ratings = get_elo_ratings()
    mapped = NAME_MAP.get(team_name, team_name)
    return ratings.get(mapped, ratings.get(team_name, DEFAULT_ELO))


if __name__ == "__main__":
    ratings = get_elo_ratings()
    for team, elo in sorted(ratings.items(), key=lambda x: -x[1]):
        print(f"{team:25s} {elo}")
