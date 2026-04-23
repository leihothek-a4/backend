from queue import Queue
from typing import Dict, List, Type

from .event import Event
from .listener import EventListener


class EventListenerManager:
    def __init__(self) -> None:
        self._listeners: List[EventListener] = []
        self._listening_types: Dict[EventListener, Type[Event]] = {}
        self._event_queue: Queue[Event] = Queue()

    def register(self, listener: EventListener) -> None:
        self._listeners.append(listener)

        listening_type = listener.on_event.__annotations__["event"]
        self._listening_types[listener] = listening_type
        
    def queue_event(self, event: Event) -> None:
        """
        Queue a event to be dispatched later
        """
        
        self._event_queue.put(event)

    def dispatch_events(self) -> None:
        """
        Dispatch all Queued events
        """
        while not self._event_queue.empty():
            event = self._event_queue.get()
            for listener in self._listeners:
                listener_type = self._listening_types.get(listener, Event)
                if isinstance(event, listener_type):
                    listener.on_event(event)
