from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from collections import Counter


@dataclass
class LoopPattern:
    tool: str
    count: int
    is_looping: bool
    severity: str = "low"
    suggestion: str = ""


class DoomLoopDetector:
    def __init__(
        self,
        repeat_threshold: int = 3,
        window_size: int = 10,
    ):
        self.repeat_threshold = repeat_threshold
        self.window_size = window_size

    def detect_loop(self, history: list[dict[str, Any]]) -> LoopPattern:
        if not history:
            return LoopPattern(tool="", count=0, is_looping=False)

        window = history[-self.window_size :] if len(history) > self.window_size else history
        tool_names = [h.get("tool", "") for h in window if h.get("tool")]
        
        if not tool_names:
            return LoopPattern(tool="", count=0, is_looping=False)

        counts = Counter(tool_names)
        max_tool, max_count = counts.most_common(1)[0]

        is_looping = max_count >= self.repeat_threshold
        severity = self._calculate_severity(max_count)

        return LoopPattern(
            tool=max_tool,
            count=max_count,
            is_looping=is_looping,
            severity=severity,
            suggestion=self._generate_suggestion(max_tool, max_count) if is_looping else "",
        )

    def _calculate_severity(self, count: int) -> str:
        if count >= self.repeat_threshold + 2:
            return "critical"
        elif count >= self.repeat_threshold + 1:
            return "high"
        elif count >= self.repeat_threshold:
            return "medium"
        return "low"

    def _generate_suggestion(self, tool: str, count: int) -> str:
        return f"Consider switching from {tool} after {count} repeats. Try semantic_search or evaluate_paper."