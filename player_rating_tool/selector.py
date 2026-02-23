from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .models import PlayerProfile, PlayerStats


@dataclass(frozen=True)
class SelectionEntry:
    profile: PlayerProfile
    selection_score: float
    sample_size: int
    reason: str


def _sample_size(stats: PlayerStats) -> int:
    if stats.role == "Batter":
        return stats.batting_innings
    if stats.role == "Bowler":
        return stats.bowling_innings
    if stats.role in {"Allrounder", "Wicket Keeper"}:
        return max(stats.batting_innings, stats.bowling_innings)
    return max(stats.batting_innings, stats.bowling_innings)


def _normalize_role_key(role: str) -> str:
    token = role.strip().lower().replace(" ", "_")
    mapping = {
        "batter": "Batter",
        "bowler": "Bowler",
        "allrounder": "Allrounder",
        "wicket_keeper": "Wicket Keeper",
        "wicketkeeper": "Wicket Keeper",
    }
    if token not in mapping:
        raise ValueError(f"Unknown role in team structure: {role}")
    return mapping[token]


def _compute_role_priors(
    players: list[PlayerProfile],
) -> tuple[dict[str, float], float]:
    role_sums: dict[str, float] = {}
    role_counts: dict[str, int] = {}
    for p in players:
        role_sums[p.role] = role_sums.get(p.role, 0.0) + p.rating
        role_counts[p.role] = role_counts.get(p.role, 0) + 1

    priors = {role: role_sums[role] / role_counts[role] for role in role_sums}
    global_prior = sum(p.rating for p in players) / max(len(players), 1)
    return priors, global_prior


def _desired_rating_thresholds(
    scored: list[SelectionEntry], needed: Counter[str]
) -> dict[str, float]:
    thresholds: dict[str, float] = {}
    for role, role_needed in needed.items():
        if role_needed <= 0:
            continue
        role_entries = [e for e in scored if e.profile.role == role]
        role_entries = sorted(role_entries, key=lambda e: e.profile.rating, reverse=True)
        if not role_entries:
            continue
        top_n = min(role_needed, len(role_entries))
        thresholds[role] = role_entries[top_n - 1].profile.rating
    return thresholds


def select_team(
    players: list[PlayerProfile],
    stats_by_player: dict[str, PlayerStats],
    team_structure: dict[str, int],
    shrinkage_k: float,
    emerging_max_innings: int,
    emerging_slots: int,
    desired_rating_filter_enabled: bool,
) -> tuple[list[SelectionEntry], dict[str, int], dict[str, float]]:
    needed = Counter({_normalize_role_key(k): int(v) for k, v in team_structure.items() if int(v) > 0})
    shortages: dict[str, int] = {}
    target_size = sum(needed.values())

    role_priors, global_prior = _compute_role_priors(players)
    scored: list[SelectionEntry] = []
    for p in players:
        stats = stats_by_player[p.player_name]
        n = _sample_size(stats)
        reliability = n / (n + max(shrinkage_k, 1.0))
        prior = role_priors.get(p.role, global_prior)
        selection_score = (reliability * p.rating) + ((1.0 - reliability) * prior)
        scored.append(
            SelectionEntry(
                profile=p,
                selection_score=round(selection_score, 2),
                sample_size=n,
                reason="default",
            )
        )

    desired_thresholds = _desired_rating_thresholds(scored, needed)

    selected: list[SelectionEntry] = []
    for role in ("Batter", "Bowler", "Allrounder", "Wicket Keeper"):
        role_needed = needed.get(role, 0)
        if role_needed <= 0:
            continue
        role_players = [e for e in scored if e.profile.role == role]
        if desired_rating_filter_enabled and role in desired_thresholds:
            threshold = desired_thresholds[role]
            role_players = [e for e in role_players if e.profile.rating >= threshold]
            role_players = [
                SelectionEntry(
                    profile=e.profile,
                    selection_score=e.selection_score,
                    sample_size=e.sample_size,
                    reason="desired_rating",
                )
                for e in role_players
            ]
        role_players = sorted(role_players, key=lambda e: (e.selection_score, e.profile.rating), reverse=True)
        if len(role_players) < role_needed:
            shortages[role] = role_needed - len(role_players)
        selected.extend(role_players[:role_needed])

    if desired_rating_filter_enabled:
        selected = sorted(selected, key=lambda e: (e.selection_score, e.profile.rating), reverse=True)
        return selected[:target_size], shortages, desired_thresholds

    selected_names = {e.profile.player_name for e in selected}
    if len(selected) < target_size:
        remaining = [e for e in scored if e.profile.player_name not in selected_names and e.profile.role != ""]
        remaining = sorted(remaining, key=lambda e: (e.selection_score, e.profile.rating), reverse=True)
        selected.extend(remaining[: target_size - len(selected)])
        selected_names = {e.profile.player_name for e in selected}

    # Reserve up to `emerging_slots` for low-sample players while preserving role quotas.
    if emerging_slots > 0 and selected:
        emerging_pool = [e for e in scored if e.sample_size < emerging_max_innings and e.profile.player_name not in selected_names]
        emerging_pool = sorted(emerging_pool, key=lambda e: e.profile.rating, reverse=True)

        for emerging in emerging_pool[:emerging_slots]:
            same_role_selected = [e for e in selected if e.profile.role == emerging.profile.role]
            if not same_role_selected:
                continue
            replace = min(same_role_selected, key=lambda e: e.selection_score)
            if emerging.profile.rating <= replace.profile.rating:
                continue
            selected.remove(replace)
            selected.append(
                SelectionEntry(
                    profile=emerging.profile,
                    selection_score=emerging.selection_score,
                    sample_size=emerging.sample_size,
                    reason="emerging_slot",
                )
            )
            selected_names = {e.profile.player_name for e in selected}

    selected = sorted(selected, key=lambda e: (e.selection_score, e.profile.rating), reverse=True)
    return selected[:target_size], shortages, desired_thresholds
