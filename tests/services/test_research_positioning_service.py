# pyright: reportMissingImports=false

from __future__ import annotations

from pathlib import Path

from crane.services.research_positioning_service import ResearchPositioningService


def test_analyze_positioning_with_topic_infers_domain_and_levels() -> None:
    service = ResearchPositioningService()

    out = service.analyze_positioning(research_topic="LLM safety for multi-agent planning")

    assert out["topic"] == "LLM safety for multi-agent planning"
    assert out["domain"] in {"AI/ML", "NLP"}
    assert set(out["levels"].keys()) == {
        "civilizational",
        "industry",
        "organizational",
        "tactical",
        "operational",
    }
    assert isinstance(out["cross_level_connections"], list)
    assert isinstance(out["blind_spots"], list)


def test_analyze_positioning_with_paper_extracts_topic_and_detects_gaps(tmp_path: Path) -> None:
    tex = tmp_path / "paper.tex"
    tex.write_text(
        """
\\title{Compute-Efficient LLM Alignment}
\\begin{abstract}
We study alignment methods for large language models under strict compute budgets.
\\end{abstract}
\\section{Introduction}
Motivation and setup.
""".strip(),
        encoding="utf-8",
    )

    service = ResearchPositioningService(project_dir=str(tmp_path))
    out = service.analyze_positioning(paper_path="paper.tex")

    assert out["topic"] == "Compute-Efficient LLM Alignment"
    assert out["levels"]["tactical"]["milestones"]
    assert any(
        "limitations" in step.lower() for step in out["levels"]["operational"]["immediate_actions"]
    )


def test_analyze_positioning_detects_strategic_tactical_mismatch() -> None:
    service = ResearchPositioningService()

    out = service.analyze_positioning(
        research_topic=(
            "LLM governance for sovereign AI with compute inequality in "
            "specialized low-resource sectors"
        )
    )

    assert out["level_mismatch"] == "Solving a strategic problem with tactical tools"
    assert out["zoom_recommendation"] == "organizational"


def test_analyze_positioning_flags_organizational_zoom_when_alignment_is_weak() -> None:
    service = ResearchPositioningService()

    out = service.analyze_positioning(research_topic="graph indexing for enterprise search")

    assert len(out["levels"]["operational"]["immediate_actions"]) >= 4
    assert out["zoom_recommendation"] == "organizational"
