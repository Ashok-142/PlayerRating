from __future__ import annotations

from collections import Counter

from .models import PlayerProfile


def select_team(players: list[PlayerProfile], team_structure: dict[str, int]) -> tuple[list[PlayerProfile], dict[str, int]]:
    needed = Counter(team_structure)
    selected: list[PlayerProfile] = []
    shortages: dict[str, int] = {}

    for role in ("batter", "bowler", "allrounder"):
        role_needed = needed.get(role, 0)
        if role_needed <= 0:
            continue
        role_players = [p for p in players if p.role == role]
        if len(role_players) < role_needed:
            shortages[role] = role_needed - len(role_players)
        selected.extend(role_players[:role_needed])

    selected_ids = {p.player_id for p in selected}

    target_size = sum(team_structure.values())
    if len(selected) < target_size:
        remaining = [p for p in players if p.player_id not in selected_ids]
        selected.extend(remaining[: target_size - len(selected)])

    return sorted(selected, key=lambda p: p.rating, reverse=True), shortages
