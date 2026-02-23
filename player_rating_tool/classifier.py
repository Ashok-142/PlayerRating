from __future__ import annotations

from .models import PlayerSeasonStats


def classify_role(batting_score: float, bowling_score: float, allrounder_margin: float = 8.0) -> str:
    if abs(batting_score - bowling_score) <= allrounder_margin:
        return "allrounder"
    if batting_score > bowling_score:
        return "batter"
    return "bowler"


def batting_skill(stats: PlayerSeasonStats) -> float:
    run_impact = stats.runs / max(stats.matches, 1)
    return (stats.batting_average * 0.45) + (stats.strike_rate * 0.25) + (run_impact * 0.30)


def bowling_skill(stats: PlayerSeasonStats) -> float:
    wickets_per_match = stats.wickets / max(stats.matches, 1)
    avg_component = max(0.0, 60.0 - stats.bowling_average)
    economy_component = max(0.0, 12.0 - stats.economy) * 5
    return (wickets_per_match * 35.0) + (avg_component * 0.35) + (economy_component * 0.30)


def fielding_skill(stats: PlayerSeasonStats) -> float:
    catches_per_match = stats.catches / max(stats.matches, 1)
    return catches_per_match * 40.0
