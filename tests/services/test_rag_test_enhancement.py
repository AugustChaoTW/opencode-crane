import pytest
from unittest.mock import MagicMock
from crane.services.rag_test_enhancement import (
    RAGTestEnhancement,
    TestCaseSuggestion,
)


def test_generate_test_hints():
    mock_service = MagicMock()
    mock_service.query.return_value = {
        "chunks": ["test chunk 1", "test chunk 2"],
        "sources": ["source1", "source2"],
    }

    enhancer = RAGTestEnhancement(mock_service)
    suggestions = enhancer.generate_test_hints("def add(a,b)", "math")

    assert len(suggestions) == 2
    assert all(isinstance(s, TestCaseSuggestion) for s in suggestions)


def test_retrieve_code_examples():
    mock_service = MagicMock()
    mock_service.query.return_value = {"chunks": ["example1"]}

    enhancer = RAGTestEnhancement(mock_service)
    examples = enhancer.retrieve_code_examples("pytest")

    assert isinstance(examples, list)