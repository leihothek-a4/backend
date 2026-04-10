from ...prelude.app import App
from ...prelude.module import Module, module
from .bluetooth_server import BluetoothServer


@module
class BluetoothMonitor(Module):
    def setup(self, app: App) -> None:
        app.register_system(BluetoothServer())
