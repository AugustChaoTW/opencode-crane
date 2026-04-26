"""Tests for Context Auto-compaction service - crane_compact_context (#100)"""
import pytest
from crane.services.context_compactor import ContextCompactor, CompactionResult


class TestContextCompactor:
    def test_default_threshold(self):
        compactor = ContextCompactor()
        assert compactor.token_threshold == 170000

    def test_custom_threshold(self):
        compactor = ContextCompactor(token_threshold=200000)
        assert compactor.token_threshold == 200000

    def test_no_compaction_needed(self):
        compactor = ContextCompactor(token_threshold=100000)
        context = {
            "messages": [{"role": "user", "content": "Hello"}],
            "token_count": 50000,
        }
        result = compactor.compact(context)
        assert result.compacted is False

    def test_compaction_needed_at_threshold(self):
        compactor = ContextCompactor(token_threshold=100000)
        context = {
            "messages": [{"role": "user", "content": "test"}] * 10,
            "token_count": 120000,
        }
        result = compactor.compact(context)
        assert result.compacted is True

    def test_preserves_recent_messages(self):
        compactor = ContextCompactor(preserve_recent=3)
        context = {
            "messages": [{"role": "user", "content": f"msg {i}"} for i in range(10)],
            "token_count": 180000,
        }
        result = compactor.compact(context)
        preserved = result.preserved_count
        assert preserved >= 3

    def test_compaction_result_has_required_fields(self):
        compactor = ContextCompactor()
        context = {
            "messages": [{"role": "user", "content": "test"}],
            "token_count": 200000,
        }
        result = compactor.compact(context)
        assert hasattr(result, "compacted")
        assert hasattr(result, "original_count")
        assert hasattr(result, "preserved_count")

    def test_token_reduction_calculated(self):
        compactor = ContextCompactor(token_threshold=100000)
        context = {
            "messages": [{"role": "user", "content": "Hello world " * 50}] * 5,
            "token_count": 150000,
        }
        result = compactor.compact(context)
        assert result.token_reduction >= 0


class TestCompactionResult:
    def test_result_default_values(self):
        result = CompactionResult(
            compacted=True,
            original_count=10,
            preserved_count=3,
            token_reduction=50000,
        )
        assert result.compacted is True
        assert result.original_count == 10
        assert result.token_reduction == 50000