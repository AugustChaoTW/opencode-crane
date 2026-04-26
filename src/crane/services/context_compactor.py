from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass
class CompactionResult:
    compacted: bool
    original_count: int
    preserved_count: int
    token_reduction: int


class ContextCompactor:
    def __init__(
        self,
        token_threshold: int = 170000,
        preserve_recent: int = 5,
    ):
        self.token_threshold = token_threshold
        self.preserve_recent = preserve_recent

    def compact(self, context: dict[str, Any]) -> CompactionResult:
        messages = context.get("messages", [])
        token_count = context.get("token_count", 0)

        original_count = len(messages)

        if token_count < self.token_threshold or original_count <= self.preserve_recent:
            return CompactionResult(
                compacted=False,
                original_count=original_count,
                preserved_count=original_count,
                token_reduction=0,
            )

        preserved = messages[-self.preserve_recent :] if len(messages) > self.preserve_recent else messages
        preserved_count = len(preserved)

        estimated_tokens = sum(len(m.get("content", "")) // 4 for m in messages)
        preserved_tokens = sum(len(m.get("content", "")) // 4 for m in preserved)
        token_reduction = max(0, estimated_tokens - preserved_tokens)

        return CompactionResult(
            compacted=True,
            original_count=original_count,
            preserved_count=preserved_count,
            token_reduction=token_reduction,
        )