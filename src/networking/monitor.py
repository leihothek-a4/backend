from ..prelude.app import App
from ..prelude.module import Module, module
from .bluetooth_manager import BluetoothManager


@module
class BluetoothMonitor(Module):
    def setup(self, app: App) -> None:
        manager = BluetoothManager()
        app.register_system(manager)
        app.register_listener(manager)
