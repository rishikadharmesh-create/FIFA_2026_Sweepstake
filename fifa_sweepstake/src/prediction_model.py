"""
Match outcome prediction model based on Elo ratings.

Win probability formula (standard Elo for football, World Football Elo style):
    P(A beats B) = 1 / (1 + 10^(-(EloA - EloB + home_adv) / 400))

For knockout matches (no draws allowed - extra time/penalties), we convert
the draw probability into a 50/50 split for whoever "wins" the tie.

Sentiment/news adjustment: optional small Elo bonus/penalty derived from
an external sentiment score in range [-1, 1], scaled by SENTIMENT_WEIGHT.
"""

import random

HOME_ADVANTAGE = 30  # Elo points bonus for home team (small/neutral for WC)
DRAW_PROB_BASE = 0.24  # base probability of a draw in group-stage matches
SENTIMENT_WEIGHT = 40  # max Elo points swing from sentiment score of +-1


def adjusted_elo(base_elo, sentiment_score=0.0):
    """Apply sentiment adjustment to a base Elo rating."""
    return base_elo + sentiment_score * SENTIMENT_WEIGHT


def win_draw_probabilities(elo_a, elo_b, neutral=True):
    """
    Returns (p_win_a, p_draw, p_win_b) for a group-stage match (draws allowed).
    """
    home_adv = 0 if neutral else HOME_ADVANTAGE
    diff = elo_a - elo_b + home_adv

    p_a_no_draw = 1 / (1 + 10 ** (-diff / 400))

    # Scale draw probability down as the rating gap widens
    gap_factor = max(0.0, 1 - abs(diff) / 800)
    p_draw = DRAW_PROB_BASE * gap_factor

    p_a = p_a_no_draw * (1 - p_draw)
    p_b = (1 - p_a_no_draw) * (1 - p_draw)

    return p_a, p_draw, p_b


def knockout_win_probability(elo_a, elo_b, neutral=True):
    """
    Returns p_a (probability team A advances) for a knockout match.
    Draw probability is redistributed proportionally between A and B,
    representing the coin-flip nature of extra time / penalties.
    """
    p_a, p_draw, p_b = win_draw_probabilities(elo_a, elo_b, neutral=neutral)
    p_a_total = p_a + p_draw * (p_a / (p_a + p_b))
    return p_a_total


def simulate_match(elo_a, elo_b, knockout=False, neutral=True, rng=None):
    """
    Simulate a single match outcome.
    Returns "A", "B", or "draw" (only possible if knockout=False).
    """
    rng = rng or random
    if knockout:
        p_a = knockout_win_probability(elo_a, elo_b, neutral=neutral)
        return "A" if rng.random() < p_a else "B"
    else:
        p_a, p_draw, p_b = win_draw_probabilities(elo_a, elo_b, neutral=neutral)
        r = rng.random()
        if r < p_a:
            return "A"
        elif r < p_a + p_draw:
            return "draw"
        else:
            return "B"


def update_elo(elo_a, elo_b, result, k=30):
    """
    Update Elo ratings after a real match result.
    result: "A" (A won), "B" (B won), or "draw"
    Returns (new_elo_a, new_elo_b)
    """
    p_a, _, p_b = win_draw_probabilities(elo_a, elo_b, neutral=True)
    score_a = {"A": 1.0, "draw": 0.5, "B": 0.0}[result]
    expected_a = p_a + (1 - p_a - p_b) * 0.5  # treat draw chance as half-credit baseline

    new_elo_a = elo_a + k * (score_a - expected_a)
    new_elo_b = elo_b + k * ((1 - score_a) - (1 - expected_a))
    return new_elo_a, new_elo_b
