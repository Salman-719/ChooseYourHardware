from __future__ import annotations

import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Iterable, List, TypedDict

from metadata_extractor.services.hardware_models import HardwareRecord

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent


def _get_db_path() -> Path:
    env_path = os.getenv("HARDWARE_DB_PATH")
    path = Path(env_path) if env_path else (BASE_DIR / "hardware.db")
    if not path.is_absolute():
        path = BASE_DIR / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


HARDWARE_DB_PATH = _get_db_path()


class HardwareItem(TypedDict, total=False):
    hardware_id: str
    kind: str
    vendor: str
    model_name: str
    spec: dict
    url: str | None
    price: str | None
    source: str | None


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(HARDWARE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path | None = None) -> None:
    """
    Create or refresh the hardware table if it doesn't match the expected schema.
    """
    path = db_path or HARDWARE_DB_PATH
    expected_columns = {
        "id",
        "hardware_id",
        "kind",
        "vendor",
        "model_name",
        "spec_json",
        "url",
        "price",
        "source",
        "discovered_at",
    }

    with sqlite3.connect(path) as conn:
        cur = conn.execute("PRAGMA table_info(hardware_items)")
        existing_columns = {row[1] for row in cur.fetchall()}
        if existing_columns and existing_columns != expected_columns:
            logger.warning("Recreating hardware_items table to match expected schema")
            conn.execute("DROP TABLE IF EXISTS hardware_items")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS hardware_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hardware_id TEXT UNIQUE,
                kind TEXT,
                vendor TEXT,
                model_name TEXT,
                spec_json TEXT,
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
    Insert new hardware rows, skipping duplicates by hardware_id. Returns count inserted.
    """
    init_db()
    inserted = 0
    with _get_connection() as conn:
        for item in items:
            record = HardwareRecord.model_validate(item)
            spec_json = json.dumps(record.spec)
            try:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO hardware_items (
                        hardware_id, kind, vendor, model_name, spec_json, url, price, source
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.hardware_id,
                        record.kind,
                        record.vendor,
                        record.model_name,
                        spec_json,
                        record.url,
                        record.price,
                        record.source,
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
    init_db()
    with _get_connection() as conn:
        cur = conn.execute(
            """
            SELECT hardware_id, kind, vendor, model_name, spec_json, url, price, source, discovered_at
            FROM hardware_items
            ORDER BY discovered_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = []
        for row in cur.fetchall():
            spec_json = row["spec_json"] or "{}"
            try:
                spec = json.loads(spec_json)
            except json.JSONDecodeError:
                spec = {}
            rows.append(
                {
                    "hardware_id": row["hardware_id"],
                    "kind": row["kind"],
                    "vendor": row["vendor"],
                    "model_name": row["model_name"],
                    "spec": spec,
                    "url": row["url"],
                    "price": row["price"],
                    "source": row["source"],
                    "discovered_at": row["discovered_at"],
                }
            )
        return rows
