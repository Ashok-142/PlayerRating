from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .loader import normalize_role
from .models import PlayerStats

DEFAULT_DB_PATH = Path("data/player_rating.db")


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: str | Path | None = None) -> None:
    with get_connection(db_path) as conn:
        _ensure_schema(conn)
        conn.commit()


def _ensure_schema(conn: sqlite3.Connection) -> None:
    statements = [
        """
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL COLLATE NOCASE UNIQUE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL COLLATE NOCASE UNIQUE,
            role TEXT NOT NULL DEFAULT 'Batter',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS team_players (
            team_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (team_id, player_id),
            FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
            FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            home_team_id INTEGER NOT NULL,
            away_team_id INTEGER NOT NULL,
            total_overs INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'scheduled',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (home_team_id) REFERENCES teams(id),
            FOREIGN KEY (away_team_id) REFERENCES teams(id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS match_squads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            is_playing_xi INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (match_id, team_id, player_id),
            FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE,
            FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
            FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS innings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER NOT NULL,
            innings_no INTEGER NOT NULL,
            batting_team_id INTEGER NOT NULL,
            bowling_team_id INTEGER NOT NULL,
            total_runs INTEGER NOT NULL DEFAULT 0,
            wickets INTEGER NOT NULL DEFAULT 0,
            legal_balls INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'in_progress',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (match_id, innings_no),
            FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE,
            FOREIGN KEY (batting_team_id) REFERENCES teams(id),
            FOREIGN KEY (bowling_team_id) REFERENCES teams(id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS ball_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER NOT NULL,
            innings_id INTEGER NOT NULL,
            event_seq INTEGER NOT NULL,
            over_no INTEGER NOT NULL,
            ball_in_over INTEGER NOT NULL,
            legal_ball INTEGER NOT NULL DEFAULT 1,
            striker_id INTEGER NOT NULL,
            non_striker_id INTEGER NOT NULL,
            bowler_id INTEGER NOT NULL,
            runs_off_bat INTEGER NOT NULL DEFAULT 0,
            extras INTEGER NOT NULL DEFAULT 0,
            extra_type TEXT NOT NULL DEFAULT 'none',
            is_wicket INTEGER NOT NULL DEFAULT 0,
            dismissal_type TEXT,
            dismissed_player_id INTEGER,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (innings_id, event_seq),
            FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE,
            FOREIGN KEY (innings_id) REFERENCES innings(id) ON DELETE CASCADE,
            FOREIGN KEY (striker_id) REFERENCES players(id),
            FOREIGN KEY (non_striker_id) REFERENCES players(id),
            FOREIGN KEY (bowler_id) REFERENCES players(id),
            FOREIGN KEY (dismissed_player_id) REFERENCES players(id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS player_match_batting_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            innings INTEGER NOT NULL DEFAULT 0,
            runs INTEGER NOT NULL DEFAULT 0,
            balls_faced INTEGER NOT NULL DEFAULT 0,
            fours INTEGER NOT NULL DEFAULT 0,
            sixes INTEGER NOT NULL DEFAULT 0,
            dismissals INTEGER NOT NULL DEFAULT 0,
            not_outs INTEGER NOT NULL DEFAULT 0,
            highest_score INTEGER NOT NULL DEFAULT 0,
            strike_rate REAL NOT NULL DEFAULT 0.0,
            average REAL NOT NULL DEFAULT 0.0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (match_id, player_id),
            FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE,
            FOREIGN KEY (player_id) REFERENCES players(id),
            FOREIGN KEY (team_id) REFERENCES teams(id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS player_match_bowling_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            innings INTEGER NOT NULL DEFAULT 0,
            balls_bowled INTEGER NOT NULL DEFAULT 0,
            runs_conceded INTEGER NOT NULL DEFAULT 0,
            wickets INTEGER NOT NULL DEFAULT 0,
            wides INTEGER NOT NULL DEFAULT 0,
            no_balls INTEGER NOT NULL DEFAULT 0,
            overs REAL NOT NULL DEFAULT 0.0,
            economy REAL NOT NULL DEFAULT 0.0,
            strike_rate REAL NOT NULL DEFAULT 0.0,
            average REAL NOT NULL DEFAULT 0.0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (match_id, player_id),
            FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE,
            FOREIGN KEY (player_id) REFERENCES players(id),
            FOREIGN KEY (team_id) REFERENCES teams(id)
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_ball_events_innings_seq ON ball_events(innings_id, event_seq);",
        "CREATE INDEX IF NOT EXISTS idx_ball_events_match ON ball_events(match_id);",
        "CREATE INDEX IF NOT EXISTS idx_match_squads_match ON match_squads(match_id, team_id);",
        "CREATE INDEX IF NOT EXISTS idx_batting_match_player ON player_match_batting_stats(match_id, player_id);",
        "CREATE INDEX IF NOT EXISTS idx_bowling_match_player ON player_match_bowling_stats(match_id, player_id);",
    ]

    for stmt in statements:
        conn.execute(stmt)


def _normalize_team_name(name: str) -> str:
    cleaned = str(name or "").strip()
    if not cleaned:
        raise ValueError("Team name is required")
    return cleaned


def _normalize_player_name(name: str) -> str:
    cleaned = str(name or "").strip()
    if not cleaned:
        raise ValueError("Player name is required")
    return cleaned


def _normalize_extra_type(extra_type: str) -> str:
    token = str(extra_type or "none").strip().lower()
    allowed = {"none", "wide", "no_ball", "bye", "leg_bye"}
    if token not in allowed:
        raise ValueError(f"Invalid extra_type '{extra_type}'. Allowed: {sorted(allowed)}")
    return token


def _normalize_dismissal_type(dismissal_type: str | None) -> str | None:
    if dismissal_type is None:
        return None
    token = dismissal_type.strip().lower()
    if token == "":
        return None
    return token


def _get_or_create_team(conn: sqlite3.Connection, team_name: str) -> int:
    cleaned = _normalize_team_name(team_name)
    row = conn.execute(
        "SELECT id FROM teams WHERE name = ? COLLATE NOCASE",
        (cleaned,),
    ).fetchone()
    if row:
        return int(row["id"])

    cur = conn.execute("INSERT INTO teams(name) VALUES(?)", (cleaned,))
    return int(cur.lastrowid)


def _get_or_create_player(conn: sqlite3.Connection, player_name: str, role: str = "Batter") -> int:
    cleaned_name = _normalize_player_name(player_name)
    normalized_role = normalize_role(role)

    row = conn.execute(
        "SELECT id, role FROM players WHERE player_name = ? COLLATE NOCASE",
        (cleaned_name,),
    ).fetchone()
    if row:
        player_id = int(row["id"])
        existing_role = str(row["role"])
        if existing_role != normalized_role:
            conn.execute(
                "UPDATE players SET role = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (normalized_role, player_id),
            )
        return player_id

    cur = conn.execute(
        "INSERT INTO players(player_name, role) VALUES(?, ?)",
        (cleaned_name, normalized_role),
    )
    return int(cur.lastrowid)


def create_match_with_squads(
    home_team: str,
    away_team: str,
    total_overs: int,
    home_squad: list[dict[str, str]],
    away_squad: list[dict[str, str]],
    db_path: str | Path | None = None,
) -> int:
    if int(total_overs) <= 0:
        raise ValueError("Total overs must be greater than zero")

    if not home_squad:
        raise ValueError("Home squad cannot be empty")
    if not away_squad:
        raise ValueError("Away squad cannot be empty")

    with get_connection(db_path) as conn:
        _ensure_schema(conn)
        home_team_id = _get_or_create_team(conn, home_team)
        away_team_id = _get_or_create_team(conn, away_team)
        if home_team_id == away_team_id:
            raise ValueError("Home and away team must be different")

        cur = conn.execute(
            """
            INSERT INTO matches(home_team_id, away_team_id, total_overs, status)
            VALUES(?, ?, ?, 'scheduled')
            """,
            (home_team_id, away_team_id, int(total_overs)),
        )
        match_id = int(cur.lastrowid)

        _save_match_squad(conn, match_id, home_team_id, home_squad)
        _save_match_squad(conn, match_id, away_team_id, away_squad)

        conn.commit()
        return match_id


def _save_match_squad(
    conn: sqlite3.Connection,
    match_id: int,
    team_id: int,
    squad: list[dict[str, str]],
) -> None:
    dedupe: set[str] = set()
    for row in squad:
        name = _normalize_player_name(row.get("player_name", ""))
        key = name.lower()
        if key in dedupe:
            continue
        dedupe.add(key)
        role = row.get("role", "Batter")
        player_id = _get_or_create_player(conn, name, role)
        conn.execute(
            "INSERT OR IGNORE INTO team_players(team_id, player_id) VALUES(?, ?)",
            (team_id, player_id),
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO match_squads(match_id, team_id, player_id, is_playing_xi)
            VALUES(?, ?, ?, 1)
            """,
            (match_id, team_id, player_id),
        )


def list_matches(db_path: str | Path | None = None) -> list[dict[str, Any]]:
    with get_connection(db_path) as conn:
        _ensure_schema(conn)
        rows = conn.execute(
            """
            SELECT
                m.id,
                m.total_overs,
                m.status,
                m.created_at,
                m.updated_at,
                ht.id AS home_team_id,
                ht.name AS home_team_name,
                at.id AS away_team_id,
                at.name AS away_team_name
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            ORDER BY m.id DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


def get_match(match_id: int, db_path: str | Path | None = None) -> dict[str, Any] | None:
    with get_connection(db_path) as conn:
        _ensure_schema(conn)
        row = conn.execute(
            """
            SELECT
                m.id,
                m.total_overs,
                m.status,
                m.created_at,
                m.updated_at,
                ht.id AS home_team_id,
                ht.name AS home_team_name,
                at.id AS away_team_id,
                at.name AS away_team_name
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.id = ?
            """,
            (int(match_id),),
        ).fetchone()
    return dict(row) if row else None


def get_match_squads(match_id: int, db_path: str | Path | None = None) -> dict[str, list[dict[str, Any]]]:
    with get_connection(db_path) as conn:
        _ensure_schema(conn)
        rows = conn.execute(
            """
            SELECT
                ms.team_id,
                t.name AS team_name,
                p.id AS player_id,
                p.player_name,
                p.role
            FROM match_squads ms
            JOIN players p ON p.id = ms.player_id
            JOIN teams t ON t.id = ms.team_id
            WHERE ms.match_id = ?
            ORDER BY t.name, p.player_name
            """,
            (int(match_id),),
        ).fetchall()

    result: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        team_name = str(r["team_name"])
        result.setdefault(team_name, []).append(
            {
                "team_id": int(r["team_id"]),
                "player_id": int(r["player_id"]),
                "player_name": str(r["player_name"]),
                "role": str(r["role"]),
            }
        )
    return result


def get_or_create_innings(
    match_id: int,
    innings_no: int,
    batting_team_id: int,
    bowling_team_id: int,
    db_path: str | Path | None = None,
) -> int:
    innings_no = int(innings_no)
    if innings_no <= 0:
        raise ValueError("innings_no must be greater than zero")
    if int(batting_team_id) == int(bowling_team_id):
        raise ValueError("Batting and bowling team must be different")

    with get_connection(db_path) as conn:
        _ensure_schema(conn)
        row = conn.execute(
            "SELECT id FROM innings WHERE match_id = ? AND innings_no = ?",
            (int(match_id), innings_no),
        ).fetchone()
        if row:
            return int(row["id"])

        cur = conn.execute(
            """
            INSERT INTO innings(match_id, innings_no, batting_team_id, bowling_team_id, status)
            VALUES(?, ?, ?, ?, 'in_progress')
            """,
            (int(match_id), innings_no, int(batting_team_id), int(bowling_team_id)),
        )
        conn.execute(
            "UPDATE matches SET status = 'live', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (int(match_id),),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_innings(innings_id: int, db_path: str | Path | None = None) -> dict[str, Any] | None:
    with get_connection(db_path) as conn:
        _ensure_schema(conn)
        row = conn.execute(
            """
            SELECT
                i.id,
                i.match_id,
                i.innings_no,
                i.batting_team_id,
                i.bowling_team_id,
                i.total_runs,
                i.wickets,
                i.legal_balls,
                i.status,
                bt.name AS batting_team_name,
                bw.name AS bowling_team_name
            FROM innings i
            JOIN teams bt ON bt.id = i.batting_team_id
            JOIN teams bw ON bw.id = i.bowling_team_id
            WHERE i.id = ?
            """,
            (int(innings_id),),
        ).fetchone()
    return dict(row) if row else None


def list_innings_for_match(match_id: int, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    with get_connection(db_path) as conn:
        _ensure_schema(conn)
        rows = conn.execute(
            """
            SELECT
                i.id,
                i.match_id,
                i.innings_no,
                i.batting_team_id,
                i.bowling_team_id,
                i.total_runs,
                i.wickets,
                i.legal_balls,
                i.status,
                bt.name AS batting_team_name,
                bw.name AS bowling_team_name
            FROM innings i
            JOIN teams bt ON bt.id = i.batting_team_id
            JOIN teams bw ON bw.id = i.bowling_team_id
            WHERE i.match_id = ?
            ORDER BY i.innings_no
            """,
            (int(match_id),),
        ).fetchall()
    return [dict(r) for r in rows]


def record_ball_event(
    match_id: int,
    innings_id: int,
    striker_id: int,
    non_striker_id: int,
    bowler_id: int,
    runs_off_bat: int = 0,
    extras: int = 0,
    extra_type: str = "none",
    is_wicket: bool = False,
    dismissal_type: str | None = None,
    dismissed_player_id: int | None = None,
    notes: str | None = None,
    db_path: str | Path | None = None,
) -> int:
    if int(striker_id) == int(non_striker_id):
        raise ValueError("Striker and non-striker must be different players")
    if int(runs_off_bat) < 0:
        raise ValueError("runs_off_bat cannot be negative")
    if int(extras) < 0:
        raise ValueError("extras cannot be negative")

    extra_type = _normalize_extra_type(extra_type)
    dismissal_type = _normalize_dismissal_type(dismissal_type)

    if extra_type == "none" and int(extras) > 0:
        raise ValueError("extras must be 0 when extra_type is none")
    if extra_type == "wide" and int(runs_off_bat) > 0:
        raise ValueError("runs_off_bat must be 0 for wides")
    if extra_type in {"bye", "leg_bye"} and int(runs_off_bat) > 0:
        raise ValueError("runs_off_bat must be 0 for byes/leg byes")

    legal_ball = 0 if extra_type in {"wide", "no_ball"} else 1

    with get_connection(db_path) as conn:
        _ensure_schema(conn)
        innings = conn.execute(
            """
            SELECT
                i.id,
                i.match_id,
                i.batting_team_id,
                i.bowling_team_id,
                i.legal_balls,
                i.wickets,
                i.status,
                m.total_overs
            FROM innings i
            JOIN matches m ON m.id = i.match_id
            WHERE i.id = ? AND i.match_id = ?
            """,
            (int(innings_id), int(match_id)),
        ).fetchone()
        if not innings:
            raise ValueError("Invalid innings for match")
        if str(innings["status"]) == "completed":
            raise ValueError("Innings already completed")

        legal_balls = int(innings["legal_balls"])
        wickets = int(innings["wickets"])
        total_overs = int(innings["total_overs"])
        if wickets >= 10:
            raise ValueError("Innings already all out")
        if legal_balls >= total_overs * 6:
            raise ValueError("Innings already reached max overs")

        batting_team_id = int(innings["batting_team_id"])
        bowling_team_id = int(innings["bowling_team_id"])

        def is_in_match_team(player_id: int, team_id: int) -> bool:
            row = conn.execute(
                """
                SELECT 1
                FROM match_squads
                WHERE match_id = ? AND team_id = ? AND player_id = ?
                LIMIT 1
                """,
                (int(match_id), int(team_id), int(player_id)),
            ).fetchone()
            return row is not None

        if not is_in_match_team(int(striker_id), batting_team_id):
            raise ValueError("Striker is not in batting team squad")
        if not is_in_match_team(int(non_striker_id), batting_team_id):
            raise ValueError("Non-striker is not in batting team squad")
        if not is_in_match_team(int(bowler_id), bowling_team_id):
            raise ValueError("Bowler is not in bowling team squad")
        if dismissed_player_id is not None and not is_in_match_team(
            int(dismissed_player_id), batting_team_id
        ):
            raise ValueError("Dismissed player is not in batting team squad")

        seq_row = conn.execute(
            "SELECT COALESCE(MAX(event_seq), 0) AS max_seq FROM ball_events WHERE innings_id = ?",
            (int(innings_id),),
        ).fetchone()
        next_seq = int(seq_row["max_seq"]) + 1

        if legal_ball == 1:
            legal_index = legal_balls + 1
            over_no = (legal_index - 1) // 6
            ball_in_over = ((legal_index - 1) % 6) + 1
        else:
            over_no = legal_balls // 6
            ball_in_over = (legal_balls % 6) + 1

        cur = conn.execute(
            """
            INSERT INTO ball_events(
                match_id,
                innings_id,
                event_seq,
                over_no,
                ball_in_over,
                legal_ball,
                striker_id,
                non_striker_id,
                bowler_id,
                runs_off_bat,
                extras,
                extra_type,
                is_wicket,
                dismissal_type,
                dismissed_player_id,
                notes
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(match_id),
                int(innings_id),
                next_seq,
                over_no,
                ball_in_over,
                legal_ball,
                int(striker_id),
                int(non_striker_id),
                int(bowler_id),
                int(runs_off_bat),
                int(extras),
                extra_type,
                1 if is_wicket else 0,
                dismissal_type,
                int(dismissed_player_id) if dismissed_player_id else None,
                notes.strip() if isinstance(notes, str) and notes.strip() else None,
            ),
        )

        _recompute_match_state(conn, int(match_id))
        conn.commit()
        return int(cur.lastrowid)


def undo_last_ball(innings_id: int, db_path: str | Path | None = None) -> bool:
    with get_connection(db_path) as conn:
        _ensure_schema(conn)
        target = conn.execute(
            """
            SELECT id, match_id
            FROM ball_events
            WHERE innings_id = ?
            ORDER BY event_seq DESC
            LIMIT 1
            """,
            (int(innings_id),),
        ).fetchone()
        if not target:
            return False

        conn.execute("DELETE FROM ball_events WHERE id = ?", (int(target["id"]),))
        _recompute_match_state(conn, int(target["match_id"]))
        conn.commit()
        return True


def get_ball_events(
    innings_id: int,
    limit: int = 48,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    with get_connection(db_path) as conn:
        _ensure_schema(conn)
        rows = conn.execute(
            """
            SELECT
                e.id,
                e.event_seq,
                e.over_no,
                e.ball_in_over,
                e.legal_ball,
                e.runs_off_bat,
                e.extras,
                e.extra_type,
                e.is_wicket,
                e.dismissal_type,
                sp.player_name AS striker_name,
                nsp.player_name AS non_striker_name,
                bp.player_name AS bowler_name,
                dp.player_name AS dismissed_player_name
            FROM ball_events e
            JOIN players sp ON sp.id = e.striker_id
            JOIN players nsp ON nsp.id = e.non_striker_id
            JOIN players bp ON bp.id = e.bowler_id
            LEFT JOIN players dp ON dp.id = e.dismissed_player_id
            WHERE e.innings_id = ?
            ORDER BY e.event_seq DESC
            LIMIT ?
            """,
            (int(innings_id), int(limit)),
        ).fetchall()
    return [dict(r) for r in rows]


def get_match_batting_stats(match_id: int, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    with get_connection(db_path) as conn:
        _ensure_schema(conn)
        rows = conn.execute(
            """
            SELECT
                t.name AS team_name,
                p.player_name,
                p.role,
                s.innings,
                s.runs,
                s.balls_faced,
                s.fours,
                s.sixes,
                s.dismissals,
                s.not_outs,
                s.highest_score,
                s.strike_rate,
                s.average
            FROM player_match_batting_stats s
            JOIN players p ON p.id = s.player_id
            JOIN teams t ON t.id = s.team_id
            WHERE s.match_id = ?
            ORDER BY t.name, s.runs DESC, p.player_name
            """,
            (int(match_id),),
        ).fetchall()
    return [dict(r) for r in rows]


def get_match_bowling_stats(match_id: int, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    with get_connection(db_path) as conn:
        _ensure_schema(conn)
        rows = conn.execute(
            """
            SELECT
                t.name AS team_name,
                p.player_name,
                p.role,
                s.innings,
                s.overs,
                s.balls_bowled,
                s.runs_conceded,
                s.wickets,
                s.wides,
                s.no_balls,
                s.economy,
                s.strike_rate,
                s.average
            FROM player_match_bowling_stats s
            JOIN players p ON p.id = s.player_id
            JOIN teams t ON t.id = s.team_id
            WHERE s.match_id = ?
            ORDER BY t.name, s.wickets DESC, s.economy ASC, p.player_name
            """,
            (int(match_id),),
        ).fetchall()
    return [dict(r) for r in rows]


def load_player_history_from_db(db_path: str | Path | None = None) -> list[PlayerStats]:
    with get_connection(db_path) as conn:
        _ensure_schema(conn)
        players = conn.execute(
            """
            SELECT id, player_name, role, is_active
            FROM players
            WHERE is_active = 1
            ORDER BY player_name
            """
        ).fetchall()

        batting_rows = conn.execute(
            """
            SELECT
                player_id,
                COUNT(*) AS batting_matches,
                COALESCE(SUM(innings), 0) AS batting_innings,
                COALESCE(SUM(runs), 0) AS batting_runs,
                COALESCE(SUM(not_outs), 0) AS batting_not_out,
                COALESCE(MAX(highest_score), 0) AS batting_high_score,
                COALESCE(SUM(balls_faced), 0) AS batting_balls_faced,
                COALESCE(SUM(dismissals), 0) AS batting_dismissals
            FROM player_match_batting_stats
            GROUP BY player_id
            """
        ).fetchall()
        batting_by_player = {int(r["player_id"]): dict(r) for r in batting_rows}

        bowling_rows = conn.execute(
            """
            SELECT
                player_id,
                COUNT(*) AS bowling_matches,
                COALESCE(SUM(innings), 0) AS bowling_innings,
                COALESCE(SUM(balls_bowled), 0) AS bowling_balls,
                COALESCE(SUM(runs_conceded), 0) AS bowling_runs,
                COALESCE(SUM(wickets), 0) AS bowling_wickets,
                COALESCE(SUM(wides), 0) AS bowling_wides,
                COALESCE(SUM(no_balls), 0) AS bowling_no_ball
            FROM player_match_bowling_stats
            GROUP BY player_id
            """
        ).fetchall()
        bowling_by_player = {int(r["player_id"]): dict(r) for r in bowling_rows}

    records: list[PlayerStats] = []
    for row in players:
        player_id = int(row["id"])
        player_name = str(row["player_name"])
        role = str(row["role"])
        batting = batting_by_player.get(player_id, {})
        bowling = bowling_by_player.get(player_id, {})

        batting_runs = int(batting.get("batting_runs", 0))
        batting_innings = int(batting.get("batting_innings", 0))
        batting_dismissals = int(batting.get("batting_dismissals", 0))
        batting_balls_faced = int(batting.get("batting_balls_faced", 0))
        batting_avg = (batting_runs / batting_dismissals) if batting_dismissals > 0 else float(batting_runs)
        batting_strike_rate = (
            (batting_runs * 100.0 / batting_balls_faced) if batting_balls_faced > 0 else 0.0
        )

        bowling_balls = int(bowling.get("bowling_balls", 0))
        bowling_runs = int(bowling.get("bowling_runs", 0))
        bowling_wickets = int(bowling.get("bowling_wickets", 0))
        bowling_overs = bowling_balls / 6.0
        bowling_avg = (bowling_runs / bowling_wickets) if bowling_wickets > 0 else 0.0
        bowling_economy = (bowling_runs / (bowling_balls / 6.0)) if bowling_balls > 0 else 0.0
        bowling_strike_rate = (bowling_balls / bowling_wickets) if bowling_wickets > 0 else 0.0

        records.append(
            PlayerStats(
                player_name=player_name,
                role=role,
                availability=bool(int(row["is_active"])),
                batting_matches=int(batting.get("batting_matches", 0)),
                batting_innings=batting_innings,
                batting_runs=batting_runs,
                batting_not_out=int(batting.get("batting_not_out", 0)),
                batting_high_score=int(batting.get("batting_high_score", 0)),
                batting_avg=batting_avg,
                batting_strike_rate=batting_strike_rate,
                bowling_matches=int(bowling.get("bowling_matches", 0)),
                bowling_innings=int(bowling.get("bowling_innings", 0)),
                bowling_overs=bowling_overs,
                bowling_runs=bowling_runs,
                bowling_wickets=bowling_wickets,
                bowling_economy=bowling_economy,
                bowling_strike_rate=bowling_strike_rate,
                bowling_avg=bowling_avg,
                bowling_wides=int(bowling.get("bowling_wides", 0)),
                bowling_no_ball=int(bowling.get("bowling_no_ball", 0)),
                fielding_matches=0,
                fielding_catches=0,
                fielding_caught_behind=0,
                fielding_run_out=0,
                fielding_stumping=0,
            )
        )

    return records


def _recompute_match_state(conn: sqlite3.Connection, match_id: int) -> None:
    innings_rows = conn.execute(
        """
        SELECT i.id, i.innings_no, i.wickets, i.legal_balls, m.total_overs
        FROM innings i
        JOIN matches m ON m.id = i.match_id
        WHERE i.match_id = ?
        """,
        (int(match_id),),
    ).fetchall()

    for innings_row in innings_rows:
        innings_id = int(innings_row["id"])
        totals = conn.execute(
            """
            SELECT
                COALESCE(SUM(runs_off_bat + extras), 0) AS total_runs,
                COALESCE(SUM(CASE WHEN legal_ball = 1 THEN 1 ELSE 0 END), 0) AS legal_balls,
                COALESCE(SUM(CASE WHEN is_wicket = 1 THEN 1 ELSE 0 END), 0) AS wickets
            FROM ball_events
            WHERE innings_id = ?
            """,
            (innings_id,),
        ).fetchone()

        total_runs = int(totals["total_runs"])
        legal_balls = int(totals["legal_balls"])
        wickets = int(totals["wickets"])
        total_overs = int(innings_row["total_overs"])
        innings_status = (
            "completed" if wickets >= 10 or legal_balls >= total_overs * 6 else "in_progress"
        )

        conn.execute(
            """
            UPDATE innings
            SET total_runs = ?, wickets = ?, legal_balls = ?, status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (total_runs, wickets, legal_balls, innings_status, innings_id),
        )

    completed_count_row = conn.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END), 0) AS completed_count,
            COUNT(*) AS innings_count
        FROM innings
        WHERE match_id = ?
        """,
        (int(match_id),),
    ).fetchone()
    event_count_row = conn.execute(
        "SELECT COUNT(*) AS event_count FROM ball_events WHERE match_id = ?",
        (int(match_id),),
    ).fetchone()

    completed_count = int(completed_count_row["completed_count"])
    innings_count = int(completed_count_row["innings_count"])
    event_count = int(event_count_row["event_count"])

    if innings_count >= 2 and completed_count >= 2:
        match_status = "completed"
    elif event_count > 0:
        match_status = "live"
    else:
        match_status = "scheduled"

    conn.execute(
        "UPDATE matches SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (match_status, int(match_id)),
    )
    _recompute_match_player_stats(conn, int(match_id))


def _recompute_match_player_stats(conn: sqlite3.Connection, match_id: int) -> None:
    innings_rows = conn.execute(
        """
        SELECT id, batting_team_id, bowling_team_id
        FROM innings
        WHERE match_id = ?
        """,
        (int(match_id),),
    ).fetchall()
    innings_by_id = {
        int(r["id"]): {
            "batting_team_id": int(r["batting_team_id"]),
            "bowling_team_id": int(r["bowling_team_id"]),
        }
        for r in innings_rows
    }

    event_rows = conn.execute(
        """
        SELECT
            innings_id,
            striker_id,
            non_striker_id,
            bowler_id,
            runs_off_bat,
            extras,
            extra_type,
            legal_ball,
            is_wicket,
            dismissal_type,
            dismissed_player_id
        FROM ball_events
        WHERE match_id = ?
        ORDER BY innings_id, event_seq
        """,
        (int(match_id),),
    ).fetchall()

    batting: dict[int, dict[str, Any]] = {}
    bowling: dict[int, dict[str, Any]] = {}
    batting_runs_by_innings: dict[tuple[int, int], int] = {}

    def ensure_batter(player_id: int, team_id: int) -> dict[str, Any]:
        if player_id not in batting:
            batting[player_id] = {
                "team_id": team_id,
                "innings": set(),
                "runs": 0,
                "balls_faced": 0,
                "fours": 0,
                "sixes": 0,
                "dismissals": 0,
            }
        return batting[player_id]

    def ensure_bowler(player_id: int, team_id: int) -> dict[str, Any]:
        if player_id not in bowling:
            bowling[player_id] = {
                "team_id": team_id,
                "innings": set(),
                "balls_bowled": 0,
                "runs_conceded": 0,
                "wickets": 0,
                "wides": 0,
                "no_balls": 0,
            }
        return bowling[player_id]

    for row in event_rows:
        innings_id = int(row["innings_id"])
        innings_meta = innings_by_id.get(innings_id)
        if not innings_meta:
            continue

        batting_team_id = int(innings_meta["batting_team_id"])
        bowling_team_id = int(innings_meta["bowling_team_id"])

        striker_id = int(row["striker_id"])
        non_striker_id = int(row["non_striker_id"])
        bowler_id = int(row["bowler_id"])
        runs_off_bat = int(row["runs_off_bat"])
        extras = int(row["extras"])
        extra_type = str(row["extra_type"])
        legal_ball = int(row["legal_ball"])
        is_wicket = int(row["is_wicket"])
        dismissal_type = _normalize_dismissal_type(row["dismissal_type"])
        dismissed_player_id = row["dismissed_player_id"]

        batter = ensure_batter(striker_id, batting_team_id)
        batter["innings"].add(innings_id)
        batter["runs"] += runs_off_bat
        if legal_ball == 1:
            batter["balls_faced"] += 1
        if runs_off_bat == 4:
            batter["fours"] += 1
        if runs_off_bat == 6:
            batter["sixes"] += 1
        batting_runs_by_innings[(striker_id, innings_id)] = batting_runs_by_innings.get(
            (striker_id, innings_id), 0
        ) + runs_off_bat

        ensure_batter(non_striker_id, batting_team_id)["innings"].add(innings_id)

        if dismissed_player_id is not None:
            out_id = int(dismissed_player_id)
            out_batter = ensure_batter(out_id, batting_team_id)
            out_batter["innings"].add(innings_id)
            out_batter["dismissals"] += 1

        bowler = ensure_bowler(bowler_id, bowling_team_id)
        bowler["innings"].add(innings_id)
        if legal_ball == 1:
            bowler["balls_bowled"] += 1

        conceded = runs_off_bat
        if extra_type == "wide":
            bowler["wides"] += extras
            conceded += extras
        elif extra_type == "no_ball":
            bowler["no_balls"] += extras
            conceded += extras
        elif extra_type in {"bye", "leg_bye"}:
            conceded += 0
        else:
            conceded += extras
        bowler["runs_conceded"] += conceded

        if is_wicket == 1 and dismissal_type != "run_out":
            bowler["wickets"] += 1

    conn.execute("DELETE FROM player_match_batting_stats WHERE match_id = ?", (int(match_id),))
    conn.execute("DELETE FROM player_match_bowling_stats WHERE match_id = ?", (int(match_id),))

    for player_id, stats in batting.items():
        innings_count = len(stats["innings"])
        dismissals = int(stats["dismissals"])
        not_outs = max(innings_count - dismissals, 0)
        runs = int(stats["runs"])
        balls_faced = int(stats["balls_faced"])
        strike_rate = (runs * 100.0 / balls_faced) if balls_faced > 0 else 0.0
        average = (runs / dismissals) if dismissals > 0 else float(runs)
        highest = 0
        for innings_id in stats["innings"]:
            highest = max(highest, batting_runs_by_innings.get((player_id, innings_id), 0))

        conn.execute(
            """
            INSERT INTO player_match_batting_stats(
                match_id,
                player_id,
                team_id,
                innings,
                runs,
                balls_faced,
                fours,
                sixes,
                dismissals,
                not_outs,
                highest_score,
                strike_rate,
                average
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(match_id),
                int(player_id),
                int(stats["team_id"]),
                innings_count,
                runs,
                balls_faced,
                int(stats["fours"]),
                int(stats["sixes"]),
                dismissals,
                not_outs,
                highest,
                strike_rate,
                average,
            ),
        )

    for player_id, stats in bowling.items():
        innings_count = len(stats["innings"])
        balls_bowled = int(stats["balls_bowled"])
        runs_conceded = int(stats["runs_conceded"])
        wickets = int(stats["wickets"])
        overs = balls_bowled / 6.0
        economy = (runs_conceded / (balls_bowled / 6.0)) if balls_bowled > 0 else 0.0
        strike_rate = (balls_bowled / wickets) if wickets > 0 else 0.0
        average = (runs_conceded / wickets) if wickets > 0 else 0.0

        conn.execute(
            """
            INSERT INTO player_match_bowling_stats(
                match_id,
                player_id,
                team_id,
                innings,
                balls_bowled,
                runs_conceded,
                wickets,
                wides,
                no_balls,
                overs,
                economy,
                strike_rate,
                average
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(match_id),
                int(player_id),
                int(stats["team_id"]),
                innings_count,
                balls_bowled,
                runs_conceded,
                wickets,
                int(stats["wides"]),
                int(stats["no_balls"]),
                overs,
                economy,
                strike_rate,
                average,
            ),
        )
