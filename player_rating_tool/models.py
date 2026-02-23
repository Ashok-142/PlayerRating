from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlayerStats:
    player_name: str
    role: str
    availability: bool
    batting_matches: int
    batting_innings: int
    batting_runs: int
    batting_not_out: int
    batting_high_score: int
    batting_avg: float
    batting_strike_rate: float
    bowling_matches: int
    bowling_innings: int
    bowling_overs: float
    bowling_runs: int
    bowling_wickets: int
    bowling_economy: float
    bowling_strike_rate: float
    bowling_avg: float
    bowling_wides: int
    bowling_no_ball: int
    fielding_matches: int
    fielding_catches: int
    fielding_caught_behind: int
    fielding_run_out: int
    fielding_stumping: int


@dataclass(frozen=True)
class PlayerProfile:
    player_name: str
    role: str
    rating: float
    batting_score: float
    bowling_score: float
    fielding_score: float
