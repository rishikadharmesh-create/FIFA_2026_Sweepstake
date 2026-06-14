"""
Maps team-level simulation probabilities to the 16 sweepstake participants,
producing a leaderboard ranking each person by their expected sweepstake outcome.

Scoring approach: each person's "score" = sum over their 3 teams of the
probability that team finishes in each prize position, weighted by prize value.
Weights are illustrative -- adjust to match actual prize structure.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "data"))

from participants import PARTICIPANTS

# Prize weighting (Champion worth most, then Runner-up, then SF losers equally)
PRIZE_WEIGHTS = {
    "Champion": 4,
    "Runner-up": 3,
    "SF_Loser_1": 2,
    "SF_Loser_2": 2,
}


def build_leaderboard(probs):
    """
    probs: dict {team: {"Champion": p, "Runner-up": p, "SF_Loser_1": p, "SF_Loser_2": p, ...}}
    Returns list of dicts sorted by expected_score descending:
        {name, teams, expected_score, breakdown: {team: {position: prob}}}
    """
    leaderboard = []
    for name, teams in PARTICIPANTS.items():
        score = 0.0
        breakdown = {}
        for team in teams:
            team_probs = probs.get(team, {})
            breakdown[team] = team_probs
            for pos, weight in PRIZE_WEIGHTS.items():
                score += team_probs.get(pos, 0.0) * weight
        leaderboard.append({
            "name": name,
            "teams": teams,
            "expected_score": score,
            "breakdown": breakdown,
        })

    leaderboard.sort(key=lambda x: -x["expected_score"])
    return leaderboard


if __name__ == "__main__":
    from simulate import run_simulation
    probs = run_simulation(n_sims=5000)
    lb = build_leaderboard(probs)
    print(f"{'Rank':<5}{'Name':<10}{'Teams':<45}{'Score':<8}")
    for i, entry in enumerate(lb, 1):
        print(f"{i:<5}{entry['name']:<10}{', '.join(entry['teams']):<45}{entry['expected_score']:.4f}")
