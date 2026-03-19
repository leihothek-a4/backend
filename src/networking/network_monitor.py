from ..prelude.app import App
from ..prelude.module import Module, module


@module
class NetworkMonitor(Module):
    def setup(self, app: App) -> None:
        print("Registered network module!")
