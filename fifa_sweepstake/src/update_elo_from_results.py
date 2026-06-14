"""
Updates team Elo ratings based on completed 2026 World Cup matches.

Two sources of completed results:
1. LIVE: live_data.fetch_completed_results() -- requires API_FOOTBALL_KEY
2. MANUAL: data/manual_results.csv -- a simple CSV you can edit by hand,
   useful if you don't have/want an API key, or want to log results yourself
   as they happen.

CSV format (data/manual_results.csv):
    home,away,home_goals,away_goals
    Mexico,South Africa,2,0

Usage:
    from update_elo_from_results import get_updated_elo_ratings
    elo = get_updated_elo_ratings()   # returns dict {team: elo}, base + all
                                       # completed-match adjustments applied

This is idempotent per run: it always starts from SEED_ELO and replays
ALL completed matches in order, so results don't double-apply across runs.
"""

import os
import csv

from elo_data import get_elo_ratings, NAME_MAP
from prediction_model import update_elo
from live_data import fetch_completed_results

MANUAL_RESULTS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "manual_results.csv")


def _normalize(team):
    """Reverse-map API/CSV team names to the names used in participants.py, if needed."""
    reverse_map = {v: k for k, v in NAME_MAP.items()}
    return reverse_map.get(team, team)


def load_manual_results(path=MANUAL_RESULTS_PATH):
    """
    Load completed match results from a manual CSV file.
    Returns [] if the file doesn't exist.
    """
    if not os.path.exists(path):
        return []

    results = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                results.append({
                    "home": row["home"].strip(),
                    "away": row["away"].strip(),
                    "home_goals": int(row["home_goals"]),
                    "away_goals": int(row["away_goals"]),
                })
            except (KeyError, ValueError):
                continue
    return results


def get_all_completed_results():
    """
    Combine live API results (if available) with manual CSV results.
    Live results take priority; manual results fill in anything the API
    doesn't have (e.g. no API key configured).
    """
    live = fetch_completed_results()
    manual = load_manual_results()

    # Dedup by (home, away) pair -- live results win if both present
    seen = set()
    combined = []
    for r in live:
        key = (r["home"], r["away"])
        seen.add(key)
        combined.append(r)
    for r in manual:
        key = (r["home"], r["away"])
        if key not in seen:
            combined.append(r)

    return combined


def get_updated_elo_ratings(verbose=False):
    """
    Returns a dict {team: elo} starting from SEED_ELO/live Elo baseline,
    with Elo adjustments applied for every completed match found
    (live API + manual CSV).
    """
    ratings = get_elo_ratings()
    results = get_all_completed_results()

    for r in results:
        home = _normalize(r["home"])
        away = _normalize(r["away"])

        if home not in ratings or away not in ratings:
            # Team not in our tracked set (or name mismatch) -- skip
            if verbose:
                print(f"Skipping unmatched teams: {r['home']} vs {r['away']}")
            continue

        if r["home_goals"] > r["away_goals"]:
            outcome = "A"
        elif r["home_goals"] < r["away_goals"]:
            outcome = "B"
        else:
            outcome = "draw"

        old_home, old_away = ratings[home], ratings[away]
        new_home, new_away = update_elo(old_home, old_away, outcome)
        ratings[home] = new_home
        ratings[away] = new_away

        if verbose:
            print(f"{r['home']} {r['home_goals']}-{r['away_goals']} {r['away']}: "
                  f"{home} {old_home:.0f}->{new_home:.0f}, "
                  f"{away} {old_away:.0f}->{new_away:.0f}")

    return ratings


if __name__ == "__main__":
    ratings = get_updated_elo_ratings(verbose=True)
    print("\nUpdated ratings (top 15):")
    for team, elo in sorted(ratings.items(), key=lambda x: -x[1])[:15]:
        print(f"{team:25s} {elo:.1f}")
