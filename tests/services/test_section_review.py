"""Tests for section review service."""

from __future__ import annotations

import importlib

from crane.models.paper import AiAnnotations, Paper


def _load_parser():
    return importlib.import_module("crane.services.latex_parser")


def _load_review():
    return importlib.import_module("crane.services.section_review_service")


class TestLatexParser:
    def test_parse_sections(self, tmp_path):
        parser = _load_parser()
        tex_file = tmp_path / "test.tex"
        tex_file.write_text(r"""
\title{Test Paper}
\begin{abstract}
This is a test abstract.
\end{abstract}
\section{Introduction}
Introduction content.
\section{Methodology}
Methodology content.
\subsection{Component A}
Component A content.
""")
        structure = parser.parse_latex_sections(tex_file)

        assert structure.title == "Test Paper"
        assert "test abstract" in structure.abstract.lower()
        assert len(structure.sections) == 2
        assert structure.sections[0].name == "Introduction"
        assert structure.sections[1].name == "Methodology"
        assert len(structure.sections[1].subsections) == 1

    def test_parse_appendices(self, tmp_path):
        parser = _load_parser()
        tex_file = tmp_path / "test.tex"
        tex_file.write_text(r"""
\section{Main}
Main content.
\appendix
\section{Appendix A}
Appendix content.
""")
        structure = parser.parse_latex_sections(tex_file)

        assert len(structure.sections) == 1
        assert len(structure.appendices) == 1
        assert structure.appendices[0].name == "Appendix A"


class TestSectionReviewService:
    def test_review_section_detects_issues(self):
        review = _load_review()
        parser = _load_parser()
        service = review.SectionReviewService()

        section = parser.SectionLocation(
            name="Test",
            level=1,
            start_line=1,
            end_line=10,
            content=(
                "It is worth noting that this is a novel approach. "
                "Furthermore, we achieve significant improvement."
            ),
        )

        result = service.review_section(section, [review.ReviewType.WRITING])

        assert len(result.issues) > 0
        assert result.score < 1.0

    def test_review_paper_returns_summary(self, tmp_path):
        review = _load_review()
        tex_file = tmp_path / "test.tex"
        tex_file.write_text(r"""
\title{Test}
\section{Introduction}
We propose a novel neuro-symbolic expert system.
\section{Experiments}
We achieve 62.5% improvement.
""")
        service = review.SectionReviewService()
        result = service.review_paper(tex_file)

        assert result.summary["total_issues"] >= 0
        assert "overall_score" in result.summary
        assert "recommendation" in result.summary

    def test_baseline_completeness_detects_missing(self):
        review = _load_review()
        parser = _load_parser()
        service = review.SectionReviewService()

        section = parser.SectionLocation(
            name="Test",
            level=1,
            start_line=1,
            end_line=10,
            content="We compare with Model Retry (no repair). Our approach is better.",
        )

        result = service.review_section(section, [review.ReviewType.BASELINE_COMPLETENESS])

        assert len(result.issues) > 0

    def test_evaluation_rigor_detects_missing_semantic(self):
        review = _load_review()
        parser = _load_parser()
        service = review.SectionReviewService()

        section = parser.SectionLocation(
            name="Test",
            level=1,
            start_line=1,
            end_line=10,
            content="We achieve 99.98% parse success rate.",
        )

        result = service.review_section(section, [review.ReviewType.EVALUATION_RIGOR])

        assert len(result.issues) > 0

    def test_scope_limitation_detects_overclaim(self):
        review = _load_review()
        parser = _load_parser()
        service = review.SectionReviewService()

        section = parser.SectionLocation(
            name="Test",
            level=1,
            start_line=1,
            end_line=10,
            content="Our production-ready system is applicable to all NLP tasks.",
        )

        result = service.review_section(section, [review.ReviewType.SCOPE_LIMITATION])

        assert len(result.issues) > 0

    def test_review_paper_includes_ai_annotation_context(self, tmp_path):
        review = _load_review()
        tex_file = tmp_path / "test.tex"
        tex_file.write_text(r"""
\title{Test}
\section{Introduction}
Baseline introduction text.
""")
        paper = Paper(
            key="k",
            title="T",
            authors=["A"],
            year=2026,
            ai_annotations=AiAnnotations(
                summary="novel breakthrough method",
                relevance_notes="state-of-the-art claims",
            ),
        )

        service = review.SectionReviewService()
        result = service.review_paper(
            tex_file,
            review_types=[review.ReviewType.FRAMING],
            paper=paper,
        )

        assert result.summary["annotation_context_used"] is True
        assert any(section.name == "AI Annotations" for section in result.sections)


class TestSectionReviewTools:
    def test_registered(self):
        from crane.server import mcp

        tools = mcp._tool_manager._tools if hasattr(mcp, "_tool_manager") else {}
        assert "review_paper_sections" in tools
        assert "parse_paper_structure" in tools


class TestScholarlyVoiceReview:
    def test_detects_informal_language(self):
        review = _load_review()
        parser = _load_parser()
        service = review.SectionReviewService()

        section = parser.SectionLocation(
            name="Test",
            level=1,
            start_line=1,
            end_line=10,
            content="This is an awesome result. The model gets better performance.",
        )

        result = service.review_section(section, [review.ReviewType.SCHOLARLY_VOICE])

        assert len(result.issues) > 0
        issue_types = [i.issue for i in result.issues]
        assert any("informal" in t.lower() for t in issue_types)

    def test_detects_personal_opinion(self):
        review = _load_review()
        parser = _load_parser()
        service = review.SectionReviewService()

        section = parser.SectionLocation(
            name="Test",
            level=1,
            start_line=1,
            end_line=10,
            content="I believe this approach is superior. We think it works well.",
        )

        result = service.review_section(section, [review.ReviewType.SCHOLARLY_VOICE])

        assert len(result.issues) > 0
        issue_types = [i.issue for i in result.issues]
        assert any("personal opinion" in t.lower() for t in issue_types)

    def test_detects_vague_quantifiers(self):
        review = _load_review()
        parser = _load_parser()
        service = review.SectionReviewService()

        section = parser.SectionLocation(
            name="Test",
            level=1,
            start_line=1,
            end_line=10,
            content="We tested a lot of samples with tons of data.",
        )

        result = service.review_section(section, [review.ReviewType.SCHOLARLY_VOICE])

        assert len(result.issues) > 0
        issue_types = [i.issue for i in result.issues]
        assert any("informal quantification" in t.lower() for t in issue_types)

    def test_no_issues_in_academic_text(self):
        review = _load_review()
        parser = _load_parser()
        service = review.SectionReviewService()

        section = parser.SectionLocation(
            name="Test",
            level=1,
            start_line=1,
            end_line=10,
            content=(
                "The proposed method demonstrates significant improvements. "
                "Results indicate a 15% increase in accuracy."
            ),
        )

        result = service.review_section(section, [review.ReviewType.SCHOLARLY_VOICE])

        assert len(result.issues) == 0


class TestAdversarialThinking:
    def test_analyze_black_swans_returns_three_scenarios(self):
        review = _load_review()
        service = review.SectionReviewService()

        issues = [
            {"type": "framing", "severity": "high", "issue": "Overclaiming detected"},
            {
                "type": "evaluation_rigor",
                "severity": "high",
                "issue": "Structural metric only",
            },
        ]

        result = service.analyze_black_swans(issues)

        assert isinstance(result, list)
        assert len(result) == 3

    def test_analyze_black_swans_has_required_fields_and_value_ranges(self):
        review = _load_review()
        service = review.SectionReviewService()

        result = service.analyze_black_swans(
            [{"type": "baseline_completeness", "severity": "critical", "issue": "Missing SOTA"}]
        )

        for scenario in result:
            assert set(scenario.keys()) == {"scenario", "probability", "impact", "mitigation"}
            assert scenario["probability"] in {"low", "very-low"}
            assert scenario["impact"] in {"critical", "high"}
            assert isinstance(scenario["mitigation"], str)
            assert scenario["mitigation"].strip() != ""

    def test_analyze_black_swans_with_ai_ml_context(self):
        review = _load_review()
        service = review.SectionReviewService()

        result = service.analyze_black_swans(
            [{"type": "data", "severity": "high", "issue": "Data inconsistency"}],
            {
                "domain": "AI/ML",
                "paper_type": "empirical study",
                "key_claims": ["state-of-the-art"],
            },
        )

        assert any("AI/ML" in s["scenario"] for s in result)
        assert any("state-of-the-art" in s["scenario"] for s in result)

    def test_analyze_black_swans_with_nlp_context(self):
        review = _load_review()
        service = review.SectionReviewService()

        result = service.analyze_black_swans(
            [
                {
                    "type": "scope_limitation",
                    "severity": "high",
                    "issue": "Overgeneralization detected",
                }
            ],
            {"domain": "NLP", "paper_type": "benchmarking paper", "key_claims": ["robust parsing"]},
        )

        assert any("NLP" in s["scenario"] for s in result)
        assert any("benchmarking paper" in s["scenario"] for s in result)

    def test_analyze_black_swans_with_empty_context_uses_defaults(self):
        review = _load_review()
        service = review.SectionReviewService()

        result = service.analyze_black_swans([], {})

        assert any("the target domain" in s["scenario"] for s in result)
        assert any("empirical study" in s["scenario"] for s in result)

    def test_analyze_black_swans_with_none_context_uses_defaults(self):
        review = _load_review()
        service = review.SectionReviewService()

        result = service.analyze_black_swans([], None)

        assert len(result) == 3
        assert any("your core contribution" in s["scenario"] for s in result)

    def test_analyze_black_swans_critical_issues_raise_impact_profile(self):
        review = _load_review()
        service = review.SectionReviewService()

        low_risk = service.analyze_black_swans(
            [{"type": "methodology", "severity": "low", "issue": "Minor wording issue"}]
        )
        high_risk = service.analyze_black_swans(
            [
                {
                    "type": "baseline_completeness",
                    "severity": "critical",
                    "issue": "Missing constrained decoding baseline comparison",
                }
            ]
        )

        low_risk_critical_count = sum(1 for s in low_risk if s["impact"] == "critical")
        high_risk_critical_count = sum(1 for s in high_risk if s["impact"] == "critical")
        assert high_risk_critical_count >= low_risk_critical_count

    def test_simulate_competitor_response_returns_required_keys(self):
        review = _load_review()
        service = review.SectionReviewService()

        result = service.simulate_competitor_response([])

        assert set(result.keys()) == {
            "competitor_strategy",
            "exploitable_weaknesses",
            "counter_measures",
        }

    def test_simulate_competitor_response_non_empty_strategy_and_lists(self):
        review = _load_review()
        service = review.SectionReviewService()

        issues = [
            {"type": "framing", "severity": "high", "issue": "Overclaiming detected"},
            {"type": "data", "severity": "critical", "issue": "Inconsistent percentage reporting"},
        ]
        result = service.simulate_competitor_response(issues)

        assert result["competitor_strategy"].strip() != ""
        assert len(result["exploitable_weaknesses"]) > 0
        assert len(result["counter_measures"]) > 0

    def test_simulate_competitor_response_more_issues_means_more_weaknesses(self):
        review = _load_review()
        service = review.SectionReviewService()

        few_issues = [
            {"type": "framing", "severity": "high", "issue": "Overclaiming detected"},
        ]
        many_issues = [
            {"type": "framing", "severity": "high", "issue": "Overclaiming detected"},
            {"type": "data", "severity": "critical", "issue": "Data mismatch in Table 2"},
            {
                "type": "evaluation_rigor",
                "severity": "high",
                "issue": "Missing failure analysis",
            },
        ]

        few = service.simulate_competitor_response(few_issues)
        many = service.simulate_competitor_response(many_issues)

        assert len(many["exploitable_weaknesses"]) >= len(few["exploitable_weaknesses"])

    def test_simulate_competitor_response_works_with_none_context(self):
        review = _load_review()
        service = review.SectionReviewService()

        result = service.simulate_competitor_response(
            [{"type": "completeness", "severity": "high", "issue": "Missing limitations"}],
            None,
        )

        assert "this domain" in result["competitor_strategy"]

    def test_check_survivor_bias_returns_required_shape(self):
        review = _load_review()
        service = review.SectionReviewService()

        result = service.check_survivor_bias([])

        assert set(result.keys()) == {"has_survivor_bias", "evidence", "recommendation"}
        assert isinstance(result["has_survivor_bias"], bool)
        assert isinstance(result["evidence"], list)
        assert isinstance(result["recommendation"], str)
        assert result["recommendation"].strip() != ""

    def test_check_survivor_bias_evidence_is_list_of_strings(self):
        review = _load_review()
        service = review.SectionReviewService()

        issues = [
            {
                "type": "evaluation_rigor",
                "severity": "high",
                "issue": "State-of-the-art claim without caveats",
                "suggestion": "Add more conservative framing",
            },
            {
                "type": "baseline_completeness",
                "severity": "high",
                "issue": "Missing constrained decoding baseline comparison",
                "suggestion": "Add stronger baseline",
            },
        ]
        result = service.check_survivor_bias(issues)

        assert all(isinstance(item, str) for item in result["evidence"])

    def test_check_survivor_bias_detects_success_without_failure_acknowledgement(self):
        review = _load_review()
        service = review.SectionReviewService()

        issues = [
            {
                "type": "evaluation_rigor",
                "severity": "high",
                "issue": "state-of-the-art performance reported",
                "suggestion": "strengthen evaluation",
            },
            {
                "type": "baseline_completeness",
                "severity": "critical",
                "issue": "Missing strong baseline",
                "suggestion": "Add stronger competitor",
            },
        ]
        result = service.check_survivor_bias(issues)

        assert result["has_survivor_bias"] is True
        assert len(result["evidence"]) >= 2

    def test_check_survivor_bias_works_with_none_context(self):
        review = _load_review()
        service = review.SectionReviewService()

        result = service.check_survivor_bias([], None)

        assert isinstance(result["has_survivor_bias"], bool)
        assert result["recommendation"].strip() != ""

    def test_generate_strengthened_version_includes_issue_mitigation_and_counters(self):
        review = _load_review()
        service = review.SectionReviewService()

        issues = [
            {
                "type": "framing",
                "severity": "high",
                "issue": "Overclaiming detected",
            },
            {
                "type": "data",
                "severity": "critical",
                "issue": "Inconsistent percentage reporting",
            },
        ]
        black_swans = [
            {
                "scenario": "Dataset leakage invalidates results",
                "probability": "low",
                "impact": "critical",
                "mitigation": "Run contamination checks on all splits",
            }
        ]
        competitor_analysis = {
            "competitor_strategy": "Attack weakest baselines",
            "exploitable_weaknesses": ["Overclaiming detected"],
            "counter_measures": ["Expand baseline suite"],
        }

        result = service.generate_strengthened_version(issues, black_swans, competitor_analysis)

        assert isinstance(result, str)
        assert result.strip() != ""
        assert result.startswith("## Strengthened Version")
        assert "Overclaiming detected" in result
        assert "Run contamination checks on all splits" in result
        assert "Expand baseline suite" in result

    def test_generate_strengthened_version_with_empty_inputs_still_meaningful(self):
        review = _load_review()
        service = review.SectionReviewService()

        result = service.generate_strengthened_version([], [], {})

        assert result.strip() != ""
        assert "## Strengthened Version" in result
        assert "No critical/high issues detected" in result
        assert "No explicit exploitable weaknesses identified" in result

    def test_review_paper_summary_includes_adversarial_analysis(self, tmp_path):
        review = _load_review()
        tex_file = tmp_path / "adversarial_test.tex"
        tex_file.write_text(r"""
\title{Adversarial Test}
\section{Introduction}
We propose a novel state-of-the-art expert system.
\section{Experiments}
We achieve 99.98% parse success rate.
""")

        service = review.SectionReviewService()
        result = service.review_paper(tex_file)

        assert "adversarial_analysis" in result.summary
        adversarial = result.summary["adversarial_analysis"]
        assert set(adversarial.keys()) == {
            "black_swans",
            "competitor_response",
            "survivor_bias",
            "strengthened_version",
        }
