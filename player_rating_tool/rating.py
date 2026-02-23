from __future__ import annotations

import json
from pathlib import Path

from .classifier import batting_skill, bowling_skill, classify_role, fielding_skill
from .loader import group_by_player
from .models import PlayerProfile, PlayerSeasonStats

DEFAULT_WEIGHTS = {
    "recent_season_weight": 0.6,
    "past_season_weight": 0.4,
    "batting_role_weight": 0.70,
    "bowling_role_weight": 0.70,
    "allrounder_split_weight": 0.45,
    "fielding_weight": 0.10,
    "allrounder_margin": 8.0,
}


def load_weights(path: str | None = None) -> dict[str, float]:
    if path is None:
        return DEFAULT_WEIGHTS.copy()

    config = DEFAULT_WEIGHTS.copy()
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    config.update({k: float(v) for k, v in payload.items() if k in config})
    return config


def _blend_scores(series: list[float], recent_weight: float, past_weight: float) -> float:
    if not series:
        return 0.0
    if len(series) == 1:
        return series[0]
    return (series[-1] * recent_weight) + ((sum(series[:-1]) / (len(series) - 1)) * past_weight)


def rate_players(records: list[PlayerSeasonStats], weights: dict[str, float]) -> list[PlayerProfile]:
    grouped = group_by_player(records)
    profiles: list[PlayerProfile] = []

    for seasons in grouped.values():
        seasons_sorted = sorted(seasons, key=lambda x: x.season)
        recent_weight = weights["recent_season_weight"]
        past_weight = weights["past_season_weight"]

        batting = _blend_scores([batting_skill(s) for s in seasons_sorted], recent_weight, past_weight)
        bowling = _blend_scores([bowling_skill(s) for s in seasons_sorted], recent_weight, past_weight)
        fielding = _blend_scores([fielding_skill(s) for s in seasons_sorted], recent_weight, past_weight)

        role = classify_role(batting, bowling, allrounder_margin=weights["allrounder_margin"])

        if role == "batter":
            rating = (batting * weights["batting_role_weight"]) + (fielding * weights["fielding_weight"])
        elif role == "bowler":
            rating = (bowling * weights["bowling_role_weight"]) + (fielding * weights["fielding_weight"])
        else:
            rating = (
                (batting * weights["allrounder_split_weight"])
                + (bowling * weights["allrounder_split_weight"])
                + (fielding * weights["fielding_weight"])
            )

        latest = seasons_sorted[-1]
        profiles.append(
            PlayerProfile(
                player_id=latest.player_id,
                player_name=latest.player_name,
                role=role,
                rating=round(rating, 2),
                batting_score=round(batting, 2),
                bowling_score=round(bowling, 2),
                fielding_score=round(fielding, 2),
            )
        )

    return sorted(profiles, key=lambda p: p.rating, reverse=True)


def rate_player(player_records: list[PlayerSeasonStats], weights: dict[str, float]) -> PlayerProfile:
    if not player_records:
        raise ValueError("No records provided")
    return rate_players(player_records, weights)[0]
