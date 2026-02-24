from __future__ import annotations

import json
import tempfile
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

from player_rating_tool.loader import load_player_history
from player_rating_tool.rating import load_weights, rate_players
from player_rating_tool.selector import select_team

CONFIG_PATH = Path("configs/default_weights.json")


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
    st.set_page_config(page_title="Team Selection App", layout="wide")
    st.title("Team Selection App")
    st.write("Upload a CSV file to view ratings, team selection, raw input, and editable config.")

    if "active_config" not in st.session_state:
        try:
            st.session_state.active_config = _load_default_config()
        except Exception as exc:
            st.error(f"Failed to load default config: {exc}")
            return

    uploaded_file = st.file_uploader("Input CSV", type=["csv"])
    if uploaded_file is None:
        st.info("Please upload a CSV file to continue.")
        return

    upload_token = f"{uploaded_file.name}:{uploaded_file.size}"
    try:
        if st.session_state.get("uploaded_file_token") != upload_token:
            st.session_state.uploaded_file_token = upload_token
            st.session_state.raw_df = _read_uploaded_csv(uploaded_file)

        raw_df = st.session_state.raw_df
    except Exception as exc:
        st.error(f"Failed to parse uploaded CSV: {exc}")
        return

    main_team_structure = _team_structure_editor(st.session_state.active_config, key_prefix="main")
    c1, c2 = st.columns(2)
    if c1.button("Apply Team Structure", use_container_width=True):
        config = dict(st.session_state.active_config)
        config["team_structure"] = main_team_structure
        st.session_state.active_config = config
        st.success("Team structure applied for this session.")
    if c2.button("Save Team Structure as Default", use_container_width=True):
        try:
            config = dict(st.session_state.active_config)
            config["team_structure"] = main_team_structure
            _save_default_config(config)
            st.session_state.active_config = config
            st.success("Team structure saved to configs/default_weights.json.")
        except Exception as exc:
            st.error(f"Failed to save team structure: {exc}")

    weights = st.session_state.active_config

    tab_team, tab_rate, tab_raw, tab_config = st.tabs(
        ["Playing XI", "Player Rating", "Raw Input", "Config"]
    )

    with tab_rate:
        try:
            records = _load_records_from_dataframe(raw_df)
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
        try:
            records = _load_records_from_dataframe(raw_df)
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
        edited_raw_df = st.data_editor(
            raw_df,
            num_rows="dynamic",
            use_container_width=True,
            key="raw_input_editor",
        )
        c1, c2 = st.columns(2)
        if c1.button("Apply Raw Input Edits", use_container_width=True):
            st.session_state.raw_df = edited_raw_df
            st.success("Raw input updated. Rate and Team tabs now use edited data.")
            st.rerun()
        if c2.button("Reset Raw Input to Uploaded File", use_container_width=True):
            st.session_state.raw_df = _read_uploaded_csv(uploaded_file)
            st.success("Raw input reset to uploaded CSV.")
            st.rerun()

        st.download_button(
            label="Download Raw CSV",
            data=edited_raw_df.to_csv(index=False),
            file_name="raw_input.csv",
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
