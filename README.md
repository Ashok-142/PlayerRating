# Player Rating Tool (Cricket)

Python tool to generate player ratings from a CSV and select playing XI.

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
