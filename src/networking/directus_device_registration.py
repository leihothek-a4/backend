from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from loguru import logger

from ..prelude.app import App
from ..prelude.module import Module, module
from ..prelude.system import System
from .device_credentials import (
    get_or_create_device_uid,
    load_credentials,
    update_credentials,
)


def _env(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name)

    if v is None or str(v).strip() == "":
        return default

    return str(v).strip()


def _http_json(
    method: str, url: str, payload: dict | None = None
) -> tuple[int, dict | list | str | None]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None

    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method=method,
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")

            if not body:
                return resp.getcode() or 200, None

            try:
                return resp.getcode() or 200, json.loads(body)
            except json.JSONDecodeError:
                return resp.getcode() or 200, body

    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            body = str(e)

        try:
            parsed = json.loads(body) if body else None
        except json.JSONDecodeError:
            parsed = body

        return e.code, parsed

    except Exception as e:
        return -1, str(e)


def _post_register(base_url: str, payload: dict) -> tuple[int, dict | None]:
    code, body = _http_json("POST", base_url.rstrip("/") + "/devices/register", payload)

    return code, body if isinstance(body, dict) else None


def _get_registration_status(
    base_url: str,
    *,
    device_uid: str,
    pairing_token: str | None = None,
    device_secret: str | None = None,
) -> tuple[int, dict | None]:
    params: dict[str, str] = {"device_uid": device_uid}

    if device_secret:
        params["device_secret"] = device_secret

    elif pairing_token:
        params["pairing_token"] = pairing_token

    url = base_url.rstrip("/") + "/devices/status?" + urllib.parse.urlencode(params)

    code, body = _http_json("GET", url)

    return code, body if isinstance(body, dict) else None


def _persist_approval(status: dict[str, Any]) -> None:
    fields: dict[str, Any] = {}
    if status.get("locker_id"):
        fields["locker_id"] = status["locker_id"]
    if status.get("device_secret"):
        fields["device_secret"] = status["device_secret"]
        fields["pairing_token"] = None
    if fields:
        update_credentials(**fields)


class DirectusDeviceRegistrationSystem(System):
    """Register on start; reuse on-disk device_secret after operator approval."""

    def __init__(self) -> None:
        super().__init__(name="DirectusDeviceRegistration")

    def on_attach(self) -> None:
        pass

    def _registration_payload(self, device_uid: str) -> dict:

        hostname = socket.gethostname()

        payload: dict = {
            "device_uid": device_uid,
            "name": _env("LEIHOTHEK_DEVICE_NAME") or f"pi-{hostname}",
            "hostname": hostname,
            "firmware_version": _env("LEIHOTHEK_FIRMWARE_VERSION", "0.0.0"),
        }

        creds = load_credentials()

        secret = creds.get("device_secret")

        if isinstance(secret, str) and secret.strip():
            payload["device_secret"] = secret.strip()

        return payload

    def on_start(self) -> None:

        base_url = _env("LEIHOTHEK_DIRECTUS_URL", "http://127.0.0.1:8055")

        device_uid = get_or_create_device_uid()

        update_credentials(device_uid=device_uid, directus_url=base_url)

        creds = load_credentials()

        device_secret = creds.get("device_secret")

        pairing_token = creds.get("pairing_token")

        logger.info(
            "[leihothek] Directus registration at {} (device_uid={}, has_secret={})…",
            base_url,
            device_uid,
            bool(device_secret),
        )

        if isinstance(device_secret, str) and device_secret.strip():
            if self._try_reconnect(base_url, device_uid, device_secret.strip()):
                return

        if isinstance(pairing_token, str) and pairing_token.strip():
            if self._poll_until_approved(base_url, device_uid, pairing_token.strip()):
                return

        if not self._request_registration(base_url, device_uid):
            return

        creds = load_credentials()

        token = creds.get("pairing_token")

        if isinstance(token, str) and token.strip():
            self._poll_until_approved(base_url, device_uid, token.strip())

    def _try_reconnect(
        self, base_url: str, device_uid: str, device_secret: str
    ) -> bool:

        code, body = _post_register(base_url, self._registration_payload(device_uid))

        if code == 200 and body and body.get("approved"):
            locker_id = body.get("locker_id")

            logger.success(
                "[leihothek] Reconnected to Directus (locker_id={}, status={}).",
                locker_id,
                body.get("device", {}).get("status"),
            )

            _persist_approval(body)

            return True

        if code == 400:
            message = body.get("message") if isinstance(body, dict) else str(body)

            logger.warning(
                "[leihothek] Stored credentials rejected ({}); will request pairing again.",
                message,
            )

            update_credentials(device_secret=None, pairing_token=None)

        return False

    def _request_registration(self, base_url: str, device_uid: str) -> bool:
        deadline = time.monotonic() + 180.0

        while time.monotonic() < deadline:
            code, body = _post_register(
                base_url, self._registration_payload(device_uid)
            )

            if code == 200 and body:
                if body.get("approved"):
                    logger.success("[leihothek] Device already approved on Directus.")
                    _persist_approval(body)
                    return True

                token = body.get("pairing_token")

                if isinstance(token, str) and token:
                    update_credentials(pairing_token=token)
                    logger.success(
                        "[leihothek] Waiting for operator approval in the frontend…"
                    )

                    return True

            elif code == 400:
                message = body.get("message") if body else ""
                logger.error("[leihothek] Registration rejected: {}", message)
                return False

            detail = body.get("message") if isinstance(body, dict) else body
            logger.warning(
                "[leihothek] Registration attempt failed (HTTP {}): {} — retrying in 5s…",
                code,
                str(detail)[:300] if detail else "no response (is Directus reachable?)",
            )
            time.sleep(5)

        logger.error(
            "[leihothek] Could not register with Directus at {} after ~3 minutes.",
            base_url,
        )
        return False

    def _poll_until_approved(
        self, base_url: str, device_uid: str, pairing_token: str
    ) -> bool:
        logger.info("[leihothek] Polling for operator approval…")
        deadline = time.monotonic() + 3600.0
        poll_n = 0

        while time.monotonic() < deadline:
            poll_n += 1

            code, status = _get_registration_status(
                base_url,
                device_uid=device_uid,
                pairing_token=pairing_token,
            )

            if code == 200 and status and status.get("approved"):
                _persist_approval(status)

                logger.success(
                    "[leihothek] Approved (locker_id={}, status={}).",
                    status.get("locker_id"),
                    status.get("status"),
                )

                return True

            if code == 400:
                logger.error("[leihothek] Pairing token invalid — re-registering…")

                return False

            if poll_n == 1 or poll_n % 15 == 0:
                logger.info("[leihothek] Still waiting for approval (poll {})…", poll_n)

            time.sleep(4)

        logger.warning("[leihothek] Timed out waiting for approval (1 hour).")

        return False

    def on_detach(self) -> None:
        pass

    def on_update(self) -> None:
        pass


@module
class DirectusDeviceRegistrationModule(Module):
    def setup(self, app: App) -> None:
        app.register_system(DirectusDeviceRegistrationSystem())
