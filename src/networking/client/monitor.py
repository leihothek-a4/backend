from ...prelude.app import App
from ...prelude.module import Module, module
from .bluetooth_client import BluetoothClient


@module
class BluetoothClientMonitor(Module):
    def setup(self, app: App) -> None:
        client = BluetoothClient()
        app.register_system(client)
        app.register_listener(client)
