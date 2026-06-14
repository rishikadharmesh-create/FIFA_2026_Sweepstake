# FIFA World Cup 2026 Sweepstake Predictor

Monte Carlo simulation dashboard predicting outcomes for a 16-person sweepstake
based on Elo ratings, with hooks for live results and sentiment analysis.

## Structure

```
fifa_sweepstake/
├── data/
│   └── participants.py       # 16 participants & their 3 assigned teams
├── src/
│   ├── elo_data.py            # Elo ratings (seed data + live fetch stub)
│   ├── live_data.py           # Live fixtures/results via API-Football
│   ├── prediction_model.py    # Elo -> match win/draw probability model
│   ├── tournament_structure.py# Group draw + bracket structure (placeholder)
│   ├── tournament_simulator.py # Monte Carlo tournament simulator
│   ├── sensitivity_analysis.py # Monte Carlo sensitivity / reliability study
│   ├── update_elo_from_results.py # Applies completed-match results to Elo ratings
│   └── leaderboard.py          # Maps team probs -> participant leaderboard
├── dashboard/
│   └── app.py                  # Streamlit live dashboard
└── requirements.txt
```

## Setup

```bash
pip install -r requirements.txt
```

Optional (for live match results):
```bash
export API_FOOTBALL_KEY="your_key_from_api-football.com"
```

## Run

```bash
# Quick CLI test
python src/tournament_simulator.py
python src/leaderboard.py

# Full dashboard
streamlit run dashboard/app.py
```

## Current status / what's real vs placeholder

- **Elo ratings**: `SEED_ELO` in `elo_data.py` is a hand-curated snapshot.
  Replace with live values from https://www.eloratings.net closer to the tournament.
- **Group draw**: `tournament_structure.py` uses a *placeholder* Elo-seeded
  draw and bracket pairing. **Replace `PARTICIPANT_TEAMS` group assignment and
  `R32_PAIRING_TEMPLATE` with the real draw** once announced (Dec 2025).
- **Live results**: `live_data.py` is wired to API-Football but needs an API key
  and the correct competition/league ID for the 2026 World Cup (confirm via
  the `/leagues` endpoint nearer the time).
- **Sentiment analysis**: not yet implemented. `prediction_model.py` already
  supports a `sentiment_score` adjustment per team (range -1 to 1); next step
  is building a module that scrapes/queries news & social media and outputs
  these scores into the `sentiment` dict passed to `run_simulation()`.

## Next steps (priority order)

1. **Plug in real Elo data** — replace SEED_ELO with a scraper/API for eloratings.net.
2. **Replace placeholder draw** once the real Dec 2025 draw happens.
3. **Wire up live results** — get API-Football key, confirm league/season IDs,
   implement Elo updates after each completed match (`prediction_model.update_elo`),
   and re-run simulation automatically (e.g. on a schedule via cron + cache invalidation).
4. **Sentiment module** — build `src/sentiment.py` using news API + Reddit/X scraping,
   output `{team: score}` dict, feed into `run_simulation(sentiment=...)`.
5. **Persist simulation history** — log results per matchday to track how
   each participant's odds evolve over the tournament (nice dashboard chart).
6. **Improve bracket realism** — currently uses random tiebreaks for group
   standings (3rd place ranking) and random bracket slotting; replace with
   actual goal-difference tracking and the real FIFA bracket pairing rules.
