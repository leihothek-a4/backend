from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from events.event import Event


class System(ABC):
    def __init__(self, name="System"):
        self.name = name
        self._update_handlers: list[tuple[int, Callable]] = []
        self._event_handlers: list[tuple[int, str, Callable]] = []

    @abstractmethod
    def on_attach(self):
        """
        Called when the system is added to the app.
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
        """Calls all registered `@system` update methods in stage order."""
        for _, handler in self._update_handlers:
            handler()
