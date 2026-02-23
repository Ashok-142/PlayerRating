from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .loader import load_player_history
from .rating import load_weights, rate_players
from .selector import select_team


def _parse_team_structure(raw: str) -> dict[str, int]:
    data = json.loads(raw)
    allowed = {"batter", "bowler", "allrounder"}
    unknown = set(data) - allowed
    if unknown:
        raise ValueError(f"Unknown role keys in team structure: {sorted(unknown)}")
    return {k: int(v) for k, v in data.items() if int(v) > 0}


def run_rate(history_path: str, weights_path: str | None, output_path: str | None) -> int:
    records = load_player_history(history_path)
    weights = load_weights(weights_path)
    profiles = rate_players(records, weights)

    lines = [
        "player_id,player_name,role,rating,batting_score,bowling_score,fielding_score",
    ]
    for p in profiles:
        lines.append(
            f"{p.player_id},{p.player_name},{p.role},{p.rating},{p.batting_score},{p.bowling_score},{p.fielding_score}"
        )

    payload = "\n".join(lines)
    if output_path:
        Path(output_path).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)

    return 0


def run_team(history_path: str, team_structure_raw: str, weights_path: str | None, output_path: str | None) -> int:
    records = load_player_history(history_path)
    weights = load_weights(weights_path)
    profiles = rate_players(records, weights)
    structure = _parse_team_structure(team_structure_raw)
    chosen, shortages = select_team(profiles, structure)

    if shortages:
        warning_parts = [f"{role}:{count}" for role, count in sorted(shortages.items())]
        print(
            "WARNING: Could not fully satisfy requested role counts. "
            f"Shortages -> {', '.join(warning_parts)}",
            file=sys.stderr,
        )

    lines = ["player_id,player_name,role,rating"]
    for p in chosen:
        lines.append(f"{p.player_id},{p.player_name},{p.role},{p.rating}")

    payload = "\n".join(lines)
    if output_path:
        Path(output_path).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cricket player rating and team selection tool")
    sub = parser.add_subparsers(dest="command", required=True)

    rate_cmd = sub.add_parser("rate", help="Classify and rate players from history")
    rate_cmd.add_argument("--history", required=True, help="Path to player history CSV")
    rate_cmd.add_argument("--weights", required=False, help="Optional JSON weight config")
    rate_cmd.add_argument("--output", required=False, help="Optional output CSV path")

    team_cmd = sub.add_parser("team", help="Select team from rated players and structure")
    team_cmd.add_argument("--history", required=True, help="Path to player history CSV")
    team_cmd.add_argument(
        "--team-structure",
        required=True,
        help='JSON string like {"batter":4,"bowler":3,"allrounder":2}',
    )
    team_cmd.add_argument("--weights", required=False, help="Optional JSON weight config")
    team_cmd.add_argument("--output", required=False, help="Optional output CSV path")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "rate":
        return run_rate(args.history, args.weights, args.output)
    if args.command == "team":
        return run_team(args.history, args.team_structure, args.weights, args.output)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
