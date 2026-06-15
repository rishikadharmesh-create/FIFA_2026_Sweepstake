"""
Streamlit dashboard for the FIFA 2026 Sweepstake prediction model.

Run with:
    streamlit run dashboard/app.py

Shows:
- Live leaderboard of 16 participants
- Per-team probability breakdown
- Button to re-run simulation (pulls live Elo/results if configured)
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

import streamlit as st
import pandas as pd
import plotly.express as px

from tournament_simulator import run_simulation
from sweepstake_leaderboard import build_leaderboard, PRIZE_WEIGHTS
from sensitivity_analysis import (
    recommend_n_sims, run_sensitivity_study,
    QUICK_N_SIMS_LIST, QUICK_N_REPEATS, DATA_DIR,
)

SENS_CSV = os.path.join(DATA_DIR, "sensitivity_results.csv")

st.set_page_config(page_title="FIFA 2026 Sweepstake Predictor", layout="wide")

st.title("🏆 FIFA World Cup 2026 — Sweepstake Predictor")
st.caption("Live Monte Carlo simulation based on Elo ratings (sentiment & live results "
           "feed in as the tournament progresses)")

# --- Sidebar controls ---
st.sidebar.header("Simulation settings")

# Load precomputed sensitivity results (if available) for a recommended n_sims
sens_df = None
if os.path.exists(SENS_CSV):
    try:
        sens_df = pd.read_csv(SENS_CSV)
    except Exception:
        sens_df = None

recommended_n_sims = recommend_n_sims(sens_df) if sens_df is not None else None

if recommended_n_sims:
    st.sidebar.caption(
        f"💡 Recommended: **{recommended_n_sims:,}** simulations for stable, "
        f"precise results (see Reliability section below)"
    )
    if st.sidebar.button("Use recommended"):
        st.session_state["n_sims_slider"] = recommended_n_sims

if "n_sims_slider" not in st.session_state:
    st.session_state["n_sims_slider"] = recommended_n_sims or 10000

n_sims = st.sidebar.slider("Number of simulations", 1000, 50000, step=500, key="n_sims_slider")

st.sidebar.markdown("---")
st.sidebar.markdown("**Reproducibility**")
fixed_seed = st.sidebar.checkbox(
    "Use fixed random seed", value=True,
    help="With a fixed seed, re-running with the same settings always gives "
         "the same results. Turn off to sample a fresh random run each time."
)
seed_value = None
if fixed_seed:
    seed_value = st.sidebar.number_input("Seed", value=42, step=1)

run_button = st.sidebar.button("Run / Refresh Simulation")

st.sidebar.markdown("---")
st.sidebar.markdown("**Prize weighting**")
for pos, w in PRIZE_WEIGHTS.items():
    st.sidebar.markdown(f"- {pos.replace('_', ' ')}: weight {w}")

# --- Run simulation (cached) ---
@st.cache_data(show_spinner="Running tournament simulations...")
def get_results(n, seed):
    probs = run_simulation(n_sims=n, seed=seed)
    lb = build_leaderboard(probs)
    return probs, lb

if run_button:
    st.cache_data.clear()

probs, leaderboard = get_results(n_sims, seed_value)

# --- Leaderboard table ---
st.subheader("📊 Participant Leaderboard")
lb_df = pd.DataFrame([
    {
        "Rank": i + 1,
        "Name": e["name"],
        "Teams": ", ".join(e["teams"]),
        "Expected Score": round(e["expected_score"], 4),
    }
    for i, e in enumerate(leaderboard)
])
st.dataframe(lb_df, use_container_width=True, hide_index=True)

fig_lb = px.bar(
    lb_df.sort_values("Expected Score"),
    x="Expected Score", y="Name", orientation="h",
    title="Expected Sweepstake Score by Participant",
    text="Expected Score",
)
fig_lb.update_traces(texttemplate="%{text:.3f}", textposition="outside")
fig_lb.update_layout(height=500, yaxis_title="", xaxis_title="Expected Score")
st.plotly_chart(fig_lb, use_container_width=True)

st.markdown("---")

# --- Team probability table ---
st.subheader("⚽ Team Finish Probabilities")
team_df = pd.DataFrame([
    {
        "Team": team,
        "Champion": p["Champion"],
        "Runner-up": p["Runner-up"],
        "SF Loser 1": p["SF_Loser_1"],
        "SF Loser 2": p["SF_Loser_2"],
        "Eliminated Earlier": p["Eliminated"],
    }
    for team, p in probs.items()
]).sort_values("Champion", ascending=False)

st.dataframe(
    team_df.style.format({c: "{:.1%}" for c in team_df.columns if c != "Team"}),
    use_container_width=True, hide_index=True
)

# Stacked bar chart of finish-position probabilities per team (top 16 by Champion prob)
chart_df = team_df.head(16).melt(
    id_vars="Team",
    value_vars=["Champion", "Runner-up", "SF Loser 1", "SF Loser 2"],
    var_name="Position", value_name="Probability"
)
fig_team = px.bar(
    chart_df, x="Team", y="Probability", color="Position",
    title="Top 16 Teams — Probability by Finish Position",
    barmode="stack",
)
fig_team.update_layout(height=500, yaxis_tickformat=".0%")
st.plotly_chart(fig_team, use_container_width=True)

st.markdown("---")

# --- Per-participant drill-down ---
st.subheader("🔍 Participant Detail")
selected = st.selectbox("Select participant", [e["name"] for e in leaderboard])
entry = next(e for e in leaderboard if e["name"] == selected)

cols = st.columns(len(entry["teams"]))
for col, team in zip(cols, entry["teams"]):
    p = entry["breakdown"][team]
    with col:
        st.metric(label=team, value=f"{entry['expected_score']:.3f} pts contribution")
        st.write(f"Champion: {p.get('Champion', 0):.1%}")
        st.write(f"Runner-up: {p.get('Runner-up', 0):.1%}")
        st.write(f"SF Loser: {p.get('SF_Loser_1', 0) + p.get('SF_Loser_2', 0):.1%}")

        pie_data = pd.DataFrame({
            "Outcome": ["Champion", "Runner-up", "SF Loser", "Eliminated Earlier"],
            "Probability": [
                p.get("Champion", 0),
                p.get("Runner-up", 0),
                p.get("SF_Loser_1", 0) + p.get("SF_Loser_2", 0),
                p.get("Eliminated", 0),
            ]
        })
        fig_pie = px.pie(pie_data, names="Outcome", values="Probability", title=team, hole=0.4)
        fig_pie.update_layout(height=300, margin=dict(t=40, b=0, l=0, r=0))
        st.plotly_chart(fig_pie, use_container_width=True)

st.markdown("---")

# --- Simulation reliability section ---
with st.expander("📐 Simulation reliability & recommended settings"):
    st.markdown(
        "Monte Carlo results carry random noise: re-running with a different "
        "seed gives slightly different probabilities. The chart below shows "
        "how that noise shrinks as the number of simulations increases, and "
        "how often the **top-4 leaderboard** (i.e. who actually wins prizes) "
        "stays the same across repeated runs.\n\n"
        "**Precise** = low noise in individual team probabilities.  \n"
        "**Reproducible** = the top-4 ranking doesn't change between runs at "
        "this n_sims, and (with a fixed seed) re-running gives identical numbers."
    )

    if sens_df is not None:
        st.markdown(
            f"**Current recommendation: {recommended_n_sims:,} simulations** "
            f"(currently set to {n_sims:,})"
        )

        fig_noise = px.line(
            sens_df, x="n_sims",
            y=["avg_champion_prob_std", "max_champion_prob_std"],
            log_x=True, log_y=True, markers=True,
            labels={"value": "Std dev of Champion probability",
                    "n_sims": "Number of simulations", "variable": "Metric"},
            title="Result noise vs number of simulations (lower = more precise)",
        )
        st.plotly_chart(fig_noise, use_container_width=True)

        fig_stability = px.line(
            sens_df, x="n_sims", y="top4_stability",
            log_x=True, markers=True,
            labels={"top4_stability": "Top-4 stability",
                    "n_sims": "Number of simulations"},
            title="How often the top-4 leaderboard stays identical across repeats",
        )
        fig_stability.update_yaxes(tickformat=".0%", range=[0, 1.05])
        st.plotly_chart(fig_stability, use_container_width=True)

        st.dataframe(sens_df, use_container_width=True, hide_index=True)
    else:
        st.info("No reliability data found yet. Run a quick check below to generate it.")

    st.markdown("---")
    if st.button("🔄 Run quick reliability check (~30-40 seconds)"):
        with st.spinner("Running sensitivity study across several n_sims values..."):
            new_df = run_sensitivity_study(
                n_sims_list=QUICK_N_SIMS_LIST, n_repeats=QUICK_N_REPEATS, verbose=False
            )
            os.makedirs(DATA_DIR, exist_ok=True)
            new_df.to_csv(SENS_CSV, index=False)
        st.success("Reliability check complete — recommendation updated above.")
        st.rerun()

st.markdown("---")
st.caption("Data sources: Elo ratings (eloratings.net), live results (API-Football or "
           "data/manual_results.csv), sentiment analysis (planned). Elo ratings are "
           "adjusted based on completed World Cup matches before each simulation run.")
