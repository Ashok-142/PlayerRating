# Player Rating Tool (Cricket)

Python tool to generate player ratings from a CSV and select playing XI.

## Web app (CSV upload + tabs)

Run a simple web UI with tabs: `Scoring`, `Playing XI`, `Player Rating`, `Raw Input`, and `Config`.

- `Config` tab lets you edit weights/team structure.
- `Apply Config` uses your edited values immediately.
- `Save as Default Config` updates `configs/default_weights.json`.
- `Raw Input` shows aggregated player history generated from scored matches in DB.
- `Scoring` tab lets you:
  - create a match with home/away squads
  - add squads in a table with role dropdown per player
  - capture toss winner + toss decision (`bat first` / `bowl first`)
  - set total overs
  - score ball-by-ball with quick one-click actions (`0/1/2/3/4/6`, `Wide`, `No Ball`, `Bye`, `LegBye`, `Wicket`)
  - auto-setup first innings batting/bowling side in live console from toss details
  - view live ball-by-ball history directly in the live score screen
  - persist events + per-match batting/bowling aggregates into SQLite (`data/player_rating.db`)

```bash
pip install streamlit pandas
streamlit run app.py
```

## Database-backed scoring and player history

The app uses SQLite player history aggregated from scored matches for rating and team selection by default.
Ball-level events are stored in SQLite tables (`matches`, `innings`, `ball_events`, `player_match_batting_stats`, `player_match_bowling_stats`, etc.).
Player historical batting/bowling metrics used by the rating and team-selection flow can be loaded directly from this DB.

## Deploy online

### Render

This repo includes `requirements.txt`, `Procfile`, and `render.yaml` for quick deployment.

1. Push the repository to GitHub.
2. In Render, create a new **Web Service** and connect the repo.
3. Render auto-detects `render.yaml`, or use:
   - Build command: `pip install --upgrade pip && pip install -r requirements.txt`
   - Start command: `streamlit run app.py --server.address 0.0.0.0 --server.port $PORT`

### Other platforms (Railway/Heroku-like)

- Build/install: `pip install -r requirements.txt`
- Start: `streamlit run app.py --server.address 0.0.0.0 --server.port $PORT`

## Secrets and API keys

- Do not hardcode keys in source code.
- Use environment variables in production platforms (Render/Railway/Heroku).
- For local development, copy `.env.example` to `.env` and set values there.
- For Streamlit-hosted environments, you can also use `st.secrets`.

The project now includes `player_rating_tool/secrets.py` helpers:
- `get_secret("NAME")` for optional values
- `require_secret("NAME")` when a key is mandatory

## Quick start

```bash
python -m player_rating_tool.cli rate \
  --history data/sample_player_history.csv
```

```bash
python -m player_rating_tool.cli team \
  --history data/sample_player_history.csv \
  --weights configs/default_weights.json
```

## Input schema (`--history` CSV)

Required columns:
- `player_name`
- `role` (`Batter`, `Bowler`, `Allrounder`, `Wicket Keeper`)
- `availability` (`true`/`false`, `yes`/`no`, `1`/`0`)
- Batting:
  - `batting_matches`
  - `batting_innings`
  - `batting_runs`
  - `batting_not_out`
  - `batting_high_score`
  - `batting_avg`
  - `batting_strike_rate`
- Bowling:
  - `bowling_matches`
  - `bowling_innings`
  - `bowling_overs`
  - `bowling_runs`
  - `bowling_wickets`
  - `bowling_economy`
  - `bowling_strike_rate`
  - `bowling_avg`
  - `bowling_wides`
  - `bowling_no_ball`
- Fielding:
  - `fielding_matches`
  - `fielding_catches`
  - `fielding_caught_behind`
  - `fielding_run_out`
  - `fielding_stumping`

## Weight configuration

You can pass custom weights:

```bash
python -m player_rating_tool.cli rate \
  --history data/sample_player_history.csv \
  --weights configs/default_weights.json
```

Default config is in `/Users/ashok/Documents/PlayerRating_codex/configs/default_weights.json`.

## Outputs
- `rate` command: CSV with role + sub-scores + final rating.
- `team` command: CSV with selected XI based on role quotas and reliability-adjusted score.
  - output layout is role-wise sections (`Batter_table`, `Bowler_table`, `Allrounder_table`, `Wicket Keeper_table`)
  - top block includes `desired_rating_thresholds` by role.

Use `--output` to write output to file.

## Notes on logic
- Role comes from input CSV (tool does not auto-classify role).
- Batting, bowling, and fielding sub-scores are normalized and blended by role-specific weights.
- Team selection uses reliability-adjusted score:
  - `adjusted = (n/(n+k))*base_rating + (k/(n+k))*role_prior`
  - `n` is role-based innings (`batting_innings` or `bowling_innings`)
  - one emerging-player slot (low innings) is considered to avoid ignoring strong new players.
- Team selection considers only players where `availability = true`.
- Optional desired-rating filter:
  - derive desired rating per role from top-rated players in that role (based on requested role count)
  - only players meeting desired rating are selected
  - if fewer players qualify, XI output keeps blank rows for remaining slots (`reason=blank_slot`).
- `team_structure` and `desired_rating_filter_enabled` are configured in `configs/default_weights.json`.
