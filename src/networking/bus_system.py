from ..prelude.system import System
from .dbus_context import DBusContextManager


class BusManager(System):
    def on_attach(self) -> None:
        DBusContextManager.init()

    def on_start(self) -> None:
        pass

    def on_detach(self) -> None:
        pass

    def on_update(self) -> None:
        context = DBusContextManager.get_context()
        while context.pending():  # type: ignore
            context.iteration(False)  # type: ignore
