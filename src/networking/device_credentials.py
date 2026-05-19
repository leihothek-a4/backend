from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger

_ROW_ID = 1
_COLUMNS = (
    "device_uid",
    "directus_url",
    "pairing_token",
    "device_secret",
    "locker_id",
)


def _env(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name)
    if v is None or str(v).strip() == "":
        return default
    return str(v).strip()


def credentials_db_path() -> Path:
    override = _env("LEIHOTHEK_CREDENTIALS_DB") or _env("LEIHOTHEK_CREDENTIALS_FILE")
    if override:
        path = Path(override).expanduser()
        if path.suffix.lower() == ".json":
            return path.with_suffix(".db")
        return path
    for candidate in (
        Path("/var/lib/leihothek/device.db"),
        Path.home() / ".leihothek" / "device.db",
    ):
        if candidate.parent == Path("/var/lib/leihothek") and not candidate.parent.exists():
            continue
        return candidate
    return Path.home() / ".leihothek" / "device.db"


def _legacy_json_path(db_path: Path) -> Path | None:
    if db_path.with_suffix(".json").is_file():
        return db_path.with_suffix(".json")
    legacy = Path.home() / ".leihothek" / "device.json"
    if legacy.is_file():
        return legacy
    return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    path = credentials_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS device_credentials (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            device_uid TEXT,
            directus_url TEXT,
            pairing_token TEXT,
            device_secret TEXT,
            locker_id TEXT,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return conn


def _migrate_json_if_needed(conn: sqlite3.Connection) -> None:
    row = conn.execute(
        "SELECT device_uid FROM device_credentials WHERE id = ?", (_ROW_ID,)
    ).fetchone()
    if row and row["device_uid"]:
        return

    json_path = _legacy_json_path(credentials_db_path())
    if not json_path:
        return

    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("[leihothek] Could not migrate {}: {}", json_path, e)
        return

    if not isinstance(data, dict) or not data.get("device_uid"):
        return

    save_credentials(data)
    logger.info("[leihothek] Migrated credentials from {} to SQLite", json_path)


def load_credentials() -> dict[str, Any]:
    with _connect() as conn:
        _migrate_json_if_needed(conn)
        row = conn.execute(
            "SELECT device_uid, directus_url, pairing_token, device_secret, locker_id "
            "FROM device_credentials WHERE id = ?",
            (_ROW_ID,),
        ).fetchone()

    if not row:
        return {}

    return {key: row[key] for key in _COLUMNS if row[key] is not None}


def save_credentials(data: dict[str, Any]) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO device_credentials (
                id, device_uid, directus_url, pairing_token, device_secret, locker_id, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                device_uid = excluded.device_uid,
                directus_url = excluded.directus_url,
                pairing_token = excluded.pairing_token,
                device_secret = excluded.device_secret,
                locker_id = excluded.locker_id,
                updated_at = excluded.updated_at
            """,
            (
                _ROW_ID,
                data.get("device_uid"),
                data.get("directus_url"),
                data.get("pairing_token"),
                data.get("device_secret"),
                data.get("locker_id"),
                _now_iso(),
            ),
        )
        conn.commit()

    logger.debug("[leihothek] Saved device credentials to {}", credentials_db_path())


def get_or_create_device_uid() -> str:
    creds = load_credentials()
    uid = str(creds.get("device_uid") or "").strip()
    if uid:
        return uid

    uid = str(uuid.uuid4())
    update_credentials(device_uid=uid)
    logger.info("[leihothek] Generated new device_uid={}", uid)
    return uid


def update_credentials(**fields: Any) -> dict[str, Any]:
    creds = load_credentials()
    for key, value in fields.items():
        if value is None:
            creds.pop(key, None)
        else:
            creds[key] = value
    save_credentials(creds)
    return creds
