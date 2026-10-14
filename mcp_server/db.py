"""SQLite helpers for the Campus Customs MCP server.

Always reads/writes `data/campus_customs_new.db` (working copy).
Never invent rows — only return what is in the database.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

# mcp_server/ -> HW 5/
HW5_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = HW5_ROOT / "data" / "campus_customs_new.db"


def connect() -> sqlite3.Connection:
    if not DB_PATH.is_file():
        raise FileNotFoundError(
            f"Working database not found: {DB_PATH}. "
            "Copy data/campus_customs.db to data/campus_customs_new.db first."
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [{key: row[key] for key in row.keys()} for row in rows]
