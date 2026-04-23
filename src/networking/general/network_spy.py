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

        # if explained_new_state and explained_new_state.name in _DISCONNECT_STATES:
        if explained_new_state:
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
