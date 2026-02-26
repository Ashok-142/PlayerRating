from __future__ import annotations

import json
import tempfile
from dataclasses import asdict
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

from player_rating_tool.db import (
    create_match_with_squads,
    get_ball_events,
    get_innings,
    get_match,
    get_match_batting_stats,
    get_match_bowling_stats,
    get_match_squads,
    get_or_create_innings,
    get_player_team_map,
    init_db,
    list_innings_for_match,
    list_matches,
    load_player_history_from_db,
    record_ball_event,
    undo_last_ball,
)
from player_rating_tool.loader import load_player_history
from player_rating_tool.rating import load_weights, rate_players
from player_rating_tool.secrets import load_env_files
from player_rating_tool.selector import select_team

CONFIG_PATH = Path("configs/default_weights.json")
DB_PATH = Path("data/player_rating.db")
ROLE_OPTIONS = ["Batter", "Bowler", "Allrounder", "Wicket Keeper"]
load_env_files()


def _inject_custom_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ui-bg: #f5f6fb;
            --ui-surface: #ffffff;
            --ui-border: #d8deeb;
            --ui-ink: #1b2435;
            --ui-muted: #5d6880;
            --ui-accent: #1f5fbf;
            --ui-accent-strong: #15458b;
            --ui-highlight: #e9f2ff;
            --ui-alert: #f9a826;
        }

        .stApp {
            background:
                radial-gradient(1300px 500px at -10% -10%, #dce8ff 0%, rgba(220, 232, 255, 0) 58%),
                radial-gradient(1200px 520px at 100% -15%, #ffe7c4 0%, rgba(255, 231, 196, 0) 62%),
                var(--ui-bg);
            color: var(--ui-ink);
            font-family: "Avenir Next", "Segoe UI", "Trebuchet MS", sans-serif;
        }

        h1, h2, h3 {
            font-family: "Avenir Next", "Segoe UI", sans-serif;
            letter-spacing: -0.01em;
            color: var(--ui-ink);
        }

        .hero-panel {
            border: 1px solid var(--ui-border);
            border-radius: 20px;
            padding: 1.1rem 1.2rem;
            background: linear-gradient(125deg, #ffffff 0%, #edf4ff 60%, #fff4e3 100%);
            margin-bottom: 1rem;
            box-shadow: 0 14px 26px rgba(24, 42, 74, 0.08);
        }

        .hero-title {
            font-family: "Avenir Next", "Segoe UI", sans-serif;
            font-size: 1.55rem;
            font-weight: 700;
            line-height: 1.2;
            color: var(--ui-ink);
            margin-bottom: 0.2rem;
        }

        .hero-subtitle {
            color: var(--ui-muted);
            font-size: 0.98rem;
            margin: 0;
        }

        .workflow-strip {
            display: grid;
            gap: 0.55rem;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            margin: 0.25rem 0 0.9rem;
        }

        .workflow-step {
            background: var(--ui-surface);
            border: 1px solid var(--ui-border);
            border-radius: 12px;
            padding: 0.55rem 0.68rem;
            font-size: 0.82rem;
            color: var(--ui-muted);
            line-height: 1.2;
        }

        .workflow-step strong {
            color: var(--ui-ink);
            display: block;
            margin-bottom: 0.15rem;
            font-family: "Avenir Next", "Segoe UI", sans-serif;
        }

        .tip-panel {
            border: 1px solid var(--ui-border);
            border-radius: 14px;
            background: #fff9ee;
            padding: 0.8rem 0.9rem;
            color: var(--ui-muted);
            font-size: 0.9rem;
            margin-top: 0.35rem;
        }

        [data-testid="stTabs"] {
            margin-top: 0.3rem;
        }

        [data-testid="stTabs"] button {
            border-radius: 10px 10px 0 0;
            height: 2.6rem;
            padding: 0 0.95rem;
            color: #495775;
            font-weight: 600;
        }

        [data-testid="stTabs"] button[aria-selected="true"] {
            color: var(--ui-accent-strong);
            background: var(--ui-highlight);
            border-bottom: 2px solid var(--ui-accent);
        }

        div.stButton > button,
        div.stDownloadButton > button {
            border: 1px solid transparent;
            border-radius: 12px;
            background: linear-gradient(130deg, var(--ui-accent) 0%, var(--ui-accent-strong) 100%);
            color: white;
            font-weight: 600;
            padding: 0.45rem 0.85rem;
            transition: all 0.15s ease-in-out;
        }

        div.stButton > button:hover,
        div.stDownloadButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 9px 15px rgba(28, 75, 149, 0.24);
        }

        [data-testid="stMetric"] {
            border: 1px solid var(--ui-border);
            border-radius: 14px;
            padding: 0.65rem 0.8rem;
            background: linear-gradient(180deg, #ffffff 0%, #f8faff 100%);
        }

        [data-testid="stMetricLabel"] {
            color: var(--ui-muted);
            font-weight: 600;
        }

        [data-testid="stMetricValue"] {
            font-family: "Avenir Next", "Segoe UI", sans-serif;
            color: var(--ui-ink);
            font-weight: 700;
            letter-spacing: -0.01em;
        }

        [data-testid="stExpander"] details {
            border: 1px solid var(--ui-border);
            border-radius: 14px;
            background: var(--ui-surface);
            box-shadow: 0 8px 16px rgba(24, 42, 74, 0.05);
        }

        [data-testid="stDataFrame"],
        [data-testid="stDataEditor"] {
            border: 1px solid var(--ui-border);
            border-radius: 14px;
            overflow: hidden;
        }

        [data-testid="stForm"] {
            border: 1px solid var(--ui-border);
            border-radius: 14px;
            background: var(--ui-surface);
            padding: 0.8rem 0.9rem;
        }

        .stTextInput label, .stNumberInput label, .stSelectbox label, .stRadio label {
            font-weight: 600;
            color: var(--ui-muted);
        }

        @media (max-width: 900px) {
            .workflow-strip {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_page_banner(total_players: int, total_matches: int, live_matches: int) -> None:
    st.markdown(
        """
        <div class="hero-panel">
          <div class="hero-title">Cricket Match Scoring and Selection Studio</div>
          <p class="hero-subtitle">
            Use one-click scoring actions, keep player history in one database, and run ratings plus playing XI from the same source.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Players in DB", total_players)
    c2.metric("Total Matches", total_matches)
    c3.metric("Live Matches", live_matches)


def _load_records_from_dataframe(raw_df: pd.DataFrame) -> list:
    raw_text = raw_df.to_csv(index=False)
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as tmp:
        tmp.write(raw_text)
        tmp_path = tmp.name
    try:
        records = load_player_history(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    return records


def _read_uploaded_csv(uploaded_file) -> pd.DataFrame:
    return pd.read_csv(BytesIO(uploaded_file.getvalue()))


def _rate_table(records, weights) -> pd.DataFrame:
    profiles = rate_players(records, weights)
    rows = [
        {
            "player_name": p.player_name,
            "role": p.role,
            "rating": p.rating,
            "batting_score": p.batting_score,
            "bowling_score": p.bowling_score,
            "fielding_score": p.fielding_score,
        }
        for p in profiles
    ]
    return pd.DataFrame(rows)


def _team_tables(records, weights) -> tuple[pd.DataFrame, pd.DataFrame]:
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
    selected, _, desired_thresholds = select_team(
        players=profiles,
        stats_by_player=stats_by_player,
        team_structure=structure,
        shrinkage_k=weights["selection_shrinkage_k"],
        emerging_max_innings=int(weights["emerging_max_innings"]),
        emerging_slots=int(weights["emerging_slots"]),
        desired_rating_filter_enabled=desired_filter_enabled,
    )

    threshold_rows = []
    for role in ("Batter", "Wicket Keeper", "Allrounder", "Bowler"):
        if role in structure:
            threshold_rows.append(
                {
                    "role": role,
                    "desired_rating_threshold": desired_thresholds.get(role),
                }
            )
    thresholds_df = pd.DataFrame(threshold_rows)

    selected_by_role: dict[str, list] = {
        "Batter": [],
        "Wicket Keeper": [],
        "Allrounder": [],
        "Bowler": [],
    }
    for entry in selected:
        if entry.profile.role in selected_by_role:
            selected_by_role[entry.profile.role].append(entry)

    team_rows = []
    for role in ("Batter", "Wicket Keeper", "Allrounder", "Bowler"):
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
            team_rows.append(
                {
                    "role": role,
                    "player_name": p.player_name,
                    "selection_score": e.selection_score,
                    "base_rating": p.rating,
                    "sample_size": e.sample_size,
                    "reason": e.reason,
                    "batting_score": p.batting_score,
                    "bowling_score": p.bowling_score,
                    "fielding_score": p.fielding_score,
                }
            )

        blanks_needed = max(0, role_needed - len(role_rows))
        for _ in range(blanks_needed):
            team_rows.append(
                {
                    "role": role,
                    "player_name": "",
                    "selection_score": "",
                    "base_rating": "",
                    "sample_size": "",
                    "reason": "blank_slot",
                    "batting_score": "",
                    "bowling_score": "",
                    "fielding_score": "",
                }
            )

    return thresholds_df, pd.DataFrame(team_rows)


def _to_csv_download(df: pd.DataFrame) -> str:
    return df.to_csv(index=False)


def _records_to_dataframe(records: list) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(
            columns=[
                "player_name",
                "role",
                "availability",
                "batting_matches",
                "batting_innings",
                "batting_runs",
                "batting_not_out",
                "batting_high_score",
                "batting_avg",
                "batting_strike_rate",
                "bowling_matches",
                "bowling_innings",
                "bowling_overs",
                "bowling_runs",
                "bowling_wickets",
                "bowling_economy",
                "bowling_strike_rate",
                "bowling_avg",
                "bowling_wides",
                "bowling_no_ball",
                "fielding_matches",
                "fielding_catches",
                "fielding_caught_behind",
                "fielding_run_out",
                "fielding_stumping",
            ]
        )
    return pd.DataFrame([asdict(r) for r in records])


def _prepend_team_name_column(raw_df: pd.DataFrame, team_map: dict[str, str]) -> pd.DataFrame:
    if raw_df.empty:
        out = raw_df.copy()
        out.insert(0, "team_name", "")
        return out

    out = raw_df.copy()
    out["team_name"] = out["player_name"].astype(str).map(team_map).fillna("")
    columns = ["team_name"] + [c for c in out.columns if c != "team_name"]
    return out[columns]


def _default_squad_df() -> pd.DataFrame:
    return pd.DataFrame([{"player_name": "", "role": "Batter"} for _ in range(11)])


def _parse_squad_df(squad_df: pd.DataFrame) -> list[dict[str, str]]:
    squad: list[dict[str, str]] = []
    for row in squad_df.to_dict(orient="records"):
        name = str(row.get("player_name", "")).strip()
        role = str(row.get("role", "")).strip() or "Batter"
        if not name:
            continue
        squad.append({"player_name": name, "role": role})
    return squad


def _overs_display(legal_balls: int) -> str:
    completed_overs = legal_balls // 6
    balls = legal_balls % 6
    return f"{completed_overs}.{balls}"


def _format_match_label(match_row: dict[str, object]) -> str:
    return (
        f"#{match_row['id']} "
        f"{match_row['home_team_name']} vs {match_row['away_team_name']} "
        f"({match_row['status']}, {match_row['total_overs']} ov)"
    )


def _player_option(player_row: dict[str, object]) -> str:
    return f"{player_row['player_name']} ({player_row['role']})"


def _auto_batting_team_name(match: dict[str, object], innings_no: int) -> str | None:
    toss_winner = str(match.get("toss_winner_team_name") or "").strip()
    toss_decision = str(match.get("toss_decision") or "").strip().lower()
    home_team = str(match.get("home_team_name") or "").strip()
    away_team = str(match.get("away_team_name") or "").strip()

    if toss_winner not in {home_team, away_team}:
        return None
    if toss_decision not in {"bat", "bowl"}:
        return None

    if toss_decision == "bat":
        first_batting = toss_winner
    else:
        first_batting = away_team if toss_winner == home_team else home_team
    second_batting = away_team if first_batting == home_team else home_team
    return first_batting if int(innings_no) == 1 else second_batting


def _player_index(players: list[dict[str, object]], player_id: int) -> int:
    for idx, row in enumerate(players):
        if int(row["player_id"]) == int(player_id):
            return idx
    return 0


def _live_state_key(innings_id: int) -> str:
    return f"live_state_{innings_id}"


def _ensure_live_state(
    innings_id: int,
    batting_players: list[dict[str, object]],
    bowling_players: list[dict[str, object]],
) -> dict[str, object]:
    key = _live_state_key(innings_id)
    state = st.session_state.get(key)
    if not isinstance(state, dict):
        state = {}

    batting_ids = [int(p["player_id"]) for p in batting_players]
    bowling_ids = [int(p["player_id"]) for p in bowling_players]

    if not batting_ids:
        return {}
    if not bowling_ids:
        return {}

    striker_id = int(state.get("striker_id", batting_ids[0]))
    if striker_id not in batting_ids:
        striker_id = batting_ids[0]

    default_non_striker = batting_ids[1] if len(batting_ids) > 1 else batting_ids[0]
    non_striker_id = int(state.get("non_striker_id", default_non_striker))
    if non_striker_id not in batting_ids or non_striker_id == striker_id:
        non_striker_id = default_non_striker if default_non_striker != striker_id else batting_ids[0]

    bowler_id = int(state.get("bowler_id", bowling_ids[0]))
    if bowler_id not in bowling_ids:
        bowler_id = bowling_ids[0]

    merged_state = {
        "striker_id": striker_id,
        "non_striker_id": non_striker_id,
        "bowler_id": bowler_id,
        "needs_new_batter": bool(state.get("needs_new_batter", False)),
        "last_out_player_id": state.get("last_out_player_id"),
    }
    st.session_state[key] = merged_state
    return merged_state


def _rotate_strike_if_needed(
    state: dict[str, object],
    runs_off_bat: int,
    extras: int,
    legal_ball_before: int,
    legal_ball_after: int,
) -> None:
    if (int(runs_off_bat) + int(extras)) % 2 == 1:
        state["striker_id"], state["non_striker_id"] = state["non_striker_id"], state["striker_id"]
    over_completed = legal_ball_after > legal_ball_before and legal_ball_after % 6 == 0
    if over_completed:
        state["striker_id"], state["non_striker_id"] = state["non_striker_id"], state["striker_id"]


def _record_from_console(
    match_id: int,
    innings_id: int,
    state: dict[str, object],
    runs_off_bat: int = 0,
    extras: int = 0,
    extra_type: str = "none",
    is_wicket: bool = False,
    dismissal_type: str | None = None,
    dismissed_player_id: int | None = None,
    notes: str | None = None,
) -> None:
    before = get_innings(innings_id, DB_PATH)
    if before is None:
        raise ValueError("Innings not found")

    striker_id = int(state["striker_id"])
    non_striker_id = int(state["non_striker_id"])
    bowler_id = int(state["bowler_id"])
    record_ball_event(
        match_id=match_id,
        innings_id=innings_id,
        striker_id=striker_id,
        non_striker_id=non_striker_id,
        bowler_id=bowler_id,
        runs_off_bat=int(runs_off_bat),
        extras=int(extras),
        extra_type=extra_type,
        is_wicket=bool(is_wicket),
        dismissal_type=dismissal_type,
        dismissed_player_id=int(dismissed_player_id) if dismissed_player_id is not None else None,
        notes=notes,
        db_path=DB_PATH,
    )
    after = get_innings(innings_id, DB_PATH)
    if after is None:
        return

    if is_wicket:
        state["needs_new_batter"] = True
        state["last_out_player_id"] = int(dismissed_player_id) if dismissed_player_id is not None else striker_id
        return

    _rotate_strike_if_needed(
        state=state,
        runs_off_bat=int(runs_off_bat),
        extras=int(extras),
        legal_ball_before=int(before["legal_balls"]),
        legal_ball_after=int(after["legal_balls"]),
    )
    state["needs_new_batter"] = False
    state["last_out_player_id"] = None


def _render_scoring_tab() -> None:
    st.subheader("Scoring Console")
    st.caption("Quick scoring mode: choose players once, then update most balls in one click.")
    setup_tab, live_tab, report_tab = st.tabs(["Match Setup", "Live Console", "Reports"])

    with setup_tab:
        c1, c2, c3 = st.columns(3)
        home_team = c1.text_input("Home Team", key="score_home_team")
        away_team = c2.text_input("Away Team", key="score_away_team")
        total_overs = int(
            c3.number_input(
                "Total Overs",
                min_value=1,
                max_value=100,
                value=20,
                step=1,
                key="score_total_overs",
            )
        )

        toss_winner_name: str | None = None
        toss_decision: str | None = None
        home_clean = home_team.strip()
        away_clean = away_team.strip()
        if home_clean and away_clean and home_clean.lower() != away_clean.lower():
            t1, t2 = st.columns(2)
            toss_winner_name = t1.radio(
                "Toss Winner",
                options=[home_clean, away_clean],
                horizontal=True,
                key="score_toss_winner",
            )
            toss_decision_label = t2.radio(
                "Toss Decision",
                options=["Bat First", "Bowl First"],
                horizontal=True,
                key="score_toss_decision",
            )
            toss_decision = "bat" if toss_decision_label == "Bat First" else "bowl"
        else:
            st.caption("Enter distinct Home and Away team names to set toss details.")

        if "score_home_squad_seed" not in st.session_state:
            st.session_state.score_home_squad_seed = _default_squad_df()
        if "score_away_squad_seed" not in st.session_state:
            st.session_state.score_away_squad_seed = _default_squad_df()

        col_home, col_away = st.columns(2, gap="large")
        with col_home:
            st.caption("Home Squad")
            home_squad_df = st.data_editor(
                st.session_state.score_home_squad_seed,
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                key="score_home_squad_editor",
                column_config={
                    "player_name": st.column_config.TextColumn("Player Name", width="large"),
                    "role": st.column_config.SelectboxColumn("Role", options=ROLE_OPTIONS, width="medium"),
                },
            )
        with col_away:
            st.caption("Away Squad")
            away_squad_df = st.data_editor(
                st.session_state.score_away_squad_seed,
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                key="score_away_squad_editor",
                column_config={
                    "player_name": st.column_config.TextColumn("Player Name", width="large"),
                    "role": st.column_config.SelectboxColumn("Role", options=ROLE_OPTIONS, width="medium"),
                },
            )

        st.session_state.score_home_squad_seed = home_squad_df
        st.session_state.score_away_squad_seed = away_squad_df

        if st.button("Create Match", use_container_width=True, key="score_create_match"):
            try:
                home_squad = _parse_squad_df(home_squad_df)
                away_squad = _parse_squad_df(away_squad_df)
                match_id = create_match_with_squads(
                    home_team=home_team,
                    away_team=away_team,
                    total_overs=total_overs,
                    home_squad=home_squad,
                    away_squad=away_squad,
                    toss_winner=toss_winner_name,
                    toss_decision=toss_decision,
                    db_path=DB_PATH,
                )
                st.session_state.active_match_id = match_id
                st.session_state.score_home_squad_seed = _default_squad_df()
                st.session_state.score_away_squad_seed = _default_squad_df()
                st.success(f"Match #{match_id} created.")
                st.rerun()
            except Exception as exc:
                st.error(f"Failed to create match: {exc}")

    matches = list_matches(DB_PATH)
    if not matches:
        with live_tab:
            st.info("Create a match in Match Setup to start live scoring.")
        with report_tab:
            st.info("Reports appear after at least one match is created.")
        return

    match_ids = [int(m["id"]) for m in matches]
    active_match_id = st.session_state.get("active_match_id")
    if active_match_id in match_ids:
        live_match_id = int(active_match_id)
    else:
        preferred_live = next((m for m in matches if str(m["status"]).lower() == "live"), None)
        preferred_scheduled = next((m for m in matches if str(m["status"]).lower() == "scheduled"), None)
        preferred_match = preferred_live or preferred_scheduled or matches[0]
        live_match_id = int(preferred_match["id"])
    st.session_state.active_match_id = live_match_id
    default_index = match_ids.index(live_match_id) if live_match_id in match_ids else 0

    with live_tab:
        match_id = int(live_match_id)

        match = get_match(match_id, DB_PATH)
        if match is None:
            st.error("Could not load selected match.")
            return

        st.caption(
            f"Match #{match_id} | {match['home_team_name']} vs {match['away_team_name']}"
        )

        squads = get_match_squads(match_id, DB_PATH)
        home_team_name = str(match["home_team_name"])
        away_team_name = str(match["away_team_name"])
        home_team_id = int(match["home_team_id"])
        away_team_id = int(match["away_team_id"])

        innings_rows = list_innings_for_match(match_id, DB_PATH)
        innings_by_no = {int(r["innings_no"]): r for r in innings_rows}
        first_innings = innings_by_no.get(1)
        second_innings = innings_by_no.get(2)
        if first_innings is None or str(first_innings.get("status", "")) != "completed":
            innings_no = 1
        else:
            innings_no = 2

        auto_batting = _auto_batting_team_name(match, innings_no)
        if auto_batting is not None:
            toss_winner = str(match.get("toss_winner_team_name") or "")
            toss_decision = str(match.get("toss_decision") or "")
            decision_text = "bat first" if toss_decision == "bat" else "bowl first"
            st.caption(
                f"Auto setup from toss: {toss_winner} won toss and chose to {decision_text}."
            )
            batting_team_name = auto_batting
        else:
            existing_innings = first_innings if innings_no == 1 else second_innings
            if existing_innings is not None:
                batting_team_name = str(existing_innings["batting_team_name"])
            else:
                batting_team_name = home_team_name if innings_no == 1 else away_team_name
            st.caption("Toss details missing. Auto fallback applied for batting order.")

        bowling_team_name = away_team_name if batting_team_name == home_team_name else home_team_name
        b1, b2, b3, b4 = st.columns(4)
        b1.caption(f"Innings: {innings_no}")
        b2.caption(f"Batting: {batting_team_name}")
        b3.caption(f"Bowling: {bowling_team_name}")
        if innings_no == 1 and first_innings is not None and str(first_innings["status"]) == "completed":
            b4.caption("Next: 2nd innings")
        elif innings_no == 2 and second_innings is not None and str(second_innings["status"]) == "completed":
            b4.caption("Match: Completed")
        else:
            b4.caption("Mode: Live")

        try:
            batting_team_id = home_team_id if batting_team_name == home_team_name else away_team_id
            bowling_team_id = away_team_id if batting_team_id == home_team_id else home_team_id
            active_innings_id = get_or_create_innings(
                match_id=match_id,
                innings_no=innings_no,
                batting_team_id=batting_team_id,
                bowling_team_id=bowling_team_id,
                db_path=DB_PATH,
            )
            st.session_state.active_innings_id = active_innings_id
        except Exception as exc:
            st.error(f"Could not initialize innings automatically: {exc}")
            return

        innings = get_innings(active_innings_id, DB_PATH)
        if not innings or int(innings["match_id"]) != match_id:
            st.info("Could not load innings.")
            return

        team_players: dict[int, list[dict[str, object]]] = {}
        for players in squads.values():
            for p in players:
                team_players.setdefault(int(p["team_id"]), []).append(p)

        batting_players = sorted(
            team_players.get(int(innings["batting_team_id"]), []),
            key=lambda r: str(r["player_name"]).lower(),
        )
        bowling_players = sorted(
            team_players.get(int(innings["bowling_team_id"]), []),
            key=lambda r: str(r["player_name"]).lower(),
        )

        if len(batting_players) < 2:
            st.error("Batting side must have at least 2 players.")
            return
        if not bowling_players:
            st.error("Bowling side must have at least 1 player.")
            return

        state = _ensure_live_state(int(active_innings_id), batting_players, bowling_players)
        if not state:
            st.error("Could not initialize live state.")
            return

        total_overs = int(match["total_overs"])
        legal_balls = int(innings["legal_balls"])
        total_runs = int(innings["total_runs"])
        wickets = int(innings["wickets"])
        over_text = _overs_display(legal_balls)
        run_rate = (total_runs / (legal_balls / 6.0)) if legal_balls > 0 else 0.0

        m1, m2, m3 = st.columns(3)
        m1.metric("Score", f"{total_runs}/{wickets}")
        m2.metric("Overs", f"{over_text} / {total_overs}")
        m3.metric("Run Rate", f"{run_rate:.2f}")
        st.caption(f"Status: {innings['status']}")

        def submit_action(**kwargs: object) -> None:
            if state["striker_id"] == state["non_striker_id"]:
                st.error("Select different striker and non-striker.")
                return
            try:
                _record_from_console(
                    match_id=match_id,
                    innings_id=int(active_innings_id),
                    state=state,
                    **kwargs,
                )
                st.rerun()
            except Exception as exc:
                st.error(f"Scoring failed: {exc}")

        st.caption("Active Players")
        p1, p2, p3, p4 = st.columns([2.2, 2.2, 2.2, 1.0], gap="small")
        striker_row = p1.selectbox(
            "Striker",
            options=batting_players,
            format_func=_player_option,
            index=_player_index(batting_players, int(state["striker_id"])),
        )
        non_striker_row = p2.selectbox(
            "Non-Striker",
            options=batting_players,
            format_func=_player_option,
            index=_player_index(batting_players, int(state["non_striker_id"])),
        )
        bowler_row = p3.selectbox(
            "Bowler",
            options=bowling_players,
            format_func=_player_option,
            index=_player_index(bowling_players, int(state["bowler_id"])),
        )
        state["striker_id"] = int(striker_row["player_id"])
        state["non_striker_id"] = int(non_striker_row["player_id"])
        state["bowler_id"] = int(bowler_row["player_id"])

        if p4.button("Swap", use_container_width=True, key=f"live_swap_{active_innings_id}"):
            state["striker_id"], state["non_striker_id"] = state["non_striker_id"], state["striker_id"]
            st.rerun()

        if state["striker_id"] == state["non_striker_id"]:
            st.warning("Striker and non-striker must be different.")
        if state.get("needs_new_batter", False):
            st.warning("Wicket logged. Select new batter (striker/non-striker) and continue.")
            last_out_player_id = state.get("last_out_player_id")
            if last_out_player_id not in {state["striker_id"], state["non_striker_id"]}:
                state["needs_new_batter"] = False
                state["last_out_player_id"] = None

        st.caption("Quick Score")
        run_actions = [("0", 0), ("1", 1), ("2", 2), ("3", 3), ("4", 4), ("6", 6), ("W", None)]
        run_cols = st.columns(len(run_actions))
        for col, (label, runs) in zip(run_cols, run_actions):
            if col.button(label, key=f"quick_run_{active_innings_id}_{label}", use_container_width=True):
                if label == "W":
                    submit_action(
                        runs_off_bat=0,
                        extras=0,
                        extra_type="none",
                        is_wicket=True,
                        dismissal_type="bowled",
                        dismissed_player_id=int(state["striker_id"]),
                    )
                else:
                    submit_action(runs_off_bat=int(runs), extras=0, extra_type="none")

        extra_cols = st.columns(5)
        if extra_cols[0].button("Wide", key=f"quick_wd_{active_innings_id}", use_container_width=True):
            submit_action(runs_off_bat=0, extras=1, extra_type="wide")
        if extra_cols[1].button("No Ball", key=f"quick_nb_{active_innings_id}", use_container_width=True):
            submit_action(runs_off_bat=0, extras=1, extra_type="no_ball")
        if extra_cols[2].button("Bye 1", key=f"quick_b1_{active_innings_id}", use_container_width=True):
            submit_action(runs_off_bat=0, extras=1, extra_type="bye")
        if extra_cols[3].button("LegBye 1", key=f"quick_lb1_{active_innings_id}", use_container_width=True):
            submit_action(runs_off_bat=0, extras=1, extra_type="leg_bye")
        if extra_cols[4].button("Undo", key=f"quick_undo_{active_innings_id}", use_container_width=True):
            try:
                did_undo = undo_last_ball(int(active_innings_id), DB_PATH)
                if did_undo:
                    st.rerun()
                st.warning("No ball available to undo.")
            except Exception as exc:
                st.error(f"Undo failed: {exc}")

        st.caption("Ball-by-Ball History")
        history_rows = get_ball_events(int(active_innings_id), limit=120, db_path=DB_PATH)
        if history_rows:
            history_df = pd.DataFrame(history_rows)
            history_df["ball"] = history_df.apply(
                lambda r: f"{int(r['over_no'])}.{int(r['ball_in_over'])}",
                axis=1,
            )
            history_df["event"] = history_df.apply(
                lambda r: (
                    "Wicket"
                    if int(r["is_wicket"]) == 1
                    else f"{int(r['runs_off_bat']) + int(r['extras'])} runs"
                ),
                axis=1,
            )
            st.dataframe(
                history_df[
                    [
                        "event_seq",
                        "ball",
                        "event",
                        "striker_name",
                        "bowler_name",
                        "extra_type",
                        "dismissal_type",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
                height=320,
            )
        else:
            st.info("No balls recorded yet.")

    with report_tab:
        report_match = st.selectbox(
            "Match for Reports",
            options=matches,
            format_func=_format_match_label,
            index=default_index,
            key="report_selected_match",
        )
        report_match_id = int(report_match["id"])

        innings_rows = list_innings_for_match(report_match_id, DB_PATH)
        if innings_rows:
            innings_df = pd.DataFrame(innings_rows)
            innings_df["overs"] = innings_df["legal_balls"].apply(_overs_display)
            st.caption("Innings Summary")
            st.dataframe(
                innings_df[
                    [
                        "innings_no",
                        "batting_team_name",
                        "bowling_team_name",
                        "total_runs",
                        "wickets",
                        "overs",
                        "status",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

        if innings_rows:
            innings_map = {int(r["id"]): f"Innings {r['innings_no']} - {r['batting_team_name']}" for r in innings_rows}
            selected_innings_id = st.selectbox(
                "Ball Log Innings",
                options=list(innings_map.keys()),
                format_func=lambda x: innings_map[x],
                key=f"report_innings_{report_match_id}",
            )
            recent_events = get_ball_events(int(selected_innings_id), limit=120, db_path=DB_PATH)
            if recent_events:
                events_df = pd.DataFrame(recent_events)
                events_df["ball"] = events_df.apply(
                    lambda r: f"{int(r['over_no'])}.{int(r['ball_in_over'])}",
                    axis=1,
                )
                st.caption("Ball Events")
                st.dataframe(
                    events_df[
                        [
                            "event_seq",
                            "ball",
                            "striker_name",
                            "non_striker_name",
                            "bowler_name",
                            "runs_off_bat",
                            "extras",
                            "extra_type",
                            "is_wicket",
                            "dismissal_type",
                            "dismissed_player_name",
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No ball events yet.")

        batting_stats = get_match_batting_stats(report_match_id, DB_PATH)
        bowling_stats = get_match_bowling_stats(report_match_id, DB_PATH)

        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.caption("Batting Stats")
            if batting_stats:
                st.dataframe(pd.DataFrame(batting_stats), use_container_width=True, hide_index=True)
            else:
                st.info("No batting stats yet.")
        with c2:
            st.caption("Bowling Stats")
            if bowling_stats:
                st.dataframe(pd.DataFrame(bowling_stats), use_container_width=True, hide_index=True)
            else:
                st.info("No bowling stats yet.")


def _load_default_config() -> dict[str, object]:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return load_weights(None)


def _save_default_config(config: dict[str, object]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")


def _team_structure_editor(current_config: dict[str, object], key_prefix: str) -> dict[str, int]:
    st.subheader("Team Structure")
    st.caption("Set how many players to pick for each role in the Playing XI.")
    team_structure = current_config.get("team_structure", {})
    if not isinstance(team_structure, dict):
        team_structure = {}
    c1, c2, c3, c4 = st.columns(4)
    return {
        "Batter": int(
            c1.number_input(
                "Batters",
                min_value=0,
                value=int(team_structure.get("Batter", 4)),
                step=1,
                key=f"{key_prefix}_team_Batter",
                help="Number of specialist batters to include in the XI.",
            )
        ),
        "Bowler": int(
            c2.number_input(
                "Bowlers",
                min_value=0,
                value=int(team_structure.get("Bowler", 3)),
                step=1,
                key=f"{key_prefix}_team_Bowler",
                help="Number of specialist bowlers to include in the XI.",
            )
        ),
        "Allrounder": int(
            c3.number_input(
                "Allrounders",
                min_value=0,
                value=int(team_structure.get("Allrounder", 3)),
                step=1,
                key=f"{key_prefix}_team_Allrounder",
                help="Number of allrounders to include in the XI.",
            )
        ),
        "Wicket Keeper": int(
            c4.number_input(
                "Wicket Keepers",
                min_value=0,
                value=int(team_structure.get("Wicket Keeper", 1)),
                step=1,
                key=f"{key_prefix}_team_Wicket Keeper",
                help="Number of wicket keepers to include in the XI.",
            )
        ),
    }


def _config_editor(current_config: dict[str, object]) -> dict[str, object]:
    edited = dict(current_config)
    st.subheader("Weights")
    st.caption(
        "Weights define how batting, bowling, and fielding contribute to each role rating. "
        "Higher weight means higher impact on final role rating."
    )
    roles = [
        ("batter", "Batter"),
        ("bowler", "Bowler"),
        ("allrounder", "Allrounder"),
        ("wicket_keeper", "Wicket Keeper"),
    ]
    score_types = [("batting", "Batting"), ("bowling", "Bowling"), ("fielding", "Fielding")]

    for role_key, role_label in roles:
        st.markdown(f"**{role_label} Weights**")
        c1, c2, c3 = st.columns(3)
        for idx, (score_key, score_label) in enumerate(score_types):
            key = f"{role_key}_{score_key}_weight"
            value = float(edited.get(key, 0.0))
            if idx == 0:
                edited[key] = c1.number_input(
                    f"{score_label}",
                    min_value=0.0,
                    max_value=1.0,
                    value=value,
                    step=0.01,
                    key=f"cfg_{key}",
                    help=f"Contribution of {score_label.lower()} score to {role_label.lower()} rating.",
                )
            elif idx == 1:
                edited[key] = c2.number_input(
                    f"{score_label}",
                    min_value=0.0,
                    max_value=1.0,
                    value=value,
                    step=0.01,
                    key=f"cfg_{key}",
                    help=f"Contribution of {score_label.lower()} score to {role_label.lower()} rating.",
                )
            else:
                edited[key] = c3.number_input(
                    f"{score_label}",
                    min_value=0.0,
                    max_value=1.0,
                    value=value,
                    step=0.01,
                    key=f"cfg_{key}",
                    help=f"Contribution of {score_label.lower()} score to {role_label.lower()} rating.",
                )

    st.subheader("Selection Settings")
    st.caption("These settings control how team selection balances rating quality and player sample size.")
    c1, c2, c3 = st.columns(3)
    edited["selection_shrinkage_k"] = c1.number_input(
        "Selection shrinkage k",
        min_value=1.0,
        value=float(edited.get("selection_shrinkage_k", 20.0)),
        step=1.0,
        key="cfg_selection_shrinkage_k",
        help=(
            "Reliability smoothing factor. Higher values penalize low-sample players more and pull "
            "selection scores closer to role average."
        ),
    )
    edited["emerging_max_innings"] = int(
        c2.number_input(
            "Emerging max innings",
            min_value=0,
            value=int(float(edited.get("emerging_max_innings", 12))),
            step=1,
            key="cfg_emerging_max_innings",
            help="Players below this innings threshold are treated as emerging candidates.",
        )
    )
    edited["emerging_slots"] = int(
        c3.number_input(
            "Emerging slots",
            min_value=0,
            value=int(float(edited.get("emerging_slots", 1))),
            step=1,
            key="cfg_emerging_slots",
            help="Maximum number of emerging players that can replace regular picks.",
        )
    )
    edited["desired_rating_filter_enabled"] = 1 if st.checkbox(
        "Enable desired rating filter",
        value=bool(int(edited.get("desired_rating_filter_enabled", 0))),
        key="cfg_desired_rating_filter_enabled",
        help=(
            "If enabled, only players meeting role-wise desired rating thresholds are eligible. "
            "Can create blank slots when not enough players qualify."
        ),
    ) else 0

    return edited


def main() -> None:
    st.set_page_config(
        page_title="Cricket Scoring Studio",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    _inject_custom_styles()

    try:
        init_db(DB_PATH)
    except Exception as exc:
        st.error(f"Failed to initialize database: {exc}")
        return

    if "active_config" not in st.session_state:
        try:
            st.session_state.active_config = _load_default_config()
        except Exception as exc:
            st.error(f"Failed to load default config: {exc}")
            return

    raw_df: pd.DataFrame = pd.DataFrame()
    records = []
    try:
        records = load_player_history_from_db(DB_PATH)
        team_map = get_player_team_map(DB_PATH)
        raw_df = _prepend_team_name_column(_records_to_dataframe(records), team_map)
        if not records:
            st.info("No player history in DB yet. Use Scoring tab to add matches.")
    except Exception as exc:
        st.error(f"Failed to load player data from DB: {exc}")

    matches = list_matches(DB_PATH)
    live_matches = sum(1 for m in matches if str(m["status"]).lower() == "live")
    _render_page_banner(total_players=len(records), total_matches=len(matches), live_matches=live_matches)

    weights = st.session_state.active_config

    tab_scoring, tab_team, tab_rate, tab_raw, tab_config = st.tabs(
        ["Scoring Console", "Playing XI", "Player Ratings", "DB History", "Config"]
    )

    with tab_scoring:
        _render_scoring_tab()

    with tab_rate:
        st.caption("Player ratings are computed from batting, bowling, and fielding aggregates stored in the DB.")
        if not records:
            st.info("No player data available for rating.")
        else:
            try:
                rate_df = _rate_table(records, weights)
                st.dataframe(rate_df, use_container_width=True)
                st.download_button(
                    label="Download Rate CSV",
                    data=_to_csv_download(rate_df),
                    file_name="rate_output.csv",
                    mime="text/csv",
                )
            except Exception as exc:
                st.error(f"Failed to compute ratings: {exc}")

    with tab_team:
        st.caption("Playing XI recommendation based on role structure and reliability-adjusted player scores.")
        with st.expander("Playing XI Structure Controls", expanded=False):
            main_team_structure = _team_structure_editor(st.session_state.active_config, key_prefix="main")
            c1, c2 = st.columns(2)
            if c1.button("Apply Team Structure", use_container_width=True):
                config = dict(st.session_state.active_config)
                config["team_structure"] = main_team_structure
                st.session_state.active_config = config
                st.success("Team structure applied for this session.")
                st.rerun()
            if c2.button("Save Team Structure as Default", use_container_width=True):
                try:
                    config = dict(st.session_state.active_config)
                    config["team_structure"] = main_team_structure
                    _save_default_config(config)
                    st.session_state.active_config = config
                    st.success("Team structure saved to configs/default_weights.json.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Failed to save team structure: {exc}")

        if not records:
            st.info("No player data available for team selection.")
        else:
            try:
                thresholds_df, team_df = _team_tables(records, weights)
                st.subheader("Desired Rating Thresholds")
                col_thresholds, _ = st.columns([1, 3])
                with col_thresholds:
                    st.dataframe(
                        thresholds_df,
                        use_container_width=True,
                        hide_index=True,
                        height=180,
                    )
                st.subheader("Playing XI")
                st.dataframe(
                    team_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "role": st.column_config.TextColumn(
                            "Role", help="Role bucket used for team composition."
                        ),
                        "player_name": st.column_config.TextColumn(
                            "Player Name", help="Selected player for this role slot."
                        ),
                        "selection_score": st.column_config.NumberColumn(
                            "Selection Score",
                            help="Reliability-adjusted score used for final team selection ranking.",
                            format="%.2f",
                        ),
                        "base_rating": st.column_config.NumberColumn(
                            "Base Rating",
                            help="Raw player rating before reliability adjustment.",
                            format="%.2f",
                        ),
                        "sample_size": st.column_config.NumberColumn(
                            "Sample Size",
                            help="Innings count used to estimate player reliability.",
                        ),
                        "reason": st.column_config.TextColumn(
                            "Reason",
                            help="Why this row exists (default, desired_rating, emerging_slot, or blank_slot).",
                        ),
                        "batting_score": st.column_config.NumberColumn(
                            "Batting Score",
                            help="Normalized batting component score for this player.",
                            format="%.2f",
                        ),
                        "bowling_score": st.column_config.NumberColumn(
                            "Bowling Score",
                            help="Normalized bowling component score for this player.",
                            format="%.2f",
                        ),
                        "fielding_score": st.column_config.NumberColumn(
                            "Fielding Score",
                            help="Normalized fielding component score for this player.",
                            format="%.2f",
                        ),
                    },
                )

                out = []
                out.append("desired_rating_thresholds")
                out.append(thresholds_df.to_csv(index=False).strip())
                out.append("")
                out.append("playing_xi")
                out.append(team_df.to_csv(index=False).strip())
                team_csv_payload = "\n".join(out) + "\n"

                st.download_button(
                    label="Download Team CSV",
                    data=team_csv_payload,
                    file_name="team_output.csv",
                    mime="text/csv",
                )
            except Exception as exc:
                st.error(f"Failed to select team: {exc}")

    with tab_raw:
        st.caption("Aggregated player history from scored matches in the database.")
        if raw_df.empty:
            st.info("No aggregated player rows in database yet.")
        else:
            st.dataframe(raw_df, use_container_width=True, hide_index=True)
            st.download_button(
                label="Download Aggregated DB CSV",
                data=raw_df.to_csv(index=False),
                file_name="db_aggregated_player_history.csv",
                mime="text/csv",
            )

    with tab_config:
        updated_config = _config_editor(st.session_state.active_config)
        st.json(updated_config)

        c1, c2 = st.columns(2)
        if c1.button("Apply Config", use_container_width=True):
            st.session_state.active_config = updated_config
            st.success("Config applied for this session.")

        if c2.button("Save as Default Config", use_container_width=True):
            try:
                _save_default_config(updated_config)
                st.session_state.active_config = updated_config
                st.success("Saved to configs/default_weights.json.")
            except Exception as exc:
                st.error(f"Failed to save config: {exc}")


if __name__ == "__main__":
    main()
