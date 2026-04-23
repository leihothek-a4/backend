from ..prelude.app import App
from ..prelude.module import Module, module
from .bus_system import BusManager
from .dbus_context import DBusContextManager


@module
class NetworkMonitor(Module):
    def setup(self, app: App) -> None:
        app.register_system(BusManager())
