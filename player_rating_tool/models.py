from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlayerSeasonStats:
    player_id: str
    player_name: str
    season: int
    matches: int
    runs: int
    batting_average: float
    strike_rate: float
    wickets: int
    bowling_average: float
    economy: float
    catches: int


@dataclass(frozen=True)
class PlayerProfile:
    player_id: str
    player_name: str
    role: str
    rating: float
    batting_score: float
    bowling_score: float
    fielding_score: float
