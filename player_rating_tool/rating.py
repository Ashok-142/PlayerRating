from __future__ import annotations

import json
from pathlib import Path

from .classifier import batting_skill, bowling_skill, fielding_skill
from .models import PlayerProfile, PlayerStats

DEFAULT_WEIGHTS = {
    "batter_batting_weight": 0.78,
    "batter_bowling_weight": 0.05,
    "batter_fielding_weight": 0.17,
    "bowler_batting_weight": 0.05,
    "bowler_bowling_weight": 0.78,
    "bowler_fielding_weight": 0.17,
    "allrounder_batting_weight": 0.44,
    "allrounder_bowling_weight": 0.41,
    "allrounder_fielding_weight": 0.15,
    "wicket_keeper_batting_weight": 0.50,
    "wicket_keeper_bowling_weight": 0.08,
    "wicket_keeper_fielding_weight": 0.42,
    "selection_shrinkage_k": 20.0,
    "emerging_max_innings": 12.0,
    "emerging_slots": 1.0,
    "desired_rating_filter_enabled": 0.0,
    "team_structure": {
        "Batter": 4,
        "Bowler": 3,
        "Allrounder": 3,
        "Wicket Keeper": 1,
    },
}


def load_weights(path: str | None = None) -> dict[str, object]:
    if path is None:
        return DEFAULT_WEIGHTS.copy()

    config = DEFAULT_WEIGHTS.copy()
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    for k, v in payload.items():
        if k not in config:
            continue
        if isinstance(config[k], dict):
            if not isinstance(v, dict):
                raise ValueError(f"Expected object for '{k}'")
            config[k] = {str(role): int(count) for role, count in v.items()}
        else:
            config[k] = float(v)
    return config


def _role_weights(role: str, weights: dict[str, float]) -> tuple[float, float, float]:
    if role == "Batter":
        return (
            weights["batter_batting_weight"],
            weights["batter_bowling_weight"],
            weights["batter_fielding_weight"],
        )
    if role == "Bowler":
        return (
            weights["bowler_batting_weight"],
            weights["bowler_bowling_weight"],
            weights["bowler_fielding_weight"],
        )
    if role == "Allrounder":
        return (
            weights["allrounder_batting_weight"],
            weights["allrounder_bowling_weight"],
            weights["allrounder_fielding_weight"],
        )
    if role == "Wicket Keeper":
        return (
        weights["wicket_keeper_batting_weight"],
        weights["wicket_keeper_bowling_weight"],
        weights["wicket_keeper_fielding_weight"],
        )
    # Neutral fallback when role is blank.
    return (
        weights["allrounder_batting_weight"],
        weights["allrounder_bowling_weight"],
        weights["allrounder_fielding_weight"],
    )


def rate_players(records: list[PlayerStats], weights: dict[str, float]) -> list[PlayerProfile]:
    profiles: list[PlayerProfile] = []

    for stats in records:
        batting = batting_skill(stats)
        bowling = bowling_skill(stats)
        fielding = fielding_skill(stats)
        role = stats.role

        batting_w, bowling_w, fielding_w = _role_weights(role, weights)
        rating = (batting * batting_w) + (bowling * bowling_w) + (fielding * fielding_w)

        profiles.append(
            PlayerProfile(
                player_name=stats.player_name,
                role=role,
                rating=round(rating, 2),
                batting_score=round(batting, 2),
                bowling_score=round(bowling, 2),
                fielding_score=round(fielding, 2),
            )
        )

    return sorted(profiles, key=lambda p: p.rating, reverse=True)


def rate_player(player_record: PlayerStats, weights: dict[str, float]) -> PlayerProfile:
    return rate_players([player_record], weights)[0]
