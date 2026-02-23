# Player Rating Tool (Cricket)

Python tool to:
- classify players into `batter`, `bowler`, `allrounder`
- generate rating based on historical performance
- select a team based on rating + target team structure

## Quick start

```bash
python -m player_rating_tool.cli rate \
  --history data/sample_player_history.csv
```

```bash
python -m player_rating_tool.cli team \
  --history data/sample_player_history.csv \
  --team-structure '{"batter":4,"bowler":3,"allrounder":4}'
```

## Input schema (`--history` CSV)

Required columns:
- `player_id`
- `player_name`
- `season`
- `matches`
- `runs`
- `batting_average`
- `strike_rate`
- `wickets`
- `bowling_average`
- `economy`
- `catches`

## Weight configuration

You can pass custom weights:

```bash
python -m player_rating_tool.cli rate \
  --history data/sample_player_history.csv \
  --weights configs/default_weights.json
```

Default config is in `/Users/ashok/Documents/PlayerRating_codex/configs/default_weights.json`.

## Outputs
- `rate` command: CSV with per-player role + scores + final rating.
- `team` command: CSV with selected squad from rated players.

Use `--output` to write output to file.

## Notes on logic
- Recent season is weighted more heavily than older seasons.
- Batting and bowling skill are calculated separately.
- Role classification uses the gap between batting and bowling scores.
- Team selection first satisfies role counts, then fills remaining slots by highest rating.
- If the player pool cannot satisfy a role quota, CLI prints a warning and backfills with best remaining players.

## Next steps
See `/Users/ashok/Documents/PlayerRating_codex/SYSTEM_DESIGN.md` for a scalable architecture that supports predictive ratings, constraints, and explainable team selection.
