from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType
from typing import TYPE_CHECKING, List, Type

from .module import Module

if TYPE_CHECKING:
    from ..app import App


class ModuleManager:
    _registry: List[Type[Module]] = []

    @classmethod
    def register(cls, module_cls: Type[Module]) -> None:
        cls._registry.append(module_cls)

    @classmethod
    def discover(cls, package: ModuleType) -> None:
        """Recursively import all submodules under a package to trigger @module registration."""
        for _importer, modname, _ispkg in pkgutil.walk_packages(
            package.__path__, package.__name__ + "."
        ):
            importlib.import_module(modname)

    @classmethod
    def initialize_all(cls, app: App) -> List[Module]:
        instances = []
        for module_cls in cls._registry:
            instance = module_cls()
            instance.setup(app)
            instances.append(instance)
        return instances

    @classmethod
    def get_modules(cls) -> List[Type[Module]]:
        return list(cls._registry)


def module(module_cls: Type[Module]) -> Type[Module]:
    """Decorator to register a Module class with the ModuleManager."""
    ModuleManager.register(module_cls)
    return module_cls
