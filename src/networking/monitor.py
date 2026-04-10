from ..prelude.app import App
from ..prelude.module import Module, module


@module
class BluetoothMonitor(Module):
    def setup(self, app: App) -> None:
        pass  # BluetoothServer disabled (D-Bus policy not configured)
