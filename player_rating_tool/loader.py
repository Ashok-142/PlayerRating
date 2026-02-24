from __future__ import annotations

import csv
import re
from pathlib import Path

from .models import PlayerStats


CANONICAL_COLUMNS = {
    "player_name": ["player_name", "player name"],
    "role": ["role"],
    "availability": ["availability", "available", "is_available", "player_available"],
    "batting_matches": ["batting_matches", "batting matches"],
    "batting_innings": ["batting_innings", "batting innings"],
    "batting_runs": ["batting_runs", "batting runs"],
    "batting_not_out": ["batting_not_out", "batting not out"],
    "batting_high_score": ["batting_high_score", "batting high score", "batting hs"],
    "batting_avg": ["batting_avg", "batting avg"],
    "batting_strike_rate": ["batting_strike_rate", "batting strike rate"],
    "bowling_matches": ["bowling_matches", "bowling matches"],
    "bowling_innings": ["bowling_innings", "bowling inns", "bowling innings"],
    "bowling_overs": ["bowling_overs", "bowling overs"],
    "bowling_runs": ["bowling_runs", "bowling runs"],
    "bowling_wickets": ["bowling_wickets", "bowling wkts", "bowling wickets"],
    "bowling_economy": ["bowling_economy", "bowling economy"],
    "bowling_strike_rate": ["bowling_strike_rate", "bowling strike rate"],
    "bowling_avg": ["bowling_avg", "bowling avg"],
    "bowling_wides": ["bowling_wides", "bowling wides"],
    "bowling_no_ball": ["bowling_no_ball", "bowling no ball", "bowling no_ball"],
    "fielding_matches": ["fielding_matches", "fielding matches"],
    "fielding_catches": ["fielding_catches", "fielding catches"],
    "fielding_caught_behind": [
        "fielding_caught_behind",
        "fielding caught behind",
        "fielding caught_behind",
        "fielding_caught_bowled",
        "fielding caught bowled",
        "fielding caught_bowled",
    ],
    "fielding_run_out": ["fielding_run_out", "fielding run out", "fielding run_out"],
    "fielding_stumping": ["fielding_stumping", "fielding stumping"],
}

ROLE_ALIASES = {
    "batter": "Batter",
    "bat": "Batter",
    "bowler": "Bowler",
    "bowl": "Bowler",
    "allrounder": "Allrounder",
    "all_rounder": "Allrounder",
    "all-rounder": "Allrounder",
    "wicket_keeper": "Wicket Keeper",
    "wicketkeeper": "Wicket Keeper",
    "wk": "Wicket Keeper",
    "keeper": "Wicket Keeper",
}


def _to_int(value: str) -> int:
    if value is None:
        return 0
    token = value.strip().replace(",", "")
    if token == "":
        return 0
    if token.endswith("*"):
        token = token[:-1]
    match = re.search(r"-?\d+(\.\d+)?", token)
    if not match:
        raise ValueError(f"Cannot parse integer from '{value}'")
    return int(float(match.group(0)))


def _to_float(value: str) -> float:
    if value is None:
        return 0.0
    token = value.strip().replace(",", "")
    if token == "":
        return 0.0
    match = re.search(r"-?\d+(\.\d+)?", token)
    if not match:
        raise ValueError(f"Cannot parse float from '{value}'")
    return float(match.group(0))


def _to_bool(value: str) -> bool:
    if value is None:
        return False
    token = value.strip().lower()
    if token in {"1", "true", "yes", "y", "available"}:
        return True
    if token in {"0", "false", "no", "n", "unavailable"}:
        return False
    raise ValueError(f"Cannot parse boolean from '{value}'. Use true/false or yes/no.")


def _normalize_column(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def _resolve_columns(fieldnames: list[str]) -> dict[str, str]:
    normalized_to_original = {_normalize_column(col): col for col in fieldnames}
    resolved: dict[str, str] = {}
    missing: list[str] = []

    for canonical, aliases in CANONICAL_COLUMNS.items():
        actual = None
        for alias in aliases:
            normalized_alias = _normalize_column(alias)
            if normalized_alias in normalized_to_original:
                actual = normalized_to_original[normalized_alias]
                break
        if actual is None:
            missing.append(canonical)
        else:
            resolved[canonical] = actual

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    return resolved


def normalize_role(role: str) -> str:
    cleaned = role.strip()
    if cleaned == "":
        return ""
    key = cleaned.lower().replace(" ", "_")
    if key in ROLE_ALIASES:
        return ROLE_ALIASES[key]
    raise ValueError("Invalid role. Use: Batter, Bowler, Allrounder, Wicket Keeper")


def load_player_history(csv_path: str | Path) -> list[PlayerStats]:
    path = Path(csv_path)
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header")
        column_map = _resolve_columns(reader.fieldnames)

        records: list[PlayerStats] = []
        for row in reader:
            player_name = row[column_map["player_name"]].strip()
            records.append(
                PlayerStats(
                    player_name=player_name,
                    role=normalize_role(row[column_map["role"]]),
                    availability=_to_bool(row[column_map["availability"]]),
                    batting_matches=_to_int(row[column_map["batting_matches"]]),
                    batting_innings=_to_int(row[column_map["batting_innings"]]),
                    batting_runs=_to_int(row[column_map["batting_runs"]]),
                    batting_not_out=_to_int(row[column_map["batting_not_out"]]),
                    batting_high_score=_to_int(row[column_map["batting_high_score"]]),
                    batting_avg=_to_float(row[column_map["batting_avg"]]),
                    batting_strike_rate=_to_float(row[column_map["batting_strike_rate"]]),
                    bowling_matches=_to_int(row[column_map["bowling_matches"]]),
                    bowling_innings=_to_int(row[column_map["bowling_innings"]]),
                    bowling_overs=_to_float(row[column_map["bowling_overs"]]),
                    bowling_runs=_to_int(row[column_map["bowling_runs"]]),
                    bowling_wickets=_to_int(row[column_map["bowling_wickets"]]),
                    bowling_economy=_to_float(row[column_map["bowling_economy"]]),
                    bowling_strike_rate=_to_float(row[column_map["bowling_strike_rate"]]),
                    bowling_avg=_to_float(row[column_map["bowling_avg"]]),
                    bowling_wides=_to_int(row[column_map["bowling_wides"]]),
                    bowling_no_ball=_to_int(row[column_map["bowling_no_ball"]]),
                    fielding_matches=_to_int(row[column_map["fielding_matches"]]),
                    fielding_catches=_to_int(row[column_map["fielding_catches"]]),
                    fielding_caught_behind=_to_int(row[column_map["fielding_caught_behind"]]),
                    fielding_run_out=_to_int(row[column_map["fielding_run_out"]]),
                    fielding_stumping=_to_int(row[column_map["fielding_stumping"]]),
                )
            )

    return records
