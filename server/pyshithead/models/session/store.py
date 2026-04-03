from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

DEFAULT_DATABASE_URL = "sqlite:///./shithead.db"


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

    def clear_all(self):
        with self._connect() as connection:
            connection.execute("DELETE FROM session_players")
            connection.execute("DELETE FROM game_sessions")

    def mark_all_players_disconnected(self):
        with self._connect() as connection:
            connection.execute("UPDATE session_players SET connected = 0")

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
