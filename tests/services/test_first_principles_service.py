# pyright: reportMissingImports=false

from __future__ import annotations

from pathlib import Path

import pytest

from crane.services.first_principles_service import FirstPrinciplesService


class _Workspace:
    def __init__(self, project_root: str):
        self.project_root = project_root


@pytest.fixture
def service(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> FirstPrinciplesService:
    monkeypatch.setattr(
        "crane.services.first_principles_service.resolve_workspace",
        lambda _project_dir=None: _Workspace(str(tmp_path)),
    )
    return FirstPrinciplesService(project_dir=str(tmp_path))


def test_deconstruct_ai_ml_contains_rich_knowledge(service: FirstPrinciplesService) -> None:
    out = service.deconstruct(domain="AI/ML")

    assert out["domain"] == "ai/ml"
    assert len(out["conventional_wisdom"]) >= 4
    beliefs = [item["belief"] for item in out["conventional_wisdom"]]
    assert "Bigger models win" in beliefs
    assert out["first_principles"]
    assert out["rebuilt_conclusions"]
    assert out["conventional_vs_rebuilt_gap"]
    assert out["contrarian_opportunities"]
    assert out["historical_patterns"]
    assert isinstance(out["expert_consensus_assessment"], str)
    assert out["actionable_implications"]


def test_deconstruct_specific_belief_focuses_result(service: FirstPrinciplesService) -> None:
    out = service.deconstruct(
        domain="general",
        specific_belief="Impact factor measures paper quality",
    )

    assert out["specific_belief"] == "Impact factor measures paper quality"
    assert len(out["conventional_wisdom"]) == 1
    assert out["conventional_wisdom"][0]["belief"] == "Impact factor measures paper quality"
    assert out["conventional_wisdom"][0]["is_tradition"] is True


def test_deconstruct_infers_domain_from_paper_path(
    service: FirstPrinciplesService,
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        "This work improves transformer token efficiency for sequence language tasks.",
        encoding="utf-8",
    )

    out = service.deconstruct(domain="", paper_path=str(paper))
    assert out["domain"] == "nlp"


def test_deconstruct_missing_paper_raises(service: FirstPrinciplesService) -> None:
    with pytest.raises(FileNotFoundError):
        service.deconstruct(domain="", paper_path="missing.tex")


def test_consensus_assessment_identifies_echo_chamber_risk(
    service: FirstPrinciplesService,
) -> None:
    out = service.deconstruct(domain="general")
    assert "consensus" in out["expert_consensus_assessment"].lower()
