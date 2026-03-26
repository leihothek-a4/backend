import dbus
from loguru import logger

from ...prelude.system import System
from ..dbus_context import DBusContextManager
from .data.nm_constants import NMConstantsStorage


class NetworkSpy(System):
    @staticmethod
    def _network_state_changed(
        new_state: dbus.UInt32, prev_state: dbus.UInt32, reason: dbus.UInt32
    ):
        explained_prev_state = NMConstantsStorage.get_device_state_by_value(prev_state)
        explained_new_state = NMConstantsStorage.get_device_state_by_value(new_state)
        explained_reason = NMConstantsStorage.get_state_reason_by_value(reason)

        logger.info(
            "prev_state: {0}, new_state: {1}, reason: {2}".format(
                explained_prev_state.name,  # type: ignore
                explained_new_state.name,  # type: ignore
                explained_reason.description,  # type: ignore
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
