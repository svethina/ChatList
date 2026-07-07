"""Доступ к SQLite для ChatList."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator, Iterable

DEFAULT_DB_PATH = "chatlist.db"

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS prompts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT    NOT NULL,
    prompt      TEXT    NOT NULL,
    tags        TEXT
);

CREATE INDEX IF NOT EXISTS idx_prompts_created_at ON prompts (created_at);

CREATE TABLE IF NOT EXISTS models (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    api_url     TEXT    NOT NULL,
    api_id      TEXT    NOT NULL,
    api_key_env TEXT    NOT NULL,
    is_active   INTEGER NOT NULL DEFAULT 1,
    provider    TEXT
);

CREATE INDEX IF NOT EXISTS idx_models_is_active ON models (is_active);

CREATE TABLE IF NOT EXISTS results (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_id     INTEGER NOT NULL,
    model_id      INTEGER NOT NULL,
    response_text TEXT    NOT NULL,
    created_at    TEXT    NOT NULL,
    FOREIGN KEY (prompt_id) REFERENCES prompts (id) ON DELETE RESTRICT,
    FOREIGN KEY (model_id)  REFERENCES models (id)  ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_results_prompt_id  ON results (prompt_id);
CREATE INDEX IF NOT EXISTS idx_results_model_id   ON results (model_id);
CREATE INDEX IF NOT EXISTS idx_results_created_at ON results (created_at);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

SEED_MODELS: list[dict[str, Any]] = [
    {
        "name": "OpenRouter GPT-4o mini",
        "api_url": "https://openrouter.ai/api/v1/chat/completions",
        "api_id": "openai/gpt-4o-mini",
        "api_key_env": "OPENROUTER_API_KEY",
        "is_active": 0,
        "provider": "openrouter",
    },
    {
        "name": "Tencent Hy3",
        "api_url": "https://openrouter.ai/api/v1/chat/completions",
        "api_id": "tencent/hy3-preview",
        "api_key_env": "OPENROUTER_API_KEY",
        "is_active": 0,
        "provider": "openrouter",
    },
    {
        "name": "GPT-4o",
        "api_url": "https://api.openai.com/v1/chat/completions",
        "api_id": "gpt-4o",
        "api_key_env": "OPENAI_API_KEY",
        "is_active": 0,
        "provider": "openai",
    },
    {
        "name": "DeepSeek Chat",
        "api_url": "https://api.deepseek.com/v1/chat/completions",
        "api_id": "deepseek-chat",
        "api_key_env": "DEEPSEEK_API_KEY",
        "is_active": 0,
        "provider": "deepseek",
    },
]

DEFAULT_SETTINGS: dict[str, str] = {
    "request_timeout": "60",
    "db_path": DEFAULT_DB_PATH,
    "log_requests": "1",
    "log_file": "chatlist.log",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


@contextmanager
def get_connection(db_path: str | None = None) -> Generator[sqlite3.Connection, None, None]:
    path = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: str | None = None) -> None:
    path = db_path or DEFAULT_DB_PATH
    with get_connection(path) as conn:
        conn.executescript(SCHEMA_SQL)
    seed_defaults(db_path=path)
    activate_models_with_keys(db_path=path)


def seed_defaults(db_path: str | None = None) -> None:
    with get_connection(db_path) as conn:
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )
        for model in SEED_MODELS:
            conn.execute(
                """
                INSERT OR IGNORE INTO models
                    (name, api_url, api_id, api_key_env, is_active, provider)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    model["name"],
                    model["api_url"],
                    model["api_id"],
                    model["api_key_env"],
                    model["is_active"],
                    model["provider"],
                ),
            )


# --- prompts ---


def add_prompt(prompt: str, tags: str | None = None, db_path: str | None = None) -> int:
    created_at = utc_now_iso()
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO prompts (created_at, prompt, tags) VALUES (?, ?, ?)",
            (created_at, prompt, tags or None),
        )
        return int(cursor.lastrowid)


def list_prompts(db_path: str | None = None) -> list[dict[str, Any]]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM prompts ORDER BY created_at DESC"
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def search_prompts(
    query: str,
    db_path: str | None = None,
) -> list[dict[str, Any]]:
    pattern = f"%{query}%"
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT * FROM prompts
            WHERE prompt LIKE ? OR IFNULL(tags, '') LIKE ?
            ORDER BY created_at DESC
            """,
            (pattern, pattern),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_prompt(prompt_id: int, db_path: str | None = None) -> dict[str, Any] | None:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM prompts WHERE id = ?",
            (prompt_id,),
        ).fetchone()
    return _row_to_dict(row) if row else None


# --- models ---


def add_model(
    name: str,
    api_url: str,
    api_id: str,
    api_key_env: str,
    is_active: bool = True,
    provider: str | None = None,
    db_path: str | None = None,
) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO models
                (name, api_url, api_id, api_key_env, is_active, provider)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, api_url, api_id, api_key_env, int(is_active), provider),
        )
        return int(cursor.lastrowid)


def update_model(model_id: int, **fields: Any) -> None:
    allowed = {"name", "api_url", "api_id", "api_key_env", "is_active", "provider"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    if "is_active" in updates:
        updates["is_active"] = int(updates["is_active"])
    columns = ", ".join(f"{key} = ?" for key in updates)
    values = list(updates.values()) + [model_id]
    with get_connection() as conn:
        conn.execute(f"UPDATE models SET {columns} WHERE id = ?", values)


def delete_model(model_id: int, db_path: str | None = None) -> None:
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM models WHERE id = ?", (model_id,))


def get_model(model_id: int, db_path: str | None = None) -> dict[str, Any] | None:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM models WHERE id = ?",
            (model_id,),
        ).fetchone()
    return _row_to_dict(row) if row else None


def list_models(
    active_only: bool = False,
    db_path: str | None = None,
) -> list[dict[str, Any]]:
    query = "SELECT * FROM models"
    params: tuple[Any, ...] = ()
    if active_only:
        query += " WHERE is_active = 1"
    query += " ORDER BY name"
    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(row) for row in rows]


def search_models(
    query: str,
    db_path: str | None = None,
) -> list[dict[str, Any]]:
    pattern = f"%{query}%"
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT * FROM models
            WHERE name LIKE ?
               OR api_url LIKE ?
               OR api_id LIKE ?
               OR IFNULL(provider, '') LIKE ?
            ORDER BY name
            """,
            (pattern, pattern, pattern, pattern),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def activate_models_with_keys(db_path: str | None = None) -> None:
    """Активирует модели, для которых задан API-ключ в окружении."""
    import os

    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT id, api_key_env FROM models").fetchall()
        for row in rows:
            if os.getenv(row["api_key_env"]):
                conn.execute(
                    "UPDATE models SET is_active = 1 WHERE id = ?",
                    (row["id"],),
                )


# --- results ---


def insert_results(
    rows: Iterable[dict[str, Any]],
    db_path: str | None = None,
) -> int:
    created_at = utc_now_iso()
    data = [
        (
            row["prompt_id"],
            row["model_id"],
            row["response_text"],
            row.get("created_at", created_at),
        )
        for row in rows
    ]
    if not data:
        return 0
    with get_connection(db_path) as conn:
        conn.executemany(
            """
            INSERT INTO results (prompt_id, model_id, response_text, created_at)
            VALUES (?, ?, ?, ?)
            """,
            data,
        )
    return len(data)


def list_results(db_path: str | None = None) -> list[dict[str, Any]]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                r.id,
                r.prompt_id,
                r.model_id,
                r.response_text,
                r.created_at,
                p.prompt AS prompt_text,
                m.name AS model_name
            FROM results r
            JOIN prompts p ON p.id = r.prompt_id
            JOIN models m ON m.id = r.model_id
            ORDER BY r.created_at DESC
            """
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def search_results(
    query: str,
    db_path: str | None = None,
) -> list[dict[str, Any]]:
    pattern = f"%{query}%"
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                r.id,
                r.prompt_id,
                r.model_id,
                r.response_text,
                r.created_at,
                p.prompt AS prompt_text,
                m.name AS model_name
            FROM results r
            JOIN prompts p ON p.id = r.prompt_id
            JOIN models m ON m.id = r.model_id
            WHERE r.response_text LIKE ?
               OR p.prompt LIKE ?
               OR m.name LIKE ?
            ORDER BY r.created_at DESC
            """,
            (pattern, pattern, pattern),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


# --- settings ---


def get_setting(key: str, db_path: str | None = None) -> str | None:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?",
            (key,),
        ).fetchone()
    return row["value"] if row else None


def set_setting(key: str, value: str, db_path: str | None = None) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )


def list_settings(db_path: str | None = None) -> list[dict[str, str]]:
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT key, value FROM settings ORDER BY key").fetchall()
    return [{"key": row["key"], "value": row["value"]} for row in rows]
