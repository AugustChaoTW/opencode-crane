from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class EventType(Enum):
    PROCESSING = "processing"
    TOOL_CALL = "tool_call"
    APPROVAL_REQUIRED = "approval_required"
    ERROR = "error"
    SUCCESS = "success"


@dataclass
class Event:
    type: EventType
    data: dict[str, Any]
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


class EventSystem:
    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.history: list[Event] = []

    def emit(self, event_type: str, data: dict[str, Any]) -> Event:
        try:
            et = EventType(event_type)
        except ValueError:
            et = EventType.PROCESSING

        event = Event(type=et, data=data)
        self.history.append(event)

        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history :]

        return event

    def get_events(self, event_type: EventType | None = None) -> list[Event]:
        if event_type is None:
            return list(self.history)
        return [e for e in self.history if e.type == event_type]

    def clear_history(self) -> None:
        self.history.clear()