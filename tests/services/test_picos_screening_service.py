from __future__ import annotations

import importlib
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

pytest = importlib.import_module("pytest")


def _load_service_module():
    return importlib.import_module("crane.services.picos_screening_service")


def _register_tools(mcp: _ToolCollector) -> None:
    screening_tools = importlib.import_module("crane.tools.screening")
    screening_tools.register_tools(mcp)


class _ToolCollector:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


@pytest.fixture
def service():
    mod = _load_service_module()
    return mod.PICOSScreeningService("references")


class TestPICOSDataclasses:
    def test_picos_criteria_strips_whitespace(self):
        mod = _load_service_module()
        criteria = mod.PICOSCriteria(population="  deep learning models  ", outcome="  accuracy ")
        assert criteria.population == "deep learning models"
        assert criteria.outcome == "accuracy"

    @pytest.mark.parametrize(
        ("kwargs", "expected"),
        [
            (
                {
                    "population_score": 0.0,
                    "intervention_score": 0.0,
                    "comparison_score": 0.0,
                    "outcome_score": 0.0,
                    "study_design_score": 0.0,
                    "overall_score": 0.0,
                },
                0.0,
            ),
            (
                {
                    "population_score": 1.0,
                    "intervention_score": 1.0,
                    "comparison_score": 1.0,
                    "outcome_score": 1.0,
                    "study_design_score": 1.0,
                    "overall_score": 1.0,
                },
                1.0,
            ),
        ],
    )
    def test_picos_match_accepts_score_bounds(self, kwargs, expected):
        mod = _load_service_module()
        result = mod.PICOSMatch(**kwargs)
        assert result.overall_score == expected

    @pytest.mark.parametrize(
        "bad_field",
        [
            "population_score",
            "intervention_score",
            "comparison_score",
            "outcome_score",
            "study_design_score",
            "overall_score",
        ],
    )
    def test_picos_match_rejects_out_of_range_scores(self, bad_field):
        mod = _load_service_module()
        kwargs = {
            "population_score": 0.5,
            "intervention_score": 0.5,
            "comparison_score": 0.5,
            "outcome_score": 0.5,
            "study_design_score": 0.5,
            "overall_score": 0.5,
        }
        kwargs[bad_field] = 1.1
        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            mod.PICOSMatch(**kwargs)

    def test_picos_screening_result_rejects_invalid_decision(self):
        mod = _load_service_module()
        match = mod.PICOSMatch(0.1, 0.1, 0.1, 0.1, 0.1, 0.1)
        with pytest.raises(ValueError, match="decision must be one of"):
            mod.PICOSScreeningResult(
                paper_key="paper-a",
                title="A",
                match=match,
                decision="unknown",
                extracted_picos=mod.PICOSCriteria(),
            )


class TestExtractPICOS:
    def test_extract_picos_complete_data(self, service):
        paper = {
            "title": "Attention mechanisms for deep learning models",
            "abstract": "We compare against baseline CNN and improve classification accuracy.",
            "ai_annotations": {
                "methodology": "Experimental benchmark across datasets.",
                "key_contributions": ["We propose a transformer approach for text models."],
            },
        }
        picos = service.extract_picos(paper)
        assert "models" in picos.population
        assert "attention" in picos.intervention or "transformer" in picos.intervention
        assert "baseline cnn" in picos.comparison
        assert "accuracy" in picos.outcome
        assert picos.study_design == "empirical"

    def test_extract_picos_partial_data(self, service):
        paper = {
            "title": "A survey of language models",
            "abstract": "This survey reviews prior methods.",
        }
        picos = service.extract_picos(paper)
        assert picos.study_design == "survey"
        assert isinstance(picos.intervention, str)
        assert isinstance(picos.outcome, str)

    def test_extract_picos_empty_data(self, service):
        picos = service.extract_picos({})
        assert picos == _load_service_module().PICOSCriteria()

    def test_extract_picos_handles_string_key_contributions(self, service):
        paper = {
            "title": "Method for documents",
            "abstract": "Compared to linear baseline, we increase recall.",
            "ai_annotations": {"key_contributions": "we introduce retrieval"},
        }
        picos = service.extract_picos(paper)
        assert "retrieval" in picos.intervention
        assert "recall" in picos.outcome

    @pytest.mark.parametrize(
        ("abstract", "expected"),
        [
            ("We provide theorem and proof for convergence.", "theoretical"),
            ("This is a systematic literature review and survey.", "survey"),
            ("We run experiments and benchmark evaluation.", "empirical"),
            ("Background and motivation only.", ""),
        ],
    )
    def test_extract_study_design_variants(self, service, abstract, expected):
        picos = service.extract_picos({"title": "Paper", "abstract": abstract})
        assert picos.study_design == expected

    @pytest.mark.parametrize(
        "abstract",
        [
            "Compared to baseline CNN, our model performs better.",
            "Our approach is better against random forest baseline.",
            "The method outperforms versus svm baseline.",
        ],
    )
    def test_extract_comparison_variants(self, service, abstract):
        picos = service.extract_picos({"title": "Paper", "abstract": abstract})
        assert picos.comparison != ""

    @pytest.mark.parametrize(
        "abstract",
        [
            "The method improves classification accuracy by 3 points.",
            "The system reduces latency in production.",
            "We achieve better F1 and precision.",
        ],
    )
    def test_extract_outcome_variants(self, service, abstract):
        picos = service.extract_picos({"title": "Paper", "abstract": abstract})
        assert picos.outcome != ""


class TestMatchPaper:
    def test_match_paper_exact_match(self, service):
        mod = _load_service_module()
        paper = mod.PICOSCriteria(
            population="deep learning models",
            intervention="attention mechanism",
            comparison="baseline cnn",
            outcome="classification accuracy",
            study_design="empirical",
        )
        criteria = mod.PICOSCriteria(
            population="deep learning models",
            intervention="attention mechanism",
            comparison="baseline cnn",
            outcome="classification accuracy",
            study_design="experimental",
        )
        match = service.match_paper(paper, criteria)
        assert match.population_score == 1.0
        assert match.intervention_score == 1.0
        assert match.comparison_score == 1.0
        assert match.outcome_score == 1.0
        assert match.study_design_score == 1.0
        assert match.overall_score == 1.0

    def test_match_paper_partial_match(self, service):
        mod = _load_service_module()
        paper = mod.PICOSCriteria(
            population="deep learning models",
            intervention="attention transformer",
            comparison="baseline cnn",
            outcome="accuracy latency",
            study_design="empirical",
        )
        criteria = mod.PICOSCriteria(
            population="models",
            intervention="attention mechanism",
            comparison="baseline svm",
            outcome="accuracy",
            study_design="empirical",
        )
        match = service.match_paper(paper, criteria)
        assert 0.0 < match.overall_score < 1.0
        assert "attention" in match.matched_terms["intervention"]

    def test_match_paper_no_match(self, service):
        mod = _load_service_module()
        paper = mod.PICOSCriteria(
            population="patients",
            intervention="drug",
            comparison="placebo",
            outcome="blood pressure",
            study_design="theoretical",
        )
        criteria = mod.PICOSCriteria(
            population="image models",
            intervention="attention",
            comparison="cnn",
            outcome="accuracy",
            study_design="survey",
        )
        match = service.match_paper(paper, criteria)
        assert match.overall_score == 0.0

    def test_match_paper_empty_criteria_gives_full_match(self, service):
        mod = _load_service_module()
        paper = mod.PICOSCriteria(population="a")
        criteria = mod.PICOSCriteria()
        match = service.match_paper(paper, criteria)
        assert match.population_score == 1.0
        assert match.intervention_score == 1.0
        assert match.comparison_score == 1.0
        assert match.outcome_score == 1.0
        assert match.study_design_score == 1.0
        assert match.overall_score == 1.0

    @pytest.mark.parametrize(
        ("paper_design", "criteria_design", "expected"),
        [
            ("experimental", "empirical", 1.0),
            ("proof-based", "theoretical", 1.0),
            ("systematic review", "survey", 1.0),
            ("survey", "empirical", 0.0),
        ],
    )
    def test_match_paper_study_design_synonyms(
        self, service, paper_design, criteria_design, expected
    ):
        mod = _load_service_module()
        paper = mod.PICOSCriteria(study_design=paper_design)
        criteria = mod.PICOSCriteria(study_design=criteria_design)
        match = service.match_paper(paper, criteria)
        assert match.study_design_score == expected


class TestScreenPapers:
    def test_screen_papers_batch_sorted_with_mixed_decisions(self, service):
        mod = _load_service_module()
        service.ref_service = MagicMock()
        service.ref_service.get.side_effect = [
            {
                "title": "Perfect",
                "abstract": "attention models compared to baseline cnn improve accuracy",
                "ai_annotations": {"methodology": "experimental benchmark"},
            },
            {
                "title": "Partial",
                "abstract": "models with attention improve latency",
                "ai_annotations": {"methodology": "empirical"},
            },
            {
                "title": "No Match",
                "abstract": "survey of healthcare policy",
                "ai_annotations": {"methodology": "survey"},
            },
        ]
        criteria = mod.PICOSCriteria(
            population="models",
            intervention="attention",
            comparison="baseline cnn",
            outcome="accuracy",
            study_design="empirical",
        )
        results = service.screen_papers(["a", "b", "c"], criteria, threshold=0.7)
        assert [r.paper_key for r in results] == ["a", "b", "c"]
        assert results[0].decision == "include"
        assert results[1].decision in {"maybe", "exclude"}
        assert results[2].decision == "exclude"

    def test_screen_papers_handles_no_papers(self, service):
        mod = _load_service_module()
        service.ref_service = MagicMock()
        criteria = mod.PICOSCriteria(population="models")
        results = service.screen_papers([], criteria)
        assert results == []
        service.ref_service.get.assert_not_called()

    @pytest.mark.parametrize("threshold", [-0.01, 1.01])
    def test_screen_papers_rejects_invalid_threshold(self, service, threshold):
        mod = _load_service_module()
        with pytest.raises(ValueError, match="threshold must be between 0.0 and 1.0"):
            service.screen_papers(["paper-a"], mod.PICOSCriteria(), threshold=threshold)


class TestMCPToolIntegration:
    def test_tool_registered(self):
        collector = _ToolCollector()
        _register_tools(collector)
        assert "screen_papers_by_picos" in collector.tools

    def test_screen_papers_by_picos_tool_returns_structured_result(self):
        collector = _ToolCollector()
        _register_tools(collector)

        with (
            patch(
                "crane.services.reference_service.ReferenceService.get_all_keys",
                return_value=["paper-a", "paper-b"],
            ) as mocked_keys,
            patch(
                "crane.services.reference_service.ReferenceService.get",
                side_effect=[
                    {
                        "title": "Paper A",
                        "abstract": "attention model compared to baseline cnn improves accuracy",
                        "ai_annotations": {"methodology": "experimental"},
                    },
                    {
                        "title": "Paper B",
                        "abstract": "survey of methods",
                        "ai_annotations": {"methodology": "survey"},
                    },
                ],
            ) as mocked_get,
        ):
            result = collector.tools["screen_papers_by_picos"](
                population="models",
                intervention="attention",
                comparison="baseline cnn",
                outcome="accuracy",
                study_design="empirical",
                threshold=0.5,
                refs_dir="references",
            )

        mocked_keys.assert_called_once_with()
        assert mocked_get.call_count == 2
        assert result["total_papers"] == 2
        assert result["threshold"] == 0.5
        assert set(result.keys()) == {
            "criteria",
            "threshold",
            "total_papers",
            "included",
            "maybe",
            "excluded",
            "results",
        }
        assert len(result["results"]) == 2

    def test_screen_papers_by_picos_tool_with_no_keys(self):
        collector = _ToolCollector()
        _register_tools(collector)

        with (
            patch(
                "crane.services.reference_service.ReferenceService.get_all_keys",
                return_value=[],
            ) as mocked_keys,
            patch(
                "crane.services.reference_service.ReferenceService.get",
            ) as mocked_get,
        ):
            result = collector.tools["screen_papers_by_picos"](refs_dir="references")

        mocked_keys.assert_called_once_with()
        mocked_get.assert_not_called()
        assert result["total_papers"] == 0
        assert result["results"] == []

    def test_screen_papers_by_picos_tool_uses_threshold_and_groups(self):
        collector = _ToolCollector()
        _register_tools(collector)

        with (
            patch(
                "crane.services.reference_service.ReferenceService.get_all_keys",
                return_value=["paper-a", "paper-b", "paper-c"],
            ),
            patch(
                "crane.services.reference_service.ReferenceService.get",
                side_effect=[
                    {
                        "title": "A",
                        "abstract": "attention baseline cnn accuracy experiment",
                        "ai_annotations": {"methodology": "experimental"},
                    },
                    {
                        "title": "B",
                        "abstract": "attention models with latency gains",
                        "ai_annotations": {"methodology": "empirical"},
                    },
                    {
                        "title": "C",
                        "abstract": "theoretical proof for optimization",
                        "ai_annotations": {"methodology": "theoretical"},
                    },
                ],
            ),
        ):
            result = collector.tools["screen_papers_by_picos"](
                intervention="attention",
                comparison="baseline cnn",
                outcome="accuracy",
                study_design="empirical",
                threshold=0.7,
            )

        assert result["included"] == ["paper-a"]
        assert "paper-b" in result["maybe"] or "paper-b" in result["excluded"]
        assert "paper-c" in result["excluded"]

    def test_screen_papers_by_picos_tool_can_be_mocked_at_service_layer(self):
        collector = _ToolCollector()
        _register_tools(collector)

        fake_match = SimpleNamespace(
            population_score=0.9,
            intervention_score=0.9,
            comparison_score=0.9,
            outcome_score=0.9,
            study_design_score=0.9,
            overall_score=0.9,
            matched_terms={"population": ["models"]},
        )
        fake_picos = SimpleNamespace(
            population="models",
            intervention="attention",
            comparison="baseline",
            outcome="accuracy",
            study_design="empirical",
        )
        fake_result = [
            SimpleNamespace(
                paper_key="paper-a",
                title="Paper A",
                decision="include",
                match=fake_match,
                extracted_picos=fake_picos,
            )
        ]

        with (
            patch(
                "crane.tools.screening.PICOSScreeningService.screen_papers",
                return_value=fake_result,
            ) as mocked_screen,
            patch(
                "crane.services.reference_service.ReferenceService.get_all_keys",
                return_value=["paper-a"],
            ),
        ):
            result = collector.tools["screen_papers_by_picos"](
                population="models",
                refs_dir="references",
            )

        mocked_screen.assert_called_once()
        assert result["included"] == ["paper-a"]
