"""RAG Enhancement for software testing - extending ask_library_service."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass
class TestCaseSuggestion:
    test_name: str
    test_code: str
    source_reference: str
    confidence: float


class RAGTestEnhancement:
    def __init__(self, ask_library_service):
        self.ask_library = ask_library_service

    def generate_test_hints(
        self, code_snippet: str, context: str
    ) -> list[TestCaseSuggestion]:
        suggestions = []
        query = f"test case for {context} in {code_snippet[:50]}"

        try:
            result = self.ask_library.query(query, k=3)
            for i, (chunk, source) in enumerate(
                zip(result.get("chunks", []), result.get("sources", []))
            ):
                suggestions.append(
                    TestCaseSuggestion(
                        test_name=f"test_{i+1}",
                        test_code=f"def test_{i+1}(): pass  # {chunk[:100]}",
                        source_reference=source,
                        confidence=1.0 - (i * 0.2),
                    )
                )
        except Exception:
            pass

        return suggestions

    def retrieve_code_examples(
        self, framework: str
    ) -> list[dict[str, Any]]:
        query = f"{framework} testing example pytest unittest"
        try:
            result = self.ask_library.query(query, k=2)
            return result.get("chunks", [])
        except Exception:
            return []