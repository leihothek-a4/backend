# from __future__ import annotations

from typing import List

from .system import System


class SystemManager:
    def __init__(self) -> None:
        self._systems: List[System] = []

    def register(self, system: System) -> None:
        self._systems.append(system)
        system.on_attach()

    def start(self) -> None:
        for system in self._systems:
            system.on_start()

    def run(self) -> None:
        for system in self._systems:
            system.on_update()

    def detach(self) -> None:
        for system in self._systems:
            system.on_detach()
