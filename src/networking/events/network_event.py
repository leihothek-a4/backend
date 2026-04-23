from dataclasses import dataclass

from ...prelude.events.event import Event


@dataclass
class NetworkEvent(Event):
    prev_state: str
    new_state: str
    reason: str

    def __post_init__(self):
        super().__init__(type="network_state_changed")
