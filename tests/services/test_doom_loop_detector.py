"""Tests for Doom Loop Detector service - crane_detect_loops (#99)"""
import pytest
from crane.services.doom_loop_detector import DoomLoopDetector, LoopPattern


class TestDoomLoopDetector:
    def test_default_thresholds(self):
        detector = DoomLoopDetector()
        assert detector.repeat_threshold == 3
        assert detector.window_size == 10

    def test_custom_thresholds(self):
        detector = DoomLoopDetector(repeat_threshold=5, window_size=20)
        assert detector.repeat_threshold == 5
        assert detector.window_size == 20

    def test_no_loop_with_varied_tools(self):
        detector = DoomLoopDetector()
        history = [
            {"tool": "search_papers", "success": True},
            {"tool": "evaluate_paper", "success": True},
            {"tool": "semantic_search", "success": True},
        ]
        result = detector.detect_loop(history)
        assert result.is_looping is False

    def test_repeat_detection_threshold(self):
        detector = DoomLoopDetector(repeat_threshold=3)
        history = [
            {"tool": "search_papers"},
            {"tool": "search_papers"},
            {"tool": "search_papers"},
        ]
        result = detector.detect_loop(history)
        assert result.is_looping is True

    def test_partial_repeat_not_flagged(self):
        detector = DoomLoopDetector(repeat_threshold=3)
        history = [
            {"tool": "search_papers"},
            {"tool": "search_papers"},
            {"tool": "semantic_search"},
        ]
        result = detector.detect_loop(history)
        assert result.is_looping is False

    def test_window_respects_limit(self):
        detector = DoomLoopDetector(window_size=5, repeat_threshold=3)
        history = [
            {"tool": "search_papers"},
            {"tool": "evaluate_paper"},
            {"tool": "search_papers"},
            {"tool": "evaluate_paper"},
            {"tool": "search_papers"},
            {"tool": "evaluate_paper"},
            {"tool": "search_papers"},
            {"tool": "evaluate_paper"},
            {"tool": "search_papers"},
            {"tool": "evaluate_paper"},
        ]
        result = detector.detect_loop(history)
        assert result.count <= 5

    def test_pattern_includes_repeated_tool(self):
        detector = DoomLoopDetector(repeat_threshold=3)
        history = [
            {"tool": "search_papers"},
            {"tool": "search_papers"},
            {"tool": "search_papers"},
        ]
        result = detector.detect_loop(history)
        assert result.tool == "search_papers"

    def test_loop_result_has_required_fields(self):
        detector = DoomLoopDetector(repeat_threshold=3)
        history = [
            {"tool": "search_papers"},
            {"tool": "search_papers"},
            {"tool": "search_papers"},
        ]
        result = detector.detect_loop(history)
        assert result.is_looping is True
        assert result.count >= 3
        assert result.tool == "search_papers"


class TestLoopPattern:
    def test_pattern_dataclass(self):
        pattern = LoopPattern(
            tool="test_tool",
            count=3,
            is_looping=True,
            severity="medium",
        )
        assert pattern.tool == "test_tool"
        assert pattern.count == 3