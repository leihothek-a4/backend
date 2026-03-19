import src
from .prelude import App
from .prelude.module import ModuleManager

if __name__ == "__main__":
    ModuleManager.discover(src)
    app = App()
    app._run()
