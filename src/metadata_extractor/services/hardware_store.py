from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, List, TypedDict

from metadata_extractor.app.config import HARDWARE_DB_PATH


class HardwareItem(TypedDict, total=False):
    name: str
    url: str | None
    price: str | None
    source: str | None


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(HARDWARE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path | None = None) -> None:
    """
    Create the hardware table if it doesn't exist.
    """
    path = db_path or HARDWARE_DB_PATH
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS hardware_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                url TEXT,
                price TEXT,
                source TEXT,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def upsert_hardware(items: Iterable[HardwareItem]) -> int:
    """
    Insert new hardware rows, skipping duplicates by name. Returns count inserted.
    """
    inserted = 0
    with _get_connection() as conn:
        for item in items:
            try:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO hardware_items (name, url, price, source)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        item.get("name"),
                        item.get("url"),
                        item.get("price"),
                        item.get("source"),
                    ),
                )
                if conn.total_changes > inserted:
                    inserted += 1
            except sqlite3.Error:
                # Keep going even if a single row fails
                continue
        conn.commit()
    return inserted


def list_hardware(limit: int = 50) -> List[HardwareItem]:
    with _get_connection() as conn:
        cur = conn.execute(
            """
            SELECT name, url, price, source, discovered_at
            FROM hardware_items
            ORDER BY discovered_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]
