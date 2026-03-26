from ...prelude.app import App
from ...prelude.module import Module, module
from .bus_spy import BusSpy


@module
class NetworkMonitor(Module):
    def setup(self, app: App) -> None:
        app.register_system(BusSpy())


"""
context = GLib.MainContext.default()

while True:
    while context.pending():
        context.iteration(False)

    # Your non-blocking work here
"""
