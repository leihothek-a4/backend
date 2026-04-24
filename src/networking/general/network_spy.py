import subprocess
import threading
import time

import dbus
from loguru import logger

from ...prelude.app import App
from ...prelude.system import System
from ..dbus_context import DBusContextManager
from ..events.network_event import NetworkEvent
from .data.nm_constants import NMConstantsStorage

_DISCONNECT_STATES = {
    "NM_DEVICE_STATE_DISCONNECTED",
    "NM_DEVICE_STATE_UNAVAILABLE",
    "NM_DEVICE_STATE_FAILED",
}


class NetworkSpy(System):
    def __init__(self, app: App) -> None:
        super().__init__(name="NetworkSpy")
        self._app = app
        self._last_recovery_at: float = 0.0
        self._recovery_cooldown_seconds = 30.0
        self._recovery_lock = threading.Lock()

    def _network_state_changed(
        self, new_state: dbus.UInt32, prev_state: dbus.UInt32, reason: dbus.UInt32
    ) -> None:
        explained_prev_state = NMConstantsStorage.get_device_state_by_value(prev_state)
        explained_new_state = NMConstantsStorage.get_device_state_by_value(new_state)
        explained_reason = NMConstantsStorage.get_state_reason_by_value(reason)

        logger.info(
            "prev_state: {0}, new_state: {1}, reason: {2}".format(
                explained_prev_state.description,  # type: ignore
                explained_new_state.description,  # type: ignore
                explained_reason.description,  # type: ignore
            )
        )

        if explained_new_state and explained_new_state.name in _DISCONNECT_STATES:
            self._app.queue_event(
                NetworkEvent(
                    prev_state=explained_prev_state.description
                    if explained_prev_state
                    else str(prev_state),  # type: ignore
                    new_state=explained_new_state.description,
                    reason=explained_reason.description
                    if explained_reason
                    else str(reason),  # type: ignore
                )
            )
            self._maybe_recover_network_manager(
                explained_new_state.description,
                explained_reason.description if explained_reason else str(reason),  # type: ignore
            )

    def _maybe_recover_network_manager(self, new_state: str, reason: str) -> None:
        now = time.monotonic()
        with self._recovery_lock:
            if now - self._last_recovery_at < self._recovery_cooldown_seconds:
                logger.debug("Skipping recovery: cooldown still active.")
                return
            self._last_recovery_at = now

        logger.warning(
            f"Wi-Fi appears disconnected ({new_state}, {reason}) - resetting NetworkManager."
        )
        threading.Thread(target=self._reset_network_manager, daemon=True).start()

    def _run_command(self, command: list[str]) -> bool:
        try:
            completed = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=20,
            )
            if completed.stdout:
                logger.debug(f"{' '.join(command)} -> {completed.stdout.strip()}")
            return True
        except FileNotFoundError:
            logger.warning(f"Command not found: {' '.join(command)}")
            return False
        except subprocess.CalledProcessError as error:
            stderr = error.stderr.strip() if error.stderr else "no stderr"
            logger.warning(f"Command failed ({' '.join(command)}): {stderr}")
            return False
        except subprocess.TimeoutExpired:
            logger.warning(f"Command timed out: {' '.join(command)}")
            return False

    def _reset_network_manager(self) -> None:
        # Prefer nmcli toggle to avoid requiring service manager specific privileges.
        toggled = self._run_command(["nmcli", "networking", "off"]) and self._run_command(
            ["nmcli", "networking", "on"]
        )
        if toggled:
            logger.info("NetworkManager reset via nmcli networking toggle.")
            return

        # Fallback for images where nmcli is unavailable or not authorized.
        restarted = self._run_command(["systemctl", "restart", "NetworkManager"])
        if restarted:
            logger.info("NetworkManager restarted via systemctl.")
            return

        logger.error("Failed to reset NetworkManager with available recovery commands.")

    def on_attach(self) -> None:
        pass

    def on_start(self) -> None:
        DBusContextManager.add_signal_receiver(
            self._network_state_changed,
            signal_name="StateChanged",
            dbus_interface="org.freedesktop.NetworkManager.Device",
            path="/org/freedesktop/NetworkManager/Devices/1",
        )

    def on_detach(self) -> None:
        pass

    def on_update(self) -> None:
        pass
