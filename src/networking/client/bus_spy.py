import dbus
import gi
from dbus.mainloop.glib import DBusGMainLoop

from ...prelude.system import System

gi.require_version("GLib", "2.0")

from gi.repository import GLib  # type: ignore


def _network_state_changed(
    new_state: dbus.UInt32, prev_state: dbus.UInt32, reason: dbus.UInt32
):
    print(
        "prev_state: {0}, new_state: {1}, reason: {2}".format(
            prev_state, new_state, reason
        )
    )


class BusSpy(System):
    def __init__(self) -> None:
        self.bus: dbus.SessionBus | None = None
        self.context: GLib.MainContext | None = None

    def on_attach(self) -> None:
        DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SessionBus()
        self.context = GLib.MainContext.default()

        self.bus.add_signal_receiver(
            _network_state_changed,
            signal_name="StateChanged",
            dbus_interface="org.freedesktop.NetworkManager",
        )

        print("[BusSpy] connected")

    def on_detach(self) -> None:
        pass

    def on_update(self) -> None:
        while self.context.pending():  # type: ignore
            self.context.iteration(False)  # type: ignore
