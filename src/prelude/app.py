from __future__ import annotations

from typing import TYPE_CHECKING

from .events import Event, EventListener, EventListenerManager
from .module import ModuleManager
from .system import SystemManager

if TYPE_CHECKING:
    from .system import System


class App:
    def __init__(self) -> None:
        self.system_manager = SystemManager()
        self.event_manager = EventListenerManager()
        self.modules = ModuleManager.initialize_all(self)
        self.running = True

    def register_system(self, system: System) -> None:
        self.system_manager.register(system)

    def register_listener(self, listener: EventListener) -> None:
        self.event_manager.register(listener)

    def queue_event(self, event: Event) -> None:
        """
        Queue an event that will be dispatched when the systems are done running once(so when we run on_update once for all systems)
        """
        self.event_manager.queue_event(event)

    def _run(self) -> None:
        """
        only should be ran by entrypoint
        """
        try:
            while self.running:
                self.system_manager.run()
                self.event_manager.dispatch_events()
        except Exception as e:
            # we should use some better logging then this
            print(e)
            self.system_manager.detach()
        finally:
            self.system_manager.detach()
