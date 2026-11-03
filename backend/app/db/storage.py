from __future__ import annotations

import asyncio
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from app.core.config import ROOT_DIR


DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "app.sqlite"
LOCK = asyncio.Lock()


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        legacy = conn.execute("PRAGMA table_info(tokens)").fetchall()
        if legacy and not any(column["name"] == "username" and column["pk"] for column in legacy):
            conn.executescript("ALTER TABLE tokens RENAME TO tokens_legacy")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS tokens (
                sead TEXT NOT NULL,
                username TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        if legacy and not any(column["name"] == "username" and column["pk"] for column in legacy):
            conn.execute(
                "INSERT OR IGNORE INTO tokens(username, user_id, sead, updated_at) SELECT username, user_id, sead, updated_at FROM tokens_legacy"
            )
            conn.execute("DROP TABLE tokens_legacy")


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def get_token(username: str) -> dict[str, Any] | None:
    with _connect() as conn:
        return _row_to_dict(conn.execute("SELECT * FROM tokens WHERE username = ?", (username,)).fetchone())


def save_token(user_id: str, sead: str, username: str) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO tokens(username, user_id, sead, updated_at)
            VALUES(?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(username) DO UPDATE SET
                user_id=excluded.user_id,
                sead=excluded.sead,
                updated_at=CURRENT_TIMESTAMP
            """,
            (username, user_id, sead),
        )


def delete_token(username: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM tokens WHERE username = ?", (username,))


def log_action(action: str, payload: dict[str, Any]) -> None:
    with _connect() as conn:
        conn.execute("INSERT INTO logs(action, payload) VALUES(?, ?)", (action, json.dumps(payload, ensure_ascii=False)))


def stats() -> dict[str, Any]:
    with _connect() as conn:
        token_count = conn.execute("SELECT COUNT(*) FROM tokens").fetchone()[0]
        return {"token_count": token_count}


def runtime_info() -> dict[str, Any]:
    return {"data_dir": str(DATA_DIR), "db_path": str(DB_PATH), "pid": os.getpid()}
