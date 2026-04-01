# pyright: reportMissingImports=false

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def service_refs_dir(tmp_path: Path) -> Path:
    refs = tmp_path / "references"
    (refs / "papers").mkdir(parents=True)
    (refs / "pdfs").mkdir(parents=True)
    (refs / "chunks").mkdir(parents=True)
    (refs / "bibliography.bib").write_text("", encoding="utf-8")
    return refs


@pytest.fixture
def sample_reference_map() -> dict[str, dict[str, object]]:
    return {
        "paper-a": {
            "title": "Paper A Title",
            "year": 2021,
            "doi": "10.1/a",
            "cites": ["ext-1", "paper-b"],
            "authors": ["A"],
        },
        "paper-b": {
            "title": "Paper B Title",
            "year": 2022,
            "doi": "10.1/b",
            "cites": ["ext-1", "ext-2"],
            "authors": ["B"],
        },
    }


@pytest.fixture
def mocked_requests_response() -> MagicMock:
    response = MagicMock()
    response.raise_for_status.return_value = None
    return response


@pytest.fixture
def fake_provider_paper() -> SimpleNamespace:
    return SimpleNamespace(references=["ext-1", "ext-2", "ext-3"])
