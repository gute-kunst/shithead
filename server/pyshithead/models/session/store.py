from __future__ import annotations

import json
import os
import sqlite3
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median

DEFAULT_DATABASE_URL = "sqlite:///./shithead.db"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _day_key(value: str) -> str:
    return datetime.fromisoformat(value).date().isoformat()


class SQLiteSessionStore:
    def __init__(self, database_url: str | None = None):
        resolved_database_url = database_url or os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
        self.database_url = resolved_database_url
        self.db_path = self._resolve_sqlite_path(resolved_database_url)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @staticmethod
    def _resolve_sqlite_path(database_url: str) -> Path:
        if not database_url.startswith("sqlite:///"):
            raise ValueError("Only sqlite:/// DATABASE_URL values are currently supported.")
        raw_path = database_url.removeprefix("sqlite:///")
        return Path(raw_path).expanduser().resolve()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self):
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS game_sessions (
                    invite_code TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    host_seat INTEGER NOT NULL,
                    host_token TEXT NOT NULL,
                    last_status_message TEXT,
                    pending_joker_seat INTEGER,
                    pending_joker_card_json TEXT,
                    pending_hidden_take_seat INTEGER,
                    disconnect_timeout_seconds INTEGER NOT NULL,
                    last_activity_at TEXT NOT NULL,
                    settings_json TEXT NOT NULL,
                    game_state_json TEXT
                );

                CREATE TABLE IF NOT EXISTS session_players (
                    invite_code TEXT NOT NULL,
                    seat INTEGER NOT NULL,
                    display_name TEXT NOT NULL,
                    token TEXT NOT NULL,
                    connected INTEGER NOT NULL,
                    last_seen TEXT NOT NULL,
                    disconnect_deadline_at TEXT,
                    disconnect_action TEXT,
                    PRIMARY KEY (invite_code, seat),
                    FOREIGN KEY (invite_code) REFERENCES game_sessions(invite_code) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS stats_users (
                    user_id TEXT PRIMARY KEY,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS stats_lobbies (
                    invite_code TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    creator_user_id TEXT
                );

                CREATE TABLE IF NOT EXISTS stats_games (
                    game_id INTEGER PRIMARY KEY,
                    invite_code TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    abandoned_at TEXT,
                    status TEXT NOT NULL,
                    player_count INTEGER NOT NULL
                );
                """
            )
            player_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(session_players)").fetchall()
            }
            if "disconnect_deadline_at" not in player_columns:
                try:
                    connection.execute(
                        "ALTER TABLE session_players ADD COLUMN disconnect_deadline_at TEXT"
                    )
                except sqlite3.OperationalError as err:
                    if "duplicate column name" not in str(err).lower():
                        raise
            if "disconnect_action" not in player_columns:
                try:
                    connection.execute(
                        "ALTER TABLE session_players ADD COLUMN disconnect_action TEXT"
                    )
                except sqlite3.OperationalError as err:
                    if "duplicate column name" not in str(err).lower():
                        raise

            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_stats_users_first_seen_at ON stats_users(first_seen_at)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_stats_users_last_seen_at ON stats_users(last_seen_at)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_stats_lobbies_created_at ON stats_lobbies(created_at)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_stats_games_started_at ON stats_games(started_at)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_stats_games_completed_at ON stats_games(completed_at)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_stats_games_abandoned_at ON stats_games(abandoned_at)"
            )

    def clear_all(self):
        with self._connect() as connection:
            connection.execute("DELETE FROM session_players")
            connection.execute("DELETE FROM game_sessions")
            connection.execute("DELETE FROM stats_games")
            connection.execute("DELETE FROM stats_lobbies")
            connection.execute("DELETE FROM stats_users")

    def mark_all_players_disconnected(self):
        with self._connect() as connection:
            connection.execute("UPDATE session_players SET connected = 0")

    def ensure_user_seen(self, user_id: str, seen_at: datetime | None = None):
        timestamp = (seen_at or _utc_now()).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO stats_users (
                    user_id,
                    first_seen_at,
                    last_seen_at
                ) VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    first_seen_at = CASE
                        WHEN excluded.first_seen_at < stats_users.first_seen_at
                        THEN excluded.first_seen_at
                        ELSE stats_users.first_seen_at
                    END,
                    last_seen_at = CASE
                        WHEN excluded.last_seen_at > stats_users.last_seen_at
                        THEN excluded.last_seen_at
                        ELSE stats_users.last_seen_at
                    END
                """,
                (user_id, timestamp, timestamp),
            )

    def record_lobby_created(
        self,
        invite_code: str,
        created_at: datetime | None = None,
        creator_user_id: str | None = None,
    ):
        timestamp = (created_at or _utc_now()).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO stats_lobbies (
                    invite_code,
                    created_at,
                    creator_user_id
                ) VALUES (?, ?, ?)
                ON CONFLICT(invite_code) DO NOTHING
                """,
                (invite_code, timestamp, creator_user_id),
            )

    def record_game_started(
        self,
        game_id: int,
        invite_code: str,
        started_at: datetime | None = None,
        player_count: int = 0,
    ):
        timestamp = (started_at or _utc_now()).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO stats_games (
                    game_id,
                    invite_code,
                    started_at,
                    completed_at,
                    abandoned_at,
                    status,
                    player_count
                ) VALUES (?, ?, ?, NULL, NULL, 'started', ?)
                ON CONFLICT(game_id) DO UPDATE SET
                    invite_code = excluded.invite_code,
                    started_at = COALESCE(stats_games.started_at, excluded.started_at),
                    status = CASE
                        WHEN stats_games.completed_at IS NOT NULL THEN 'completed'
                        WHEN stats_games.abandoned_at IS NOT NULL THEN 'abandoned'
                        ELSE 'started'
                    END,
                    player_count = CASE
                        WHEN stats_games.player_count = 0 THEN excluded.player_count
                        ELSE stats_games.player_count
                    END
                """,
                (game_id, invite_code, timestamp, player_count),
            )

    def record_game_completed(
        self,
        game_id: int,
        invite_code: str,
        completed_at: datetime | None = None,
        player_count: int = 0,
    ):
        timestamp = (completed_at or _utc_now()).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO stats_games (
                    game_id,
                    invite_code,
                    started_at,
                    completed_at,
                    abandoned_at,
                    status,
                    player_count
                ) VALUES (?, ?, ?, ?, NULL, 'completed', ?)
                ON CONFLICT(game_id) DO UPDATE SET
                    invite_code = excluded.invite_code,
                    started_at = COALESCE(stats_games.started_at, excluded.started_at),
                    completed_at = CASE
                        WHEN stats_games.abandoned_at IS NOT NULL THEN stats_games.completed_at
                        ELSE COALESCE(stats_games.completed_at, excluded.completed_at)
                    END,
                    status = CASE
                        WHEN stats_games.abandoned_at IS NOT NULL THEN 'abandoned'
                        ELSE 'completed'
                    END,
                    player_count = CASE
                        WHEN stats_games.player_count = 0 THEN excluded.player_count
                        ELSE stats_games.player_count
                    END
                """,
                (game_id, invite_code, timestamp, timestamp, player_count),
            )

    def record_game_abandoned(
        self,
        game_id: int,
        invite_code: str,
        abandoned_at: datetime | None = None,
        player_count: int = 0,
    ):
        timestamp = (abandoned_at or _utc_now()).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO stats_games (
                    game_id,
                    invite_code,
                    started_at,
                    completed_at,
                    abandoned_at,
                    status,
                    player_count
                ) VALUES (?, ?, ?, NULL, ?, 'abandoned', ?)
                ON CONFLICT(game_id) DO UPDATE SET
                    invite_code = excluded.invite_code,
                    started_at = COALESCE(stats_games.started_at, excluded.started_at),
                    abandoned_at = CASE
                        WHEN stats_games.completed_at IS NOT NULL THEN stats_games.abandoned_at
                        ELSE COALESCE(stats_games.abandoned_at, excluded.abandoned_at)
                    END,
                    status = CASE
                        WHEN stats_games.completed_at IS NOT NULL THEN 'completed'
                        ELSE 'abandoned'
                    END,
                    player_count = CASE
                        WHEN stats_games.player_count = 0 THEN excluded.player_count
                        ELSE stats_games.player_count
                    END
                """,
                (game_id, invite_code, timestamp, timestamp, player_count),
            )

    def invite_code_exists(self, invite_code: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM game_sessions WHERE invite_code = ?",
                (invite_code,),
            ).fetchone()
        return row is not None

    def save_session_record(self, record: dict):
        pending_joker_card_json = (
            json.dumps(record["pending_joker_card"])
            if record["pending_joker_card"] is not None
            else None
        )
        game_state_json = (
            json.dumps(record["game_state"]) if record["game_state"] is not None else None
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO game_sessions (
                    invite_code,
                    status,
                    host_seat,
                    host_token,
                    last_status_message,
                    pending_joker_seat,
                    pending_joker_card_json,
                    pending_hidden_take_seat,
                    disconnect_timeout_seconds,
                    last_activity_at,
                    settings_json,
                    game_state_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(invite_code) DO UPDATE SET
                    status = excluded.status,
                    host_seat = excluded.host_seat,
                    host_token = excluded.host_token,
                    last_status_message = excluded.last_status_message,
                    pending_joker_seat = excluded.pending_joker_seat,
                    pending_joker_card_json = excluded.pending_joker_card_json,
                    pending_hidden_take_seat = excluded.pending_hidden_take_seat,
                    disconnect_timeout_seconds = excluded.disconnect_timeout_seconds,
                    last_activity_at = excluded.last_activity_at,
                    settings_json = excluded.settings_json,
                    game_state_json = excluded.game_state_json
                """,
                (
                    record["invite_code"],
                    record["status"],
                    record["host_seat"],
                    record["host_token"],
                    record["last_status_message"],
                    record["pending_joker_seat"],
                    pending_joker_card_json,
                    record["pending_hidden_take_seat"],
                    record["disconnect_timeout_seconds"],
                    record["last_activity_at"],
                    json.dumps(record["settings"]),
                    game_state_json,
                ),
            )
            connection.execute(
                "DELETE FROM session_players WHERE invite_code = ?",
                (record["invite_code"],),
            )
            connection.executemany(
                """
                INSERT INTO session_players (
                    invite_code,
                    seat,
                    display_name,
                    token,
                    connected,
                    last_seen,
                    disconnect_deadline_at,
                    disconnect_action
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        record["invite_code"],
                        player["seat"],
                        player["display_name"],
                        player["token"],
                        int(player["connected"]),
                        player["last_seen"],
                        player.get("disconnect_deadline_at"),
                        player.get("disconnect_action"),
                    )
                    for player in record["players"]
                ],
            )

    def load_session_record(self, invite_code: str) -> dict | None:
        with self._connect() as connection:
            session_row = connection.execute(
                "SELECT * FROM game_sessions WHERE invite_code = ?",
                (invite_code,),
            ).fetchone()
            if session_row is None:
                return None
            player_rows = connection.execute(
                """
                SELECT
                    seat,
                    display_name,
                    token,
                    connected,
                    last_seen,
                    disconnect_deadline_at,
                    disconnect_action
                FROM session_players
                WHERE invite_code = ?
                ORDER BY seat
                """,
                (invite_code,),
            ).fetchall()
        return {
            "invite_code": session_row["invite_code"],
            "status": session_row["status"],
            "host_seat": session_row["host_seat"],
            "host_token": session_row["host_token"],
            "last_status_message": session_row["last_status_message"],
            "pending_joker_seat": session_row["pending_joker_seat"],
            "pending_joker_card": (
                json.loads(session_row["pending_joker_card_json"])
                if session_row["pending_joker_card_json"]
                else None
            ),
            "pending_hidden_take_seat": session_row["pending_hidden_take_seat"],
            "disconnect_timeout_seconds": session_row["disconnect_timeout_seconds"],
            "last_activity_at": session_row["last_activity_at"],
            "settings": json.loads(session_row["settings_json"]),
            "game_state": (
                json.loads(session_row["game_state_json"])
                if session_row["game_state_json"]
                else None
            ),
            "players": [
                {
                    "seat": row["seat"],
                    "display_name": row["display_name"],
                    "token": row["token"],
                    "connected": bool(row["connected"]),
                    "last_seen": row["last_seen"],
                    "disconnect_deadline_at": row["disconnect_deadline_at"],
                    "disconnect_action": row["disconnect_action"],
                }
                for row in player_rows
            ],
        }

    def delete_session(self, invite_code: str):
        with self._connect() as connection:
            connection.execute("DELETE FROM game_sessions WHERE invite_code = ?", (invite_code,))

    def list_session_records(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT invite_code FROM game_sessions ORDER BY invite_code"
            ).fetchall()
        records = []
        for row in rows:
            record = self.load_session_record(row["invite_code"])
            if record is not None:
                records.append(record)
        return records

    def build_stats(self, days: int = 30, now: datetime | None = None) -> dict:
        if days < 7 or days > 365:
            raise ValueError("days must be between 7 and 365.")

        current = now or _utc_now()
        today = current.date()
        window_start = today - timedelta(days=days - 1)
        recent_windows = {7: today - timedelta(days=6), 30: today - timedelta(days=29)}

        with self._connect() as connection:
            user_rows = connection.execute(
                "SELECT user_id, first_seen_at, last_seen_at FROM stats_users"
            ).fetchall()
            lobby_rows = connection.execute(
                "SELECT created_at FROM stats_lobbies"
            ).fetchall()
            game_rows = connection.execute(
                """
                SELECT
                    started_at,
                    completed_at,
                    abandoned_at,
                    status,
                    player_count
                FROM stats_games
                """
            ).fetchall()

        def date_from_row(value: str) -> str:
            return _day_key(value)

        def count_by_day(rows, column_name: str) -> dict[str, int]:
            counter: Counter[str] = Counter()
            for row in rows:
                value = row[column_name]
                if value:
                    counter[date_from_row(value)] += 1
            return counter

        daily_completed = count_by_day(game_rows, "completed_at")
        daily_started = count_by_day(game_rows, "started_at")
        daily_lobbies = count_by_day(lobby_rows, "created_at")
        daily_new_users = count_by_day(user_rows, "first_seen_at")

        date_range = [window_start + timedelta(days=offset) for offset in range(days)]

        completed_games = [row for row in game_rows if row["completed_at"]]
        started_games = [row for row in game_rows if row["started_at"]]

        durations = []
        for row in completed_games:
            started_at = datetime.fromisoformat(row["started_at"])
            completed_at = datetime.fromisoformat(row["completed_at"])
            durations.append((completed_at - started_at).total_seconds())

        total_users = len(user_rows)
        total_lobbies_created = len(lobby_rows)
        total_games_started = len(started_games)
        total_games_completed = len(completed_games)
        total_games_abandoned = sum(1 for row in game_rows if row["abandoned_at"])

        def window_count(rows, column_name: str, start_date) -> int:
            count = 0
            for row in rows:
                value = row[column_name]
                if value and datetime.fromisoformat(value).date() >= start_date:
                    count += 1
            return count

        recent_users = {
            label: window_count(user_rows, "first_seen_at", start_date)
            for label, start_date in recent_windows.items()
        }
        returning_users = {}
        for label, start_date in recent_windows.items():
            count = 0
            for row in user_rows:
                first_seen = datetime.fromisoformat(row["first_seen_at"]).date()
                last_seen = datetime.fromisoformat(row["last_seen_at"]).date()
                if first_seen < start_date and last_seen >= start_date:
                    count += 1
            returning_users[label] = count

        recent_games_played = {
            label: window_count(game_rows, "completed_at", start_date)
            for label, start_date in recent_windows.items()
        }
        recent_lobbies_created = {
            label: window_count(lobby_rows, "created_at", start_date)
            for label, start_date in recent_windows.items()
        }
        today_key = today.isoformat()

        def series(counter: dict[str, int]) -> list[dict[str, int | str]]:
            return [
                {"date": day.isoformat(), "count": counter.get(day.isoformat(), 0)}
                for day in date_range
            ]

        def average(values: list[float]) -> float:
            return round(sum(values) / len(values), 2) if values else 0.0

        def completion_rate(numerator: int, denominator: int) -> float:
            return round(numerator / denominator, 3) if denominator else 0.0

        return {
            "totals": {
                "total_played_games": total_games_completed,
                "total_users": total_users,
                "total_lobbies_created": total_lobbies_created,
                "total_games_started": total_games_started,
                "total_games_completed": total_games_completed,
                "total_games_abandoned": total_games_abandoned,
            },
            "conversion": {
                "lobby_to_game_start_rate": completion_rate(
                    total_games_started, total_lobbies_created
                ),
                "game_completion_rate": completion_rate(
                    total_games_completed, total_games_started
                ),
            },
            "recent": {
                "games_played_today": daily_completed.get(today_key, 0),
                "games_played_last_7_days": recent_games_played[7],
                "games_played_last_30_days": recent_games_played[30],
                "lobbies_created_today": daily_lobbies.get(today_key, 0),
                "lobbies_created_last_7_days": recent_lobbies_created[7],
                "lobbies_created_last_30_days": recent_lobbies_created[30],
                "new_users_last_7_days": recent_users[7],
                "new_users_last_30_days": recent_users[30],
                "returning_users_last_7_days": returning_users[7],
                "returning_users_last_30_days": returning_users[30],
            },
            "engagement": {
                "average_players_per_started_game": average(
                    [float(row["player_count"]) for row in started_games]
                ),
                "average_players_per_completed_game": average(
                    [float(row["player_count"]) for row in completed_games]
                ),
                "average_game_duration_seconds": int(round(average(durations))) if durations else 0,
                "median_game_duration_seconds": int(round(median(durations))) if durations else 0,
            },
            "activity": {
                "range_days": days,
                "daily_games_played": series(daily_completed),
                "daily_games_completed": series(daily_completed),
                "daily_lobbies_created": series(daily_lobbies),
                "daily_games_started": series(daily_started),
                "daily_new_users": series(daily_new_users),
            },
            "meta": {
                "generated_at": current.isoformat().replace("+00:00", "Z"),
                "timezone": "UTC",
                "is_public_endpoint": True,
                "linked_from_homepage": False,
            },
        }
