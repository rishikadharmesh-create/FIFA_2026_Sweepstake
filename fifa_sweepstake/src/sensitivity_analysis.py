"""
Monte Carlo sensitivity analysis: how does the number of simulations (n_sims)
affect the stability of the results?

WHY THIS MATTERS
Each call to run_simulation() uses random sampling, so results vary slightly
between runs. More simulations = less random noise, but takes longer to run.
This script answers: "how many simulations do I actually need before the
results stop changing meaningfully?"

METHOD
For each candidate n_sims value, run the simulation N_REPEATS times with
different random seeds. The spread (standard deviation) of key outputs across
those repeats measures how "noisy" the results are at that n_sims -- i.e. how
much the numbers would change if you happened to get a different random seed.

OUTPUTS
- data/sensitivity_results.csv -- summary table (one row per n_sims tested)
- data/sensitivity_plots.png    -- 3-panel chart:
    1. Std dev of each team's Champion probability vs n_sims
    2. Std dev of each participant's expected sweepstake score vs n_sims
    3. Stability of the "top 4" prize-winning participants vs n_sims

USAGE
    python sensitivity_analysis.py

EXPECTED RUNTIME
With the default settings (8 n_sims values x 10 repeats), this takes roughly
2-3 minutes. Reduce N_SIMS_LIST or N_REPEATS below for a quicker check.
"""

import os
import time
from collections import Counter

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from tournament_simulator import run_simulation
from sweepstake_leaderboard import build_leaderboard
from tournament_structure import PARTICIPANT_TEAMS

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# Candidate simulation counts to test
N_SIMS_LIST = [100, 500, 1000, 2500, 5000, 10000, 20000, 50000]

# Independent repeats per n_sims value (different random seeds each time)
N_REPEATS = 10

# Faster settings used by the dashboard's on-demand "quick check" button
QUICK_N_SIMS_LIST = [1000, 2500, 5000, 10000, 20000]
QUICK_N_REPEATS = 5


def run_sensitivity_study(n_sims_list=N_SIMS_LIST, n_repeats=N_REPEATS, verbose=True):
    rows = []

    for n in n_sims_list:
        champion_runs = {team: [] for team in PARTICIPANT_TEAMS}
        score_runs = {}
        top4_sets = []

        t0 = time.time()
        for rep in range(n_repeats):
            probs = run_simulation(n_sims=n, seed=rep)

            for team in PARTICIPANT_TEAMS:
                champion_runs[team].append(probs[team]["Champion"])

            lb = build_leaderboard(probs)
            for entry in lb:
                score_runs.setdefault(entry["name"], []).append(entry["expected_score"])

            top4 = frozenset(e["name"] for e in lb[:4])
            top4_sets.append(top4)

        elapsed = time.time() - t0

        champ_stds = [np.std(v) for v in champion_runs.values()]
        score_stds = [np.std(v) for v in score_runs.values()]

        # Stability: fraction of repeats whose top-4 set matches the most
        # common top-4 set seen across all repeats at this n_sims
        most_common_top4, count = Counter(top4_sets).most_common(1)[0]
        top4_stability = count / n_repeats

        rows.append({
            "n_sims": n,
            "avg_champion_prob_std": np.mean(champ_stds),
            "max_champion_prob_std": np.max(champ_stds),
            "avg_score_std": np.mean(score_stds),
            "max_score_std": np.max(score_stds),
            "top4_stability": top4_stability,
            "seconds_per_run": elapsed / n_repeats,
        })

        if verbose:
            print(
                f"n_sims={n:6d} | champion prob std: avg={np.mean(champ_stds):.4f} "
                f"max={np.max(champ_stds):.4f} | score std: avg={np.mean(score_stds):.4f} "
                f"max={np.max(score_stds):.4f} | top4 stability={top4_stability:.0%} | "
                f"{elapsed / n_repeats:.2f}s/run"
            )

    return pd.DataFrame(rows)


def recommend_n_sims(df, prob_threshold=0.005, top4_threshold=1.0):
    """
    Recommend a number of simulations based on a sensitivity results DataFrame
    (as produced by run_sensitivity_study).

    A value is considered "reliable" if, across repeated runs:
    - the average Champion-probability noise is below `prob_threshold`
      (default: 0.5 percentage points) -- this is the PRECISION criterion, and
    - the top-4 sweepstake leaderboard is identical across repeats
      (top4_stability >= `top4_threshold`, default 100%) -- this is the
      REPRODUCIBILITY criterion most relevant to the sweepstake outcome.

    Returns the smallest n_sims meeting both criteria. If none qualify,
    falls back to the n_sims with the highest top4_stability (tie-broken by
    lowest noise).
    """
    if df is None or df.empty:
        return None

    df_sorted = df.sort_values("n_sims")
    candidates = df_sorted[
        (df_sorted["avg_champion_prob_std"] < prob_threshold)
        & (df_sorted["top4_stability"] >= top4_threshold)
    ]
    if not candidates.empty:
        return int(candidates.iloc[0]["n_sims"])

    fallback = df_sorted.sort_values(
        ["top4_stability", "avg_champion_prob_std"], ascending=[False, True]
    ).iloc[0]
    return int(fallback["n_sims"])


def plot_results(df, out_path=None):
    out_path = out_path or os.path.join(DATA_DIR, "sensitivity_plots.png")

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    # Panel 1: Champion probability noise vs n_sims
    ax = axes[0]
    ax.loglog(df["n_sims"], df["avg_champion_prob_std"], "o-", label="avg across teams")
    ax.loglog(df["n_sims"], df["max_champion_prob_std"], "s--", label="max across teams")
    # 1/sqrt(n) reference line, anchored to the first data point
    ref = df["avg_champion_prob_std"].iloc[0] * np.sqrt(df["n_sims"].iloc[0] / df["n_sims"])
    ax.loglog(df["n_sims"], ref, ":", color="gray", label="1/sqrt(n) reference")
    ax.set_xlabel("Number of simulations")
    ax.set_ylabel("Std dev of Champion probability")
    ax.set_title("Champion probability noise vs n_sims")
    ax.legend()
    ax.grid(True, which="both", ls=":")

    # Panel 2: Leaderboard expected-score noise vs n_sims
    ax = axes[1]
    ax.loglog(df["n_sims"], df["avg_score_std"], "o-", label="avg across participants")
    ax.loglog(df["n_sims"], df["max_score_std"], "s--", label="max across participants")
    ax.set_xlabel("Number of simulations")
    ax.set_ylabel("Std dev of expected score")
    ax.set_title("Leaderboard score noise vs n_sims")
    ax.legend()
    ax.grid(True, which="both", ls=":")

    # Panel 3: Top-4 stability
    ax = axes[2]
    ax.semilogx(df["n_sims"], df["top4_stability"] * 100, "o-", color="green")
    ax.set_xlabel("Number of simulations")
    ax.set_ylabel("Top-4 stability (%)")
    ax.set_title("How often the 'top 4' participants\nstay the same across repeats")
    ax.set_ylim(0, 105)
    ax.grid(True, which="both", ls=":")

    plt.tight_layout()
    plt.savefig(out_path, dpi=120)
    print(f"\nSaved plots to {out_path}")


if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)

    df = run_sensitivity_study()

    csv_path = os.path.join(DATA_DIR, "sensitivity_results.csv")
    df.to_csv(csv_path, index=False)
    print(f"\nSaved summary table to {csv_path}")

    plot_results(df)

    # Simple recommendation based on champion-probability noise
    threshold = 0.005  # 0.5 percentage points
    candidates = df[df["avg_champion_prob_std"] < threshold]
    if not candidates.empty:
        rec = int(candidates.iloc[0]["n_sims"])
        print(
            f"\nRecommendation: n_sims >= {rec} keeps average Champion "
            f"probability noise below {threshold:.1%} across repeats."
        )
    else:
        print(
            f"\nNone of the tested n_sims values bring average noise below "
            f"{threshold:.1%}; consider testing larger values in N_SIMS_LIST."
        )
