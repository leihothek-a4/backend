from ...prelude.app import App
from ...prelude.module import Module, module
from .network_spy import NetworkSpy


# TODO: make sure this only gets added when we really are on the actual client
# We can make this work pretty smart by getting what type of pi it is at runtime via some kind of api we registered this pi at
@module
class NetworkMonitor(Module):
    def setup(self, app: App) -> None:
        app.register_system(NetworkSpy())
