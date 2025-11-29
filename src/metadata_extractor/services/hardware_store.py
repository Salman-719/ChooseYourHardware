from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, TypedDict

from config.settings import get_settings
from metadata_extractor.services.hardware_models import HardwareRecord

logger = logging.getLogger(__name__)

settings = get_settings()
DEVICE_DATA_DIR = settings.base_dir / "device_data"
DEVICE_DATA_DIR.mkdir(parents=True, exist_ok=True)


class HardwareItem(TypedDict, total=False):
    hardware_id: str
    kind: str
    vendor: str
    model_name: str
    spec: dict
    url: str | None
    price: str | None
    source: str | None
    discovered_at: str | None


def _hardware_path(record: HardwareRecord) -> Path:
    filename = f"{record.hardware_id}.json"
    return DEVICE_DATA_DIR / filename


def upsert_hardware(items: Iterable[HardwareItem]) -> int:
    """
    Write hardware records to device_data as JSON files.
    Returns the count of newly created files (existing files are overwritten but not counted).
    """
    inserted = 0
    for item in items:
        record = HardwareRecord.model_validate(item)
        path = _hardware_path(record)
        was_new = not path.exists()
        payload = {
            "hardware_id": record.hardware_id,
            "kind": record.kind,
            "vendor": record.vendor,
            "model_name": record.model_name,
            "spec": record.spec,
            "url": record.url,
            "price": record.price,
            "source": record.source,
            "discovered_at": getattr(record, "discovered_at", None)
            or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        }
        try:
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            if was_new:
                inserted += 1
                logger.info("Wrote new hardware file %s", path.name)
            else:
                logger.debug("Updated existing hardware file %s", path.name)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to write hardware file %s: %s", path, exc)
            continue
    return inserted


def list_hardware(limit: int = 50) -> List[HardwareItem]:
    """
    Read hardware definitions from the device_data directory.
    """
    items: List[HardwareItem] = []
    for path in sorted(DEVICE_DATA_DIR.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            record = HardwareRecord.model_validate(raw)
            payload: HardwareItem = {
                "hardware_id": record.hardware_id,
                "kind": record.kind,
                "vendor": record.vendor,
                "model_name": record.model_name,
                "spec": record.spec,
                "url": record.url,
                "price": record.price,
                "source": record.source,
                "discovered_at": raw.get("discovered_at") if isinstance(raw, dict) else None,
            }
            items.append(payload)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Skipping invalid hardware file %s: %s", path, exc)
            continue

    def _sort_key(item: HardwareItem):
        ts = item.get("discovered_at")
        if isinstance(ts, str):
            try:
                return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            except Exception:
                return datetime.min
        try:
            return datetime.fromtimestamp((DEVICE_DATA_DIR / f"{item.get('hardware_id')}.json").stat().st_mtime)
        except Exception:
            return datetime.min

    items_sorted = sorted(items, key=_sort_key, reverse=True)
    return items_sorted[:limit]
