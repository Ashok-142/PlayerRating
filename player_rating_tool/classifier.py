from __future__ import annotations

from .models import PlayerStats

def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _scale_higher_better(value: float, floor: float, ceiling: float) -> float:
    if ceiling <= floor:
        return 0.0
    return _clamp(((value - floor) / (ceiling - floor)) * 100.0)


def _scale_lower_better(value: float, best: float, worst: float) -> float:
    if worst <= best:
        return 0.0
    return _clamp(((worst - value) / (worst - best)) * 100.0)


def batting_skill(stats: PlayerStats) -> float:
    runs_per_innings = stats.batting_runs / max(stats.batting_innings, 1)

    return (
        (_scale_higher_better(stats.batting_avg, 10.0, 65.0) * 0.15)
        + (_scale_higher_better(stats.batting_strike_rate, 70.0, 190.0) * 0.35)
        + (_scale_higher_better(runs_per_innings, 5.0, 80.0) * 0.35)
        + (_scale_higher_better(stats.batting_high_score, 20.0, 180.0) * 0.15)
    )


def bowling_skill(stats: PlayerStats) -> float:
    if (
        stats.bowling_innings <= 0
        and stats.bowling_overs <= 0
        and stats.bowling_wickets <= 0
        and stats.bowling_runs <= 0
    ):
        return 0.0

    wickets_per_innings = stats.bowling_wickets / max(stats.bowling_innings, 1)
    extras_per_over = (stats.bowling_wides + stats.bowling_no_ball) / max(stats.bowling_overs, 1.0)

    return (
        (_scale_higher_better(wickets_per_innings, 0.0, 3.0) * 0.35)
        + (_scale_lower_better(stats.bowling_economy, 4.0, 11.0) * 0.20)
        + (_scale_lower_better(stats.bowling_strike_rate, 8.0, 40.0) * 0.20)
        + (_scale_lower_better(stats.bowling_avg, 10.0, 50.0) * 0.15)
        + (_scale_lower_better(extras_per_over, 0.0, 2.5) * 0.10)
    )


def fielding_skill(stats: PlayerStats) -> float:
    catches_per_match = stats.fielding_catches / max(stats.fielding_matches, 1)
    run_out_per_match = stats.fielding_run_out / max(stats.fielding_matches, 1)
    caught_behind_per_match = stats.fielding_caught_behind / max(stats.fielding_matches, 1)
    stumping_per_match = stats.fielding_stumping / max(stats.fielding_matches, 1)

    return (
        (_scale_higher_better(catches_per_match, 0.0, 1.2) * 0.45)
        + (_scale_higher_better(run_out_per_match, 0.0, 0.6) * 0.20)
        + (_scale_higher_better(caught_behind_per_match, 0.0, 0.6) * 0.15)
        + (_scale_higher_better(stumping_per_match, 0.0, 0.8) * 0.20)
    )
