import src
from .networking.dbus_context import DBusContextManager
from .prelude import App
from .prelude.module import ModuleManager

if __name__ == "__main__":
    ModuleManager.discover(src)
    DBusContextManager.init()
    app = App()
    app._run()
