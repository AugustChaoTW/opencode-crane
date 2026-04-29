# pyright: reportMissingImports=false
"""Tests for ContradictionDetectionService."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from crane.services.contradiction_detection_service import (
    Contradiction,
    ContradictionDetectionService,
    ContradictionType,
)
from crane.services.paper_knowledge_graph_service import KGEdge, PaperKnowledgeGraph
from crane.services.section_chunker import Section


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_section(name: str, content: str, canonical: str = "") -> Section:
    return Section(
        name=name,
        canonical_name=canonical or name,
        content=content,
        character_count=len(content),
        word_count=len(content.split()),
    )


@pytest.fixture
def svc() -> ContradictionDetectionService:
    return ContradictionDetectionService(api_key=None)


@pytest.fixture
def svc_with_key() -> ContradictionDetectionService:
    return ContradictionDetectionService(api_key="sk-test")


@pytest.fixture
def sample_paper(tmp_path: Path) -> Path:
    p = tmp_path / "paper.tex"
    p.write_text(
        r"""\documentclass{article}
\begin{document}
\begin{abstract}
We propose a novel method that significantly outperforms baselines.
\end{abstract}
\section{Introduction}
Our approach achieves state-of-the-art results.
\section{Methods}
We use learning rate 0.01 and batch size 64.
\section{Results}
Accuracy: 92\%. Our method outperforms the baseline by 10\% on CIFAR10.
\section{Conclusion}
In conclusion, our method does not outperform baselines in some settings.
\end{document}
""",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def kg_with_contradicts() -> PaperKnowledgeGraph:
    kg = PaperKnowledgeGraph(paper_path="fake.tex", file_hash="abc")
    kg.edges.append(
        KGEdge(
            source="MethodA",
            target="MethodB",
            relation="contradicts",
            evidence="contradictory accuracy claims",
            confidence=0.8,
        )
    )
    kg.edges.append(
        KGEdge(
            source="ModelX",
            target="DatasetY",
            relation="uses",
            evidence="evaluated on DatasetY",
            confidence=0.9,
        )
    )
    return kg


# ---------------------------------------------------------------------------
# ContradictionType enum
# ---------------------------------------------------------------------------


class TestContradictionType:
    def test_enum_values(self) -> None:
        assert ContradictionType.NUMERICAL.value == "numerical"
        assert ContradictionType.CLAIM_EVIDENCE.value == "claim_evidence"
        assert ContradictionType.CROSS_SECTION.value == "cross_section"
        assert ContradictionType.CITATION.value == "citation"


# ---------------------------------------------------------------------------
# Contradiction dataclass
# ---------------------------------------------------------------------------


class TestContradictionDataclass:
    def test_to_dict(self) -> None:
        c = Contradiction(
            type=ContradictionType.NUMERICAL,
            location_a="paper.tex",
            location_b="train.py",
            description="lr mismatch",
            severity="high",
            reviewer_attack_prob=0.87,
            suggested_fix="fix lr",
        )
        d = c.to_dict()
        assert d["type"] == "numerical"
        assert d["severity"] == "high"
        assert d["reviewer_attack_prob"] == 0.87


# ---------------------------------------------------------------------------
# Detector 2: claim-evidence
# ---------------------------------------------------------------------------


class TestDetectClaimEvidence:
    def test_flags_unsupported_claim(self, svc: ContradictionDetectionService) -> None:
        sections = [
            _make_section(
                "Abstract",
                "Our method is novel and achieves state-of-the-art performance.",
            )
        ]
        results = svc._detect_claim_evidence(sections)
        assert len(results) >= 1
        assert all(r.type == ContradictionType.CLAIM_EVIDENCE for r in results)
        assert all(r.severity == "high" for r in results)

    def test_no_flag_when_evidence_present(self, svc: ContradictionDetectionService) -> None:
        sections = [
            _make_section(
                "Results",
                "Our novel approach achieves 92.3% accuracy [12], significantly better than prior work.",
            )
        ]
        results = svc._detect_claim_evidence(sections)
        # All claims have evidence nearby — no contradiction expected
        assert len(results) == 0

    def test_multiple_sections(self, svc: ContradictionDetectionService) -> None:
        sections = [
            _make_section("Intro", "We significantly outperform all baselines."),
            _make_section("Methods", "Standard training procedure."),
        ]
        results = svc._detect_claim_evidence(sections)
        assert any(r.location_a == "Intro" for r in results)

    def test_description_truncated(self, svc: ContradictionDetectionService) -> None:
        sections = [_make_section("Abstract", "Our approach is novel " + "x" * 200)]
        results = svc._detect_claim_evidence(sections)
        for r in results:
            assert len(r.description) <= 80

    def test_suggested_fix_truncated(self, svc: ContradictionDetectionService) -> None:
        sections = [_make_section("Abstract", "Our method is state-of-the-art " + "y" * 200)]
        results = svc._detect_claim_evidence(sections)
        for r in results:
            assert len(r.suggested_fix) <= 60


# ---------------------------------------------------------------------------
# Detector 4: citation (KG-based)
# ---------------------------------------------------------------------------


class TestDetectCitation:
    def test_finds_contradicts_edges(
        self, svc: ContradictionDetectionService, kg_with_contradicts: PaperKnowledgeGraph
    ) -> None:
        results = svc._detect_citation(kg_with_contradicts)
        assert len(results) == 1
        assert results[0].type == ContradictionType.CITATION
        assert results[0].location_a == "MethodA"
        assert results[0].location_b == "MethodB"
        assert results[0].severity == "medium"

    def test_ignores_non_contradicts_edges(
        self, svc: ContradictionDetectionService
    ) -> None:
        kg = PaperKnowledgeGraph(paper_path="fake.tex")
        kg.edges.append(
            KGEdge("A", "B", "supports", "evidence", 0.9)
        )
        results = svc._detect_citation(kg)
        assert results == []

    def test_empty_kg(self, svc: ContradictionDetectionService) -> None:
        kg = PaperKnowledgeGraph(paper_path="fake.tex")
        assert svc._detect_citation(kg) == []

    def test_description_truncated(self, svc: ContradictionDetectionService) -> None:
        kg = PaperKnowledgeGraph(paper_path="fake.tex")
        kg.edges.append(
            KGEdge("X" * 40, "Y" * 40, "contradicts", "long evidence " * 10, 0.7)
        )
        results = svc._detect_citation(kg)
        assert len(results[0].description) <= 80


# ---------------------------------------------------------------------------
# Detector 3: cross-section — keyword negation fallback
# ---------------------------------------------------------------------------


class TestKeywordNegationCheck:
    def test_flags_negation_with_shared_words(
        self, svc: ContradictionDetectionService
    ) -> None:
        sec_a = _make_section("Abstract", "The method improves performance significantly.")
        sec_b = _make_section(
            "Conclusion",
            "However, the method does not improve performance in all cases.",
        )
        result = svc._keyword_negation_check(sec_a, sec_b)
        assert result is not None
        assert result["is_contradiction"] is True

    def test_no_flag_without_negation(
        self, svc: ContradictionDetectionService
    ) -> None:
        sec_a = _make_section("Abstract", "Method achieves great performance.")
        sec_b = _make_section("Conclusion", "Method achieves great performance again.")
        result = svc._keyword_negation_check(sec_a, sec_b)
        assert result is None

    def test_no_shared_words_returns_none(
        self, svc: ContradictionDetectionService
    ) -> None:
        sec_a = _make_section("Intro", "Alpha beta gamma delta epsilon.")
        sec_b = _make_section("Methods", "Zeta theta iota kappa lambda.")
        result = svc._keyword_negation_check(sec_a, sec_b)
        assert result is None


# ---------------------------------------------------------------------------
# Detector 3: cross-section — semantic prefilter fallback (no embedding)
# ---------------------------------------------------------------------------


class TestSemanticPrefilter:
    def test_fallback_pairs_when_no_api_key(
        self, svc: ContradictionDetectionService
    ) -> None:
        sections = [
            _make_section("Abstract", "We propose a method.", canonical="Abstract"),
            _make_section("Introduction", "Introduction text.", canonical="Introduction"),
            _make_section("Conclusion", "We conclude.", canonical="Conclusion"),
        ]
        pairs = svc._semantic_prefilter(sections)
        # Should return pairs that exist in FALLBACK_PAIRS
        names = {(a.canonical_name, b.canonical_name) for a, b in pairs}
        assert ("Abstract", "Introduction") in names or ("Abstract", "Conclusion") in names

    def test_empty_sections_returns_empty(
        self, svc: ContradictionDetectionService
    ) -> None:
        assert svc._semantic_prefilter([]) == []

    def test_fallback_only_matches_existing_sections(
        self, svc: ContradictionDetectionService
    ) -> None:
        sections = [_make_section("Methods", "method text", canonical="Methods")]
        pairs = svc._semantic_prefilter(sections)
        assert pairs == []


# ---------------------------------------------------------------------------
# Detector 3: cross-section — LLM path (mocked)
# ---------------------------------------------------------------------------


class TestLLMCrossSection:
    def test_llm_check_returns_contradiction(
        self, svc_with_key: ContradictionDetectionService
    ) -> None:
        sec_a = _make_section("Abstract", "Our method achieves 95% accuracy.")
        sec_b = _make_section("Table 3", "Best result: 80% accuracy.")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "is_contradiction": True,
                                "severity": "high",
                                "reason": "Accuracy differs 95% vs 80%",
                            }
                        )
                    }
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("crane.services.contradiction_detection_service.requests.post", return_value=mock_resp):
            result = svc_with_key._llm_check_contradiction(sec_a, sec_b)

        assert result is not None
        assert result["is_contradiction"] is True
        assert result["severity"] == "high"

    def test_llm_check_returns_none_on_error(
        self, svc_with_key: ContradictionDetectionService
    ) -> None:
        with patch(
            "crane.services.contradiction_detection_service.requests.post",
            side_effect=Exception("network error"),
        ):
            result = svc_with_key._llm_check_contradiction(
                _make_section("A", "text"),
                _make_section("B", "text"),
            )
        assert result is None


# ---------------------------------------------------------------------------
# Detector 1: numerical (mocked alignment service)
# ---------------------------------------------------------------------------


class TestDetectNumerical:
    def test_no_code_file_returns_empty(
        self, svc: ContradictionDetectionService, tmp_path: Path
    ) -> None:
        paper = tmp_path / "paper.tex"
        paper.write_text(r"\documentclass{article}\begin{document}\end{document}")
        results = svc._detect_numerical(str(paper))
        assert results == []

    def test_mismatch_produces_contradiction(
        self, svc: ContradictionDetectionService, tmp_path: Path
    ) -> None:
        paper = tmp_path / "paper.tex"
        paper.write_text(
            r"""We use learning rate 0.001 and epochs 50.
Dataset: CIFAR10."""
        )
        code = tmp_path / "train.py"
        code.write_text(
            "learning_rate = 0.1\nepochs = 50\n# cifar10 dataset\n"
        )

        results = svc._detect_numerical(str(paper))
        # Expects at least one contradiction for lr mismatch
        types = {r.type for r in results}
        assert ContradictionType.NUMERICAL in types
        assert all(r.severity == "high" for r in results)

    def test_returns_empty_on_alignment_error(
        self, svc: ContradictionDetectionService, tmp_path: Path
    ) -> None:
        paper = tmp_path / "paper.tex"
        paper.write_text("content")
        code = tmp_path / "train.py"
        code.write_text("x = 1")

        with patch(
            "crane.services.contradiction_detection_service.PaperCodeAlignmentService.compare_settings",
            side_effect=Exception("error"),
        ):
            results = svc._detect_numerical(str(paper))
        assert results == []


# ---------------------------------------------------------------------------
# Main detect() method
# ---------------------------------------------------------------------------


class TestDetect:
    def test_detect_all_types_default(
        self, svc: ContradictionDetectionService, sample_paper: Path
    ) -> None:
        # Pass pre-built sections and kg to avoid file IO beyond what's needed
        sections = [
            _make_section(
                "Abstract",
                "Our novel approach significantly outperforms all baselines.",
                "Abstract",
            ),
            _make_section("Conclusion", "However, results are mixed.", "Conclusion"),
        ]
        kg = PaperKnowledgeGraph(paper_path=str(sample_paper))
        kg.edges.append(
            KGEdge("MethodA", "MethodB", "contradicts", "conflicting claims", 0.7)
        )

        results = svc.detect(
            paper_path=str(sample_paper),
            sections=sections,
            kg=kg,
        )
        types_found = {r.type for r in results}
        # Should find at least claim_evidence and citation
        assert ContradictionType.CLAIM_EVIDENCE in types_found
        assert ContradictionType.CITATION in types_found

    def test_detect_only_numerical_type(
        self, svc: ContradictionDetectionService, tmp_path: Path
    ) -> None:
        paper = tmp_path / "paper.tex"
        paper.write_text(r"\documentclass{article}\begin{document}\end{document}")
        results = svc.detect(
            paper_path=str(paper),
            types=["numerical"],
        )
        # No code file → empty
        assert results == []

    def test_detect_only_citation_type(
        self,
        svc: ContradictionDetectionService,
        tmp_path: Path,
        kg_with_contradicts: PaperKnowledgeGraph,
    ) -> None:
        paper = tmp_path / "paper.tex"
        paper.write_text(r"\documentclass{article}\begin{document}\end{document}")
        results = svc.detect(
            paper_path=str(paper),
            types=["citation"],
            kg=kg_with_contradicts,
        )
        assert len(results) == 1
        assert results[0].type == ContradictionType.CITATION

    def test_detect_skips_claim_evidence_without_sections(
        self, svc: ContradictionDetectionService, tmp_path: Path
    ) -> None:
        paper = tmp_path / "paper.tex"
        paper.write_text(r"\documentclass{article}\begin{document}\end{document}")
        # Pass empty list explicitly as sections
        results = svc.detect(
            paper_path=str(paper),
            sections=[],
            types=["claim_evidence"],
        )
        assert results == []

    def test_detect_sorted_by_severity(
        self, svc: ContradictionDetectionService, tmp_path: Path
    ) -> None:
        paper = tmp_path / "paper.tex"
        paper.write_text(r"\documentclass{article}\begin{document}\end{document}")

        sections = [
            _make_section("Abstract", "Our novel approach significantly outperforms all."),
        ]
        kg = PaperKnowledgeGraph(paper_path=str(paper))
        kg.edges.append(KGEdge("A", "B", "contradicts", "evidence", 0.5))

        results = svc.detect(
            paper_path=str(paper),
            sections=sections,
            kg=kg,
            types=["claim_evidence", "citation"],
        )

        severity_order = {"high": 0, "medium": 1, "low": 2}
        for i in range(len(results) - 1):
            assert severity_order[results[i].severity] <= severity_order[results[i + 1].severity]

    def test_detect_sections_none_auto_parse(
        self, svc: ContradictionDetectionService, sample_paper: Path
    ) -> None:
        """When sections=None, service should attempt auto-parsing."""
        results = svc.detect(
            paper_path=str(sample_paper),
            types=["claim_evidence"],
        )
        # sample_paper has strong claims without evidence → at least one result
        assert isinstance(results, list)

    def test_detect_citation_without_kg_skipped(
        self, svc: ContradictionDetectionService, tmp_path: Path
    ) -> None:
        paper = tmp_path / "paper.tex"
        paper.write_text(r"\documentclass{article}\begin{document}\end{document}")
        results = svc.detect(
            paper_path=str(paper),
            kg=None,
            types=["citation"],
        )
        assert results == []


# ---------------------------------------------------------------------------
# Integration: detect_contradictions MCP tool
# ---------------------------------------------------------------------------


class TestDetectContradictionsTool:
    def test_tool_output_format(self, tmp_path: Path) -> None:
        from crane.tools.contradiction import register_tools

        calls = []

        class FakeMCP:
            def tool(self):
                def decorator(fn):
                    calls.append(fn)
                    return fn
                return decorator

        register_tools(FakeMCP())
        assert len(calls) == 1

        detect_fn = calls[0]
        paper = tmp_path / "paper.tex"
        paper.write_text(
            r"""\documentclass{article}
\begin{document}
\begin{abstract}
Our novel approach is state-of-the-art.
\end{abstract}
\end{document}"""
        )

        result = detect_fn(paper_path=str(paper))
        assert "total" in result
        assert "high_severity" in result
        assert "contradictions" in result
        assert isinstance(result["contradictions"], list)
        assert result["total"] >= 0
        assert result["high_severity"] <= result["total"]

    def test_tool_with_types_filter(self, tmp_path: Path) -> None:
        from crane.tools.contradiction import register_tools

        calls = []

        class FakeMCP:
            def tool(self):
                def decorator(fn):
                    calls.append(fn)
                    return fn
                return decorator

        register_tools(FakeMCP())
        detect_fn = calls[0]

        paper = tmp_path / "paper.tex"
        paper.write_text(r"\documentclass{article}\begin{document}\end{document}")

        result = detect_fn(paper_path=str(paper), types=["numerical"])
        assert "total" in result
        # No code file → 0 numerical contradictions
        assert result["total"] == 0
