from abc import ABC, abstractmethod


class EventListener(ABC):
    def __init__(self) -> None:
        pass

    @abstractmethod
    def on_event(self, event) -> None:
        pass
