from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from .models import PlayerSeasonStats


REQUIRED_COLUMNS = {
    "player_id",
    "player_name",
    "season",
    "matches",
    "runs",
    "batting_average",
    "strike_rate",
    "wickets",
    "bowling_average",
    "economy",
    "catches",
}


def _to_int(value: str) -> int:
    if value.strip() == "":
        return 0
    return int(float(value))


def _to_float(value: str) -> float:
    if value.strip() == "":
        return 0.0
    return float(value)


def load_player_history(csv_path: str | Path) -> list[PlayerSeasonStats]:
    path = Path(csv_path)
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header")

        missing = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

        records: list[PlayerSeasonStats] = []
        for row in reader:
            records.append(
                PlayerSeasonStats(
                    player_id=row["player_id"].strip(),
                    player_name=row["player_name"].strip(),
                    season=_to_int(row["season"]),
                    matches=_to_int(row["matches"]),
                    runs=_to_int(row["runs"]),
                    batting_average=_to_float(row["batting_average"]),
                    strike_rate=_to_float(row["strike_rate"]),
                    wickets=_to_int(row["wickets"]),
                    bowling_average=_to_float(row["bowling_average"]),
                    economy=_to_float(row["economy"]),
                    catches=_to_int(row["catches"]),
                )
            )

    return records


def group_by_player(records: Iterable[PlayerSeasonStats]) -> dict[str, list[PlayerSeasonStats]]:
    grouped: dict[str, list[PlayerSeasonStats]] = {}
    for record in records:
        grouped.setdefault(record.player_id, []).append(record)
    return grouped
