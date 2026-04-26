"""Tests for Event System service - crane_emit_event (#101)"""
import pytest
from crane.services.event_system import EventSystem, Event, EventType


class TestEventSystem:
    def test_default_event_types(self):
        events = EventSystem()
        assert EventType.PROCESSING.value in [e.value for e in EventType]
        assert EventType.TOOL_CALL.value in [e.value for e in EventType]

    def test_emit_processing_event(self):
        events = EventSystem()
        event = events.emit("processing", {"task": "search papers"})
        assert event.type == EventType.PROCESSING
        assert event.data["task"] == "search papers"

    def test_emit_tool_call_event(self):
        events = EventSystem()
        event = events.emit("tool_call", {"tool": "search_papers"})
        assert event.type == EventType.TOOL_CALL
        assert event.data["tool"] == "search_papers"

    def test_emit_approval_required_event(self):
        events = EventSystem()
        event = events.emit("approval_required", {"action": "delete"})
        assert event.type == EventType.APPROVAL_REQUIRED

    def test_event_has_timestamp(self):
        events = EventSystem()
        event = events.emit("processing", {"task": "test"})
        assert event.timestamp > 0

    def test_event_history_tracked(self):
        events = EventSystem()
        events.emit("processing", {"task": "1"})
        events.emit("processing", {"task": "2"})
        assert len(events.history) == 2

    def test_clear_history(self):
        events = EventSystem()
        events.emit("processing", {"task": "test"})
        events.clear_history()
        assert len(events.history) == 0

    def test_filter_events_by_type(self):
        events = EventSystem()
        events.emit("processing", {"task": "1"})
        events.emit("tool_call", {"tool": "test"})
        processing = events.get_events(EventType.PROCESSING)
        assert len(processing) == 1


class TestEvent:
    def test_event_dataclass(self):
        event = Event(
            type=EventType.PROCESSING,
            data={"task": "test"},
            timestamp=12345,
        )
        assert event.type == EventType.PROCESSING
        assert event.data["task"] == "test"
        assert event.timestamp == 12345


class TestEventType:
    def test_all_event_types_defined(self):
        assert EventType.PROCESSING.value == "processing"
        assert EventType.TOOL_CALL.value == "tool_call"
        assert EventType.APPROVAL_REQUIRED.value == "approval_required"
        assert EventType.ERROR.value == "error"
        assert EventType.SUCCESS.value == "success"