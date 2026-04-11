"""Tests for EvidenceOrchestrator service - Issue #71 Feynman integration."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from crane.services.evidence_orchestrator_service import (
    EvidenceOrchestrator,
    OrchestrationState,
)


class TestOrchestrationState:
    def test_initialization(self):
        state = OrchestrationState(stage="test_stage")

        assert state.stage == "test_stage"
        assert state.progress == 0.0
        assert isinstance(state.results, dict)
        assert isinstance(state.errors, list)
        assert state.timestamp is not None

    def test_to_dict(self):
        state = OrchestrationState(
            stage="researcher",
            progress=0.5,
            results={"key": "value"},
            errors=["error1"],
        )

        result = state.to_dict()

        assert result["stage"] == "researcher"
        assert result["progress"] == 0.5
        assert result["key"] == "value"
        assert "error1" in result["errors"]


class TestEvidenceOrchestrator:
    @pytest.fixture
    def orchestrator(self, tmp_path: Path):
        refs_dir = tmp_path / "references"
        refs_dir.mkdir()
        return EvidenceOrchestrator(refs_dir=str(refs_dir))

    @pytest.fixture
    def sample_paper(self, tmp_path: Path):
        paper_path = tmp_path / "sample.tex"
        paper_path.write_text(r"""
\documentclass{article}
\begin{document}

\begin{abstract}
This is a sample abstract.
\end{abstract}

\section{Introduction}
This is the introduction section.

\section{Methods}
This is the methods section.

\section{Results}
This is the results section.

\section{Discussion}
This is the discussion section.

\section{Conclusion}
This is the conclusion section.

\end{document}
""")
        return paper_path

    def test_initialization(self, orchestrator: EvidenceOrchestrator):
        assert orchestrator.paper_service is not None
        assert orchestrator.citation_service is not None
        assert orchestrator.review_service is not None
        assert orchestrator.chapter_coach is not None
        assert orchestrator.state.stage == "initialized"

    def test_run_researcher(self, orchestrator: EvidenceOrchestrator):
        with patch.object(
            orchestrator.paper_service, "search", return_value=[{"id": "paper1", "title": "Test"}]
        ):
            with patch.object(orchestrator.paper_service, "download", return_value=True):
                with patch.object(
                    orchestrator.paper_service, "read", return_value="Sample content"
                ):
                    result = orchestrator.run_researcher("test query", max_papers=1)

                    assert result.stage == "researcher"
                    assert result.progress == 1.0
                    assert result.results.get("status") == "completed"
                    assert "search_results" in result.results
                    assert "downloaded" in result.results
                    assert len(result.results["downloaded"]) == 1

    def test_run_researcher_no_results(self, orchestrator: EvidenceOrchestrator):
        with patch.object(orchestrator.paper_service, "search", return_value=[]):
            result = orchestrator.run_researcher("nonexistent query", max_papers=0)

            assert result.stage == "researcher"
            assert result.progress == 1.0
            assert result.results.get("status") == "completed"
            assert len(result.results["search_results"]) == 0

    def test_run_reviewer(self, orchestrator: EvidenceOrchestrator, sample_paper: Path):
        mock_report = MagicMock()
        mock_report.critical_defects = [
            MagicMock(id="C1", description="Critical issue", chapter="Introduction")
        ]
        mock_report.major_defects = [
            MagicMock(id="M1", description="Major issue", chapter="Methods")
        ]
        mock_report.minor_defects = [
            MagicMock(id="Mi1", description="Minor issue", chapter="Results")
        ]
        mock_report.to_dict = MagicMock(return_value={"total_defects": 3})

        with patch.object(orchestrator.review_service, "review_full", return_value=mock_report):
            result = orchestrator.run_reviewer(str(sample_paper))

            assert result.stage == "reviewer"
            assert result.progress == 1.0
            assert result.results.get("status") == "completed"
            assert len(result.results["defect_report"]["critical_issues"]) == 1
            assert len(result.results["defect_report"]["major_issues"]) == 1
            assert len(result.results["defect_report"]["minor_issues"]) == 1

    def test_run_reviewer_file_not_found(self, orchestrator: EvidenceOrchestrator):
        result = orchestrator.run_reviewer("nonexistent.tex")

        assert result.stage == "reviewer"
        assert result.results.get("status") == "failed"
        assert len(result.errors) > 0
        assert "Paper not found" in result.errors[0]

    def test_run_writer_valid_chapter(self, orchestrator: EvidenceOrchestrator, sample_paper: Path):
        with patch.object(
            orchestrator.chapter_coach,
            "coach_chapter",
            return_value={
                "suggestions": ["Fix grammar", "Improve clarity"],
                "feedback": {
                    "writing_quality": 85,
                    "clarity": 90,
                    "structure": 80,
                },
            },
        ):
            result = orchestrator.run_writer(str(sample_paper), "introduction")

            assert result.stage == "writer"
            assert result.progress == 1.0
            assert result.results.get("status") == "completed"
            assert len(result.results["recommendations"]) == 2

    def test_run_writer_invalid_chapter(
        self, orchestrator: EvidenceOrchestrator, sample_paper: Path
    ):
        result = orchestrator.run_writer(str(sample_paper), "invalid_chapter")

        assert result.stage == "writer"
        assert result.results.get("status") == "failed"
        assert len(result.errors) > 0
        assert "Invalid chapter" in result.errors[0]

    def test_run_verifier(self, orchestrator: EvidenceOrchestrator, sample_paper: Path):
        cite_keys = ["cite1", "cite2", "cite3", "cite4", "cite5"]

        with patch.object(
            orchestrator.citation_service, "extract_cite_keys", return_value=cite_keys
        ):
            result = orchestrator.run_verifier(str(sample_paper))

            assert result.stage == "verifier"
            assert result.progress == 1.0
            assert result.results.get("status") == "completed"
            assert result.results["verification_summary"]["valid"] is True
            assert result.results["verification_summary"]["total_citations"] == 5

    def test_run_verifier_empty_citations(
        self, orchestrator: EvidenceOrchestrator, sample_paper: Path
    ):
        with patch.object(orchestrator.citation_service, "extract_cite_keys", return_value=[]):
            result = orchestrator.run_verifier(str(sample_paper))

            assert result.stage == "verifier"
            assert result.progress == 1.0
            assert result.results.get("status") == "completed"
            assert result.results["verification_summary"]["valid"] is False
            assert len(result.results["cite_keys"]) == 0

    def test_run_full_orchestration(self, orchestrator: EvidenceOrchestrator, sample_paper: Path):
        mock_report = MagicMock()
        mock_report.critical_defects = []
        mock_report.major_defects = []
        mock_report.minor_defects = []
        mock_report.to_dict = MagicMock(return_value={"total_defects": 0})

        with patch.object(orchestrator.paper_service, "search", return_value=[{"id": "paper1"}]):
            with patch.object(orchestrator.paper_service, "download", return_value=True):
                with patch.object(orchestrator.paper_service, "read", return_value="Content"):
                    with patch.object(
                        orchestrator.review_service, "review_full", return_value=mock_report
                    ):
                        with patch.object(
                            orchestrator.chapter_coach,
                            "coach_chapter",
                            return_value={"suggestions": []},
                        ):
                            with patch.object(
                                orchestrator.citation_service, "extract_cite_keys", return_value=[]
                            ):
                                result = orchestrator.run_full_orchestration(
                                    research_query="test",
                                    paper_path=str(sample_paper),
                                    chapters=["introduction"],
                                    max_papers=1,
                                )

                                assert "stages" in result
                                assert "researcher" in result["stages"]
                                assert "reviewer" in result["stages"]
                                assert "writer" in result["stages"]
                                assert "verifier" in result["stages"]
                                assert "orchestration_id" in result
                                assert "completed_at" in result
                                assert result["completed_at"] is not None

    def test_extract_chapter_abstract(self, orchestrator: EvidenceOrchestrator, sample_paper: Path):
        chapter_content = orchestrator._extract_chapter(sample_paper, "abstract")

        assert "abstract" in chapter_content.lower()
        assert "sample abstract" in chapter_content

    def test_extract_chapter_introduction(
        self, orchestrator: EvidenceOrchestrator, sample_paper: Path
    ):
        chapter_content = orchestrator._extract_chapter(sample_paper, "introduction")

        assert "introduction" in chapter_content.lower()
        assert "introduction section" in chapter_content

    def test_extract_chapter_nonexistent(
        self, orchestrator: EvidenceOrchestrator, sample_paper: Path
    ):
        chapter_content = orchestrator._extract_chapter(sample_paper, "acknowledgment")

        assert chapter_content == ""
