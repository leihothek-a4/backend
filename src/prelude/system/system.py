from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from events.event import Event


class System(ABC):
    def __init__(self, name="System"):
        self.name = name

    @abstractmethod
    def on_attach(self):
        """
        Called when the system is added to the app.
        """
        pass

    @abstractmethod
    def on_start(self):
        """
        Called after all of the modules are initialized and all on_attach are called
        """
        pass

    @abstractmethod
    def on_detach(self):
        """
        Clean up resources whenever the system is removed
        """
        pass

    @abstractmethod
    def on_update(self):
        """Called on every update"""
        pass
