"""
Monte Carlo simulator for the full 2026 World Cup, producing probability
distributions for each team finishing as:
    Champion, Runner-up, SF_Loser_1, SF_Loser_2 (and earlier exits)

Usage:
    python simulate.py

Output: data/simulation_results.csv with per-team finish probabilities.
"""

import random
import itertools
import csv
import os

from elo_data import get_elo_ratings, get_team_elo, DEFAULT_ELO
from prediction_model import simulate_match, adjusted_elo
from tournament_structure import PARTICIPANT_TEAMS, generate_placeholder_groups
from update_elo_from_results import get_updated_elo_ratings

N_SIMULATIONS = 10000


def simulate_group_stage(groups, elo, sentiment, rng):
    """
    Simulate one group's matches (round-robin), return ranked team list
    [1st, 2nd, 3rd, 4th] by points (tiebreak: random for simplicity --
    real version should track goal difference).
    """
    standings = {}
    for group_name, teams in groups.items():
        points = {t: 0 for t in teams}
        for a, b in itertools.combinations(teams, 2):
            elo_a = adjusted_elo(elo.get(a, DEFAULT_ELO), sentiment.get(a, 0))
            elo_b = adjusted_elo(elo.get(b, DEFAULT_ELO), sentiment.get(b, 0))
            result = simulate_match(elo_a, elo_b, knockout=False, neutral=True, rng=rng)
            if result == "A":
                points[a] += 3
            elif result == "B":
                points[b] += 3
            else:
                points[a] += 1
                points[b] += 1
        # rank with random tiebreak (placeholder for goal difference)
        ranked = sorted(teams, key=lambda t: (points[t], rng.random()), reverse=True)
        standings[group_name] = ranked
    return standings


def get_advancers(standings, rng):
    """
    From group standings, get the 32 teams advancing:
    top 2 of each group + 8 best third-place teams (by group points, random tiebreak here).
    Returns dict: {team: seed_label} e.g. "A1", "A2", "A3rd" -- simplified to a flat list
    plus mapping for bracket slotting.
    """
    advancers = []
    thirds = []
    seed_map = {}
    for group_name, ranked in standings.items():
        advancers.append(ranked[0])
        seed_map[ranked[0]] = f"{group_name}1"
        advancers.append(ranked[1])
        seed_map[ranked[1]] = f"{group_name}2"
        thirds.append((ranked[2], group_name))

    # pick 8 best thirds at random (placeholder for real points-based ranking)
    rng.shuffle(thirds)
    best_thirds = thirds[:8]
    for team, group_name in best_thirds:
        advancers.append(team)
        seed_map[team] = f"{group_name}3"

    return advancers, seed_map


def simulate_knockouts(advancers, elo, sentiment, rng):
    """
    Simulate single-elimination bracket from Round of 32 to Final.
    advancers: list of 32 team names (order = bracket slotting)
    Returns dict with keys: champion, runner_up, sf_losers (list of 2)
    """
    round_teams = list(advancers)
    rng.shuffle(round_teams)  # placeholder bracket randomization
    semi_finalists = None

    while len(round_teams) > 1:
        next_round = []
        if len(round_teams) == 4:
            semi_finalists = list(round_teams)
        for i in range(0, len(round_teams), 2):
            a, b = round_teams[i], round_teams[i + 1]
            elo_a = adjusted_elo(elo.get(a, DEFAULT_ELO), sentiment.get(a, 0))
            elo_b = adjusted_elo(elo.get(b, DEFAULT_ELO), sentiment.get(b, 0))
            result = simulate_match(elo_a, elo_b, knockout=True, neutral=True, rng=rng)
            next_round.append(a if result == "A" else b)
        round_teams = next_round

    champion = round_teams[0]

    # determine runner-up and SF losers
    # semi_finalists = the 4 teams in SFs; 2 became finalists, 2 lost SFs
    # re-simulate is avoided by tracking; simpler: rerun final pairing logic
    # To keep this self-contained, recompute final match losers from semi_finalists
    sf_pairs = [(semi_finalists[0], semi_finalists[1]), (semi_finalists[2], semi_finalists[3])]
    finalists = []
    sf_losers = []
    for a, b in sf_pairs:
        elo_a = adjusted_elo(elo.get(a, DEFAULT_ELO), sentiment.get(a, 0))
        elo_b = adjusted_elo(elo.get(b, DEFAULT_ELO), sentiment.get(b, 0))
        result = simulate_match(elo_a, elo_b, knockout=True, neutral=True, rng=rng)
        winner = a if result == "A" else b
        loser = b if result == "A" else a
        finalists.append(winner)
        sf_losers.append(loser)

    elo_f1 = adjusted_elo(elo.get(finalists[0], DEFAULT_ELO), sentiment.get(finalists[0], 0))
    elo_f2 = adjusted_elo(elo.get(finalists[1], DEFAULT_ELO), sentiment.get(finalists[1], 0))
    final_result = simulate_match(elo_f1, elo_f2, knockout=True, neutral=True, rng=rng)
    champion = finalists[0] if final_result == "A" else finalists[1]
    runner_up = finalists[1] if final_result == "A" else finalists[0]

    return {
        "champion": champion,
        "runner_up": runner_up,
        "sf_losers": sf_losers,
    }


def run_simulation(n_sims=N_SIMULATIONS, sentiment=None, seed=None, use_live_results=True):
    """
    Run the full Monte Carlo simulation.

    sentiment: optional dict {team: score in [-1,1]} from sentiment analysis module
    use_live_results: if True (default), Elo ratings are first adjusted based on
                       completed 2026 World Cup matches (live API + data/manual_results.csv)
                       before the simulation runs -- so results so far influence
                       all future-projection probabilities.

    Returns dict {team: {"Champion": prob, "Runner-up": prob,
                          "SF_Loser_1": prob, "SF_Loser_2": prob, "Eliminated": prob}}
    """
    rng = random.Random(seed)
    sentiment = sentiment or {}
    elo = get_updated_elo_ratings() if use_live_results else get_elo_ratings()

    counts = {team: {"Champion": 0, "Runner-up": 0, "SF_Loser_1": 0,
                      "SF_Loser_2": 0, "Eliminated": 0} for team in PARTICIPANT_TEAMS}

    for _ in range(n_sims):
        groups = generate_placeholder_groups(lambda t: get_team_elo(t, elo))
        standings = simulate_group_stage(groups, elo, sentiment, rng)
        advancers, _ = get_advancers(standings, rng)
        outcome = simulate_knockouts(advancers, elo, sentiment, rng)

        for team in PARTICIPANT_TEAMS:
            if team == outcome["champion"]:
                counts[team]["Champion"] += 1
            elif team == outcome["runner_up"]:
                counts[team]["Runner-up"] += 1
            elif team == outcome["sf_losers"][0]:
                counts[team]["SF_Loser_1"] += 1
            elif team == outcome["sf_losers"][1]:
                counts[team]["SF_Loser_2"] += 1
            else:
                counts[team]["Eliminated"] += 1

    probs = {
        team: {k: v / n_sims for k, v in c.items()}
        for team, c in counts.items()
    }
    return probs


def save_results(probs, path="data/simulation_results.csv"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Team", "Champion", "Runner-up", "SF_Loser_1", "SF_Loser_2", "Eliminated"])
        for team, p in sorted(probs.items(), key=lambda x: -x[1]["Champion"]):
            writer.writerow([team, p["Champion"], p["Runner-up"], p["SF_Loser_1"], p["SF_Loser_2"], p["Eliminated"]])


if __name__ == "__main__":
    probs = run_simulation()
    save_results(probs)
    print("Top 10 teams by Champion probability:")
    for team, p in sorted(probs.items(), key=lambda x: -x[1]["Champion"])[:10]:
        print(f"{team:25s} Champion={p['Champion']:.3f}  Runner-up={p['Runner-up']:.3f}  "
              f"SF1={p['SF_Loser_1']:.3f}  SF2={p['SF_Loser_2']:.3f}")
