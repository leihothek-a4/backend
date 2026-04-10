import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class NMDeviceState(BaseModel):
    name: str
    value: int
    description: str


class NMDeviceStateReason(BaseModel):
    name: str
    value: int
    description: str


class NMConstants(BaseModel):
    device_states: list[NMDeviceState] = Field(alias="NMDeviceState")
    state_reasons: list[NMDeviceStateReason] = Field(alias="NMDeviceStateReason")


class NMConstantsStorage:
    _instance: Optional[NMConstants] = None
    _reason_map: Optional[dict[int, NMDeviceStateReason]] = None
    _state_map: Optional[dict[int, NMDeviceState]] = None
    _file_path: Path = Path(__file__).parent / "nm_constants.json"

    @classmethod
    def _load(cls) -> NMConstants:
        with cls._file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        constants = NMConstants(**data)

        cls._reason_map = {r.value: r for r in constants.state_reasons}
        cls._state_map = {s.value: s for s in constants.device_states}

        return constants

    @classmethod
    def _ensure_loaded(cls):
        if cls._instance is None:
            cls._instance = cls._load()

    @classmethod
    def get_device_state_by_value(cls, value: int) -> NMDeviceState | None:
        cls._ensure_loaded()
        return cls._state_map.get(value)  # type: ignore (we are ensured that _state_map is loaded here)

    @classmethod
    def get_state_reason_by_value(cls, value: int) -> NMDeviceStateReason | None:
        cls._ensure_loaded()
        return cls._reason_map.get(value)  # type: ignore (we are ensured that _reason_map is loaded here)
