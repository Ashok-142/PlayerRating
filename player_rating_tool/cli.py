from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .loader import load_player_history
from .rating import load_weights, rate_players
from .secrets import load_env_files
from .selector import select_team


ROLE_ORDER = ("Batter", "Bowler", "Allrounder", "Wicket Keeper")
load_env_files()


def run_rate(history_path: str, weights_path: str | None, output_path: str | None) -> int:
    records = load_player_history(history_path)
    weights = load_weights(weights_path)
    profiles = rate_players(records, weights)

    lines = [
        "player_name,role,rating,batting_score,bowling_score,fielding_score",
    ]
    for p in profiles:
        lines.append(
            f"{p.player_name},{p.role},{p.rating},{p.batting_score},{p.bowling_score},{p.fielding_score}"
        )

    payload = "\n".join(lines)
    if output_path:
        Path(output_path).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)

    return 0


def run_team(
    history_path: str,
    weights_path: str | None,
    output_path: str | None,
) -> int:
    records = load_player_history(history_path)
    weights = load_weights(weights_path)
    available_records = [r for r in records if r.availability]
    if not available_records:
        raise ValueError("No available players found in input CSV")

    profiles = rate_players(available_records, weights)
    structure_raw = weights.get("team_structure", {})
    if not isinstance(structure_raw, dict):
        raise ValueError("'team_structure' must be a JSON object in weights config")
    structure = {str(k): int(v) for k, v in structure_raw.items() if int(v) > 0}
    if not structure:
        raise ValueError("'team_structure' in weights config has no positive role counts")
    desired_filter_enabled = bool(int(weights.get("desired_rating_filter_enabled", 0)))

    stats_by_player = {s.player_name: s for s in available_records}
    selected, shortages, desired_thresholds = select_team(
        players=profiles,
        stats_by_player=stats_by_player,
        team_structure=structure,
        shrinkage_k=weights["selection_shrinkage_k"],
        emerging_max_innings=int(weights["emerging_max_innings"]),
        emerging_slots=int(weights["emerging_slots"]),
        desired_rating_filter_enabled=desired_filter_enabled,
    )

    if shortages:
        warning_parts = [f"{role}:{count}" for role, count in sorted(shortages.items())]
        print(
            "WARNING: Could not fully satisfy requested role counts. "
            f"Shortages -> {', '.join(warning_parts)}",
            file=sys.stderr,
        )

    lines: list[str] = []
    lines.append("desired_rating_thresholds")
    lines.append("role,desired_rating_threshold")
    threshold_order = ("Batter", "Wicket Keeper", "Allrounder", "Bowler")
    for role in threshold_order:
        if role in structure:
            threshold = desired_thresholds.get(role)
            threshold_text = "" if threshold is None else f"{threshold:.2f}"
            lines.append(f"{role},{threshold_text}")

    lines.append("")

    merged_role_order = ("Batter", "Wicket Keeper", "Allrounder", "Bowler")
    selected_by_role: dict[str, list] = {role: [] for role in merged_role_order}
    for e in selected:
        if e.profile.role in selected_by_role:
            selected_by_role[e.profile.role].append(e)

    lines.append("playing_xi")
    lines.append("role,player_name,selection_score,base_rating,sample_size,reason,batting_score,bowling_score,fielding_score")
    for role in merged_role_order:
        role_needed = structure.get(role, 0)
        if role_needed <= 0:
            continue

        role_rows = sorted(
            selected_by_role.get(role, []),
            key=lambda e: (e.profile.rating, e.selection_score),
            reverse=True,
        )[:role_needed]

        for e in role_rows:
            p = e.profile
            lines.append(
                f"{role},{p.player_name},{e.selection_score},{p.rating},{e.sample_size},{e.reason},{p.batting_score},{p.bowling_score},{p.fielding_score}"
            )

        blanks_needed = max(0, role_needed - len(role_rows))
        for _ in range(blanks_needed):
            lines.append(f"{role},,,,,blank_slot,,,")

    payload = "\n".join(lines)
    if output_path:
        Path(output_path).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cricket player rating tool")
    sub = parser.add_subparsers(dest="command", required=True)

    rate_cmd = sub.add_parser("rate", help="Rate players from CSV")
    rate_cmd.add_argument("--history", required=True, help="Path to player history CSV")
    rate_cmd.add_argument("--weights", required=False, help="Optional JSON weight config")
    rate_cmd.add_argument("--output", required=False, help="Optional output CSV path")

    team_cmd = sub.add_parser("team", help="Select playing XI from rated players and role structure")
    team_cmd.add_argument("--history", required=True, help="Path to player history CSV")
    team_cmd.add_argument("--weights", required=False, help="Optional JSON weight config")
    team_cmd.add_argument("--output", required=False, help="Optional output CSV path")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "rate":
        return run_rate(args.history, args.weights, args.output)
    if args.command == "team":
        return run_team(
            args.history,
            args.weights,
            args.output,
        )

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
