"""
On startup, optionally register this unit (e.g. Raspberry Pi) with the Leihothek Directus `/devices/register` API.

Configure with environment variables (e.g. in a systemd unit or `.env` on the Pi):

- ``LEIHOTHEK_LOCKER_ID`` — hex locker id used by the lock firmware (required to enable registration)
- ``LEIHOTHEK_DIRECTUS_URL`` — Directus base URL (default: ``http://127.0.0.1:8055``)
- ``LEIHOTHEK_DEVICE_NAME`` — optional display name (default: ``pi-<hostname>``)
- ``LEIHOTHEK_FIRMWARE_VERSION`` — optional string (default: ``0.0.0``)
"""

from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.request

from loguru import logger

from ..prelude.app import App
from ..prelude.module import Module, module
from ..prelude.system import System


def _env(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name)
    if v is None or str(v).strip() == "":
        return default
    return str(v).strip()


def _post_register(base_url: str, payload: dict) -> tuple[int, str]:
    url = base_url.rstrip("/") + "/devices/register"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.getcode() or 200, body
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            body = str(e)
        return e.code, body
    except Exception as e:
        return -1, str(e)


def _get_list(base_url: str) -> tuple[int, list | None]:
    url = base_url.rstrip("/") + "/devices/list"
    req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            parsed = json.loads(raw)
            return resp.getcode() or 200, parsed if isinstance(parsed, list) else None
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return -1, None


class DirectusDeviceRegistrationSystem(System):
    """Runs once in ``on_start``: POST register, then poll ``/devices/list`` until this locker appears."""

    def __init__(self) -> None:
        super().__init__(name="DirectusDeviceRegistration")

    def on_attach(self) -> None:
        pass

    def on_start(self) -> None:
        locker_id = _env("LEIHOTHEK_LOCKER_ID")
        base_url = _env("LEIHOTHEK_DIRECTUS_URL", "http://127.0.0.1:8055")
        if not locker_id:
            logger.info(
                "[leihothek] LEIHOTHEK_LOCKER_ID is not set — skipping Directus self-registration "
                "(export LEIHOTHEK_LOCKER_ID and LEIHOTHEK_DIRECTUS_URL on the Pi to enable).",
            )
            return

        hostname = socket.gethostname()
        display_name = _env("LEIHOTHEK_DEVICE_NAME") or f"pi-{hostname}"
        firmware = _env("LEIHOTHEK_FIRMWARE_VERSION", "0.0.0")

        payload = {
            "locker_id": locker_id,
            "name": display_name,
            "hostname": hostname,
            "firmware_version": firmware,
        }

        logger.info(
            "[leihothek] Waiting to register with Directus at {} (locker_id={})…",
            base_url,
            locker_id,
        )

        register_deadline = time.monotonic() + 180.0
        attempt = 0
        registered = False
        while time.monotonic() < register_deadline:
            attempt += 1
            logger.info(
                "[leihothek] Registration attempt {} — POST /devices/register …",
                attempt,
            )
            code, body = _post_register(base_url, payload)
            if code == 200:
                logger.success("[leihothek] Directus accepted the registration payload (HTTP 200).")
                registered = True
                break
            if code == 400 and "locker_id is required" in body:
                logger.error("[leihothek] Registration rejected: {}", body[:500])
                return
            logger.warning(
                "[leihothek] Registration not accepted yet (HTTP {}): {} — waiting 5s before retry…",
                code,
                body[:300] if body else "",
            )
            logger.info(
                "[leihothek] Still waiting to be fully registered with Directus (not accepted or server unreachable)…",
            )
            time.sleep(5)

        if not registered:
            logger.error(
                "[leihothek] Stopped trying to register with Directus after ~3 minutes; "
                "the app will continue without server-side device registration.",
            )
            return

        logger.info(
            "[leihothek] Waiting until this device appears on the server device list (fully registered)…",
        )
        poll_deadline = time.monotonic() + 90.0
        poll_n = 0
        lid_lower = locker_id.lower()
        while time.monotonic() < poll_deadline:
            poll_n += 1
            code, devices = _get_list(base_url)
            if code == 200 and devices:
                for row in devices:
                    if not isinstance(row, dict):
                        continue
                    if str(row.get("locker_id", "")).lower() == lid_lower:
                        logger.success(
                            "[leihothek] Fully registered on Directus (id={}, status={}, transport={}).",
                            row.get("id"),
                            row.get("status"),
                            row.get("transport"),
                        )
                        return
            logger.info(
                "[leihothek] Registered with Directus but list does not show this locker yet "
                "(poll {}) — waiting 2s…",
                poll_n,
            )
            time.sleep(2)

        logger.warning(
            "[leihothek] POST succeeded but /devices/list never showed locker_id={} within timeout — "
            "check Directus logs.",
            locker_id,
        )

    def on_detach(self) -> None:
        pass

    def on_update(self) -> None:
        pass


@module
class DirectusDeviceRegistrationModule(Module):
    def setup(self, app: App) -> None:
        app.register_system(DirectusDeviceRegistrationSystem())
