# pyright: reportMissingImports=false

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import yaml

from crane.models.paper_profile import (
    CostAssessment,
    EvidencePattern,
    JournalFit,
    PaperProfile,
    PaperType,
)
from crane.services.apc_analysis_service import APCAnalysisService
from crane.services.journal_matching_service import JournalMatchingService
from crane.tools.evaluation_v2 import register_tools


def _base_journal(name: str = "J1") -> dict:
    return {
        "name": name,
        "abbreviation": name,
        "publisher": "P",
        "quartile": "Q1",
        "impact_factor": 10.0,
        "scope_keywords": ["machine learning"],
        "preferred_paper_types": ["empirical"],
        "preferred_method_families": ["deep learning"],
        "preferred_evidence_patterns": ["benchmark_heavy"],
        "typical_word_count": [6000, 10000],
        "review_timeline_months": [3, 6],
        "acceptance_rate": 0.2,
        "apc_usd": 0,
        "open_access": False,
        "open_access_type": "subscription",
        "waiver_available": False,
        "desk_reject_signals": ["no experiments"],
        "citation_venues": ["NeurIPS"],
    }


def _write_profiles(tmp_path: Path, journals: list[dict]) -> Path:
    path = tmp_path / "profiles.yaml"
    path.write_text(yaml.safe_dump({"journals": journals}, sort_keys=False), encoding="utf-8")
    return path


def _profile() -> PaperProfile:
    return PaperProfile(
        paper_type=PaperType.EMPIRICAL,
        evidence_pattern=EvidencePattern.BENCHMARK_HEAVY,
        keywords=["machine learning"],
        problem_domain="machine learning",
        citation_neighborhood=["NeurIPS"],
        word_count=8000,
    )


class _ToolCollector:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


def _fit(name: str, score: float) -> JournalFit:
    return JournalFit(journal_name=name, overall_fit=score)


class TestPaperProfileBudgetValidation:
    def test_budget_defaults_to_none(self):
        assert PaperProfile().budget_usd is None

    def test_budget_accepts_zero(self):
        assert PaperProfile(budget_usd=0).budget_usd == 0

    def test_budget_accepts_positive(self):
        assert PaperProfile(budget_usd=1200.5).budget_usd == 1200.5

    def test_budget_rejects_negative(self):
        with pytest.raises(ValueError, match="budget_usd"):
            PaperProfile(budget_usd=-1)


class TestCostAssessmentValidation:
    def test_cost_assessment_valid(self):
        c = CostAssessment(1500, "hybrid", "within_budget", 500)
        assert c.apc_usd == 1500

    def test_apc_cannot_be_negative(self):
        with pytest.raises(ValueError, match="apc_usd"):
            CostAssessment(-1, "hybrid", "within_budget", 0)

    @pytest.mark.parametrize(
        "model", ["subscription", "gold_oa", "hybrid", "diamond_oa", "unknown"]
    )
    def test_publication_model_accepts_allowed_values(self, model: str):
        c = CostAssessment(0, model, "within_budget", 0)
        assert c.publication_model == model

    def test_publication_model_rejects_invalid_value(self):
        with pytest.raises(ValueError, match="publication_model"):
            CostAssessment(0, "green", "within_budget", 0)

    @pytest.mark.parametrize(
        "status",
        ["within_budget", "near_budget", "over_budget", "no_budget", "waiver_possible"],
    )
    def test_affordability_status_accepts_allowed_values(self, status: str):
        c = CostAssessment(0, "subscription", status, 0)
        assert c.affordability_status == status

    def test_affordability_status_rejects_invalid_value(self):
        with pytest.raises(ValueError, match="affordability_status"):
            CostAssessment(0, "subscription", "affordable", 0)


class TestAssessCost:
    def test_no_budget_status(self, tmp_path: Path):
        service = APCAnalysisService(_write_profiles(tmp_path, [_base_journal()]))
        cost = service.assess_cost(service.journals[0], budget_usd=None)
        assert cost.affordability_status == "no_budget"

    def test_free_subscription_is_within_budget(self, tmp_path: Path):
        service = APCAnalysisService(_write_profiles(tmp_path, [_base_journal()]))
        cost = service.assess_cost(service.journals[0], budget_usd=0)
        assert cost.affordability_status == "within_budget"

    def test_free_diamond_is_within_budget(self, tmp_path: Path):
        j = _base_journal()
        j["open_access_type"] = "diamond_oa"
        service = APCAnalysisService(_write_profiles(tmp_path, [j]))
        cost = service.assess_cost(service.journals[0], budget_usd=0)
        assert cost.affordability_status == "within_budget"

    def test_within_budget_status(self, tmp_path: Path):
        j = _base_journal()
        j["apc_usd"] = 900
        j["open_access_type"] = "hybrid"
        service = APCAnalysisService(_write_profiles(tmp_path, [j]))
        cost = service.assess_cost(service.journals[0], budget_usd=1000)
        assert cost.affordability_status == "within_budget"
        assert cost.budget_delta_usd == 100

    def test_exact_budget_boundary(self, tmp_path: Path):
        j = _base_journal()
        j["apc_usd"] = 1000
        j["open_access_type"] = "hybrid"
        service = APCAnalysisService(_write_profiles(tmp_path, [j]))
        cost = service.assess_cost(service.journals[0], budget_usd=1000)
        assert cost.affordability_status == "within_budget"
        assert cost.budget_delta_usd == 0

    def test_near_budget_status_within_10_percent(self, tmp_path: Path):
        j = _base_journal()
        j["apc_usd"] = 1080
        j["open_access_type"] = "hybrid"
        service = APCAnalysisService(_write_profiles(tmp_path, [j]))
        cost = service.assess_cost(service.journals[0], budget_usd=1000)
        assert cost.affordability_status == "near_budget"

    def test_over_budget_status(self, tmp_path: Path):
        j = _base_journal()
        j["apc_usd"] = 1200
        j["open_access_type"] = "hybrid"
        service = APCAnalysisService(_write_profiles(tmp_path, [j]))
        cost = service.assess_cost(service.journals[0], budget_usd=1000)
        assert cost.affordability_status == "over_budget"
        assert cost.budget_delta_usd == -200

    def test_waiver_possible_status(self, tmp_path: Path):
        j = _base_journal()
        j["apc_usd"] = 1200
        j["open_access_type"] = "hybrid"
        j["waiver_available"] = True
        service = APCAnalysisService(_write_profiles(tmp_path, [j]))
        cost = service.assess_cost(service.journals[0], budget_usd=1000)
        assert cost.affordability_status == "waiver_possible"
        assert cost.waiver_available is True

    def test_invalid_model_falls_back_to_unknown(self, tmp_path: Path):
        j = _base_journal()
        j["open_access_type"] = "green"
        service = APCAnalysisService(_write_profiles(tmp_path, [j]))
        cost = service.assess_cost(service.journals[0], budget_usd=1000)
        assert cost.publication_model == "unknown"

    def test_stale_flag_true_for_old_timestamp(self, tmp_path: Path):
        j = _base_journal()
        j["apc_last_updated"] = "2020-01-01T00:00:00Z"
        service = APCAnalysisService(_write_profiles(tmp_path, [j]))
        cost = service.assess_cost(service.journals[0], budget_usd=1000)
        assert cost.apc_stale is True

    def test_stale_flag_false_without_timestamp(self, tmp_path: Path):
        service = APCAnalysisService(_write_profiles(tmp_path, [_base_journal()]))
        cost = service.assess_cost(service.journals[0], budget_usd=1000)
        assert cost.apc_stale is False

    def test_budget_zero_marks_paid_journal_not_within(self, tmp_path: Path):
        j = _base_journal()
        j["apc_usd"] = 1
        j["open_access_type"] = "hybrid"
        service = APCAnalysisService(_write_profiles(tmp_path, [j]))
        cost = service.assess_cost(service.journals[0], budget_usd=0)
        assert cost.affordability_status in {"over_budget", "waiver_possible"}


class TestRankByAffordability:
    def test_bucket_ordering(self, tmp_path: Path):
        service = APCAnalysisService(_write_profiles(tmp_path, [_base_journal()]))
        fits = [_fit("A", 0.80), _fit("B", 0.95), _fit("C", 0.75), _fit("D", 0.99), _fit("E", 0.88)]
        costs = [
            CostAssessment(0, "subscription", "over_budget", -100),
            CostAssessment(0, "subscription", "within_budget", 100),
            CostAssessment(0, "subscription", "near_budget", -20),
            CostAssessment(0, "subscription", "waiver_possible", -200),
            CostAssessment(0, "subscription", "no_budget", 0),
        ]
        ranked = service.rank_by_affordability(fits, costs, budget_usd=1000)
        assert [fit.journal_name for fit, _ in ranked] == ["B", "C", "D", "A", "E"]

    def test_within_bucket_sorts_by_fit_then_lower_apc(self, tmp_path: Path):
        service = APCAnalysisService(_write_profiles(tmp_path, [_base_journal()]))
        fits = [_fit("A", 0.9), _fit("B", 0.9), _fit("C", 0.95)]
        costs = [
            CostAssessment(1200, "hybrid", "within_budget", 0),
            CostAssessment(900, "hybrid", "within_budget", 0),
            CostAssessment(1500, "hybrid", "within_budget", 0),
        ]
        ranked = service.rank_by_affordability(fits, costs, budget_usd=2000)
        assert [fit.journal_name for fit, _ in ranked] == ["C", "B", "A"]

    def test_no_budget_sorts_by_fit_then_apc(self, tmp_path: Path):
        service = APCAnalysisService(_write_profiles(tmp_path, [_base_journal()]))
        fits = [_fit("A", 0.9), _fit("B", 0.9), _fit("C", 0.95)]
        costs = [
            CostAssessment(1200, "hybrid", "no_budget", 0),
            CostAssessment(900, "hybrid", "no_budget", 0),
            CostAssessment(1500, "hybrid", "no_budget", 0),
        ]
        ranked = service.rank_by_affordability(fits, costs, budget_usd=None)
        assert [fit.journal_name for fit, _ in ranked] == ["C", "B", "A"]

    def test_all_over_budget_keeps_fit_ranking_within_bucket(self, tmp_path: Path):
        service = APCAnalysisService(_write_profiles(tmp_path, [_base_journal()]))
        fits = [_fit("A", 0.7), _fit("B", 0.9), _fit("C", 0.8)]
        costs = [
            CostAssessment(3000, "hybrid", "over_budget", -2000),
            CostAssessment(3200, "hybrid", "over_budget", -2200),
            CostAssessment(3100, "hybrid", "over_budget", -2100),
        ]
        ranked = service.rank_by_affordability(fits, costs, budget_usd=1000)
        assert [fit.journal_name for fit, _ in ranked] == ["B", "C", "A"]

    def test_all_within_budget_keeps_fit_ranking(self, tmp_path: Path):
        service = APCAnalysisService(_write_profiles(tmp_path, [_base_journal()]))
        fits = [_fit("A", 0.7), _fit("B", 0.9), _fit("C", 0.8)]
        costs = [
            CostAssessment(300, "hybrid", "within_budget", 700),
            CostAssessment(500, "hybrid", "within_budget", 500),
            CostAssessment(400, "hybrid", "within_budget", 600),
        ]
        ranked = service.rank_by_affordability(fits, costs, budget_usd=1000)
        assert [fit.journal_name for fit, _ in ranked] == ["B", "C", "A"]


class TestGenerateApcReport:
    def test_report_contains_required_sections(self, tmp_path: Path):
        service = APCAnalysisService(_write_profiles(tmp_path, [_base_journal()]))
        fits = [_fit("J1", 0.9)]
        costs = [CostAssessment(900, "hybrid", "within_budget", 100)]
        report = service.generate_apc_report(fits, costs, budget_usd=1000)
        assert "# APC Analysis Report" in report
        assert "## Within Budget" in report
        assert "## Over Budget" in report

    def test_report_has_markdown_table(self, tmp_path: Path):
        service = APCAnalysisService(_write_profiles(tmp_path, [_base_journal()]))
        report = service.generate_apc_report(
            [_fit("J1", 0.9)],
            [CostAssessment(0, "subscription", "within_budget", 1000)],
            budget_usd=1000,
        )
        assert "| Journal | APC | Fit Score | Model | Status |" in report
        assert "| J1 | $0 | 0.90 | subscription | within budget |" in report

    def test_report_budget_not_specified_when_none(self, tmp_path: Path):
        service = APCAnalysisService(_write_profiles(tmp_path, [_base_journal()]))
        report = service.generate_apc_report(
            [_fit("J1", 0.9)],
            [CostAssessment(1000, "hybrid", "no_budget", 0)],
            budget_usd=None,
        )
        assert "**Budget**: Not specified" in report

    def test_report_counts_affordable_journals(self, tmp_path: Path):
        service = APCAnalysisService(_write_profiles(tmp_path, [_base_journal()]))
        fits = [_fit("A", 0.9), _fit("B", 0.8), _fit("C", 0.7)]
        costs = [
            CostAssessment(900, "hybrid", "within_budget", 100),
            CostAssessment(1050, "hybrid", "near_budget", -50),
            CostAssessment(1300, "hybrid", "over_budget", -300),
        ]
        report = service.generate_apc_report(fits, costs, budget_usd=1000)
        assert "**Affordable journals**: 2/3" in report


class TestJournalMatchingBudgetAware:
    def test_match_backward_compatible_without_budget(self, tmp_path: Path):
        a = _base_journal("A")
        b = _base_journal("B")
        b["scope_keywords"] = ["vision"]
        service = JournalMatchingService(_write_profiles(tmp_path, [b, a]))
        fits = service.match(_profile())
        assert fits[0].journal_name == "A"
        assert all(fit.cost_assessment is None for fit in fits)

    def test_match_attaches_cost_assessment_when_budget_provided(self, tmp_path: Path):
        j = _base_journal("Paid")
        j["apc_usd"] = 1200
        j["open_access_type"] = "hybrid"
        service = JournalMatchingService(_write_profiles(tmp_path, [j]))
        fit = service.match(_profile(), budget_usd=1000)[0]
        assert fit.cost_assessment is not None
        assert fit.cost_assessment.affordability_status in {
            "near_budget",
            "over_budget",
            "waiver_possible",
        }

    def test_recommend_top3_budget_returns_all_slots(self, tmp_path: Path):
        journals = []
        for idx, apc in enumerate([0, 900, 2500], start=1):
            j = _base_journal(f"J{idx}")
            j["apc_usd"] = apc
            j["open_access_type"] = "hybrid" if apc > 0 else "subscription"
            journals.append(j)
        service = JournalMatchingService(_write_profiles(tmp_path, journals))
        rec = service.recommend_top3(_profile(), budget_usd=1000)
        assert rec["target"] is not None
        assert rec["backup"] is not None
        assert rec["safe"] is not None


class TestEvaluationV2APCTools:
    def test_register_tools_exposes_analyze_apc(self):
        collector = _ToolCollector()
        register_tools(collector)
        assert "analyze_apc" in collector.tools

    def test_match_journal_v2_accepts_budget_and_returns_cost(self):
        collector = _ToolCollector()
        register_tools(collector)

        fake_profile = _profile()
        fake_fit = JournalFit(journal_name="J1", overall_fit=0.9)
        fake_fit.cost_assessment = CostAssessment(900, "hybrid", "within_budget", 100)

        with (
            patch(
                "crane.tools.evaluation_v2.PaperProfileService.extract_profile",
                return_value=fake_profile,
            ),
            patch(
                "crane.tools.evaluation_v2.JournalMatchingService.recommend_top3",
                return_value={"target": fake_fit, "backup": None, "safe": None},
            ) as top3_mock,
        ):
            result = collector.tools["match_journal_v2"]("paper.tex", budget_usd=1500)

        top3_mock.assert_called_once_with(fake_profile, budget_usd=1500)
        assert result["budget_usd"] == 1500
        assert (
            result["recommendations"]["target"]["cost_assessment"]["affordability_status"]
            == "within_budget"
        )

    def test_analyze_apc_integration_payload(self):
        collector = _ToolCollector()
        register_tools(collector)

        fake_profile = _profile()
        fake_fit = JournalFit(journal_name="J1", overall_fit=0.81)
        fake_fit.cost_assessment = CostAssessment(1200, "hybrid", "over_budget", -200)

        with (
            patch(
                "crane.tools.evaluation_v2.PaperProfileService.extract_profile",
                return_value=fake_profile,
            ),
            patch(
                "crane.tools.evaluation_v2.JournalMatchingService.match",
                return_value=[fake_fit],
            ) as match_mock,
            patch(
                "crane.tools.evaluation_v2.APCAnalysisService.generate_apc_report",
                return_value="# APC Analysis Report\n",
            ),
        ):
            result = collector.tools["analyze_apc"]("paper.tex", budget_usd=1000)

        match_mock.assert_called_once_with(fake_profile, budget_usd=1000)
        assert result["affordability_summary"]["total_journals"] == 1
        assert result["apc_analysis"][0]["cost_assessment"]["affordability_status"] == "over_budget"
        assert "report_markdown" in result

    def test_analyze_apc_counts_affordable(self):
        collector = _ToolCollector()
        register_tools(collector)

        fake_profile = _profile()
        a = JournalFit(journal_name="A", overall_fit=0.9)
        a.cost_assessment = CostAssessment(900, "hybrid", "within_budget", 100)
        b = JournalFit(journal_name="B", overall_fit=0.8)
        b.cost_assessment = CostAssessment(1050, "hybrid", "near_budget", -50)
        c = JournalFit(journal_name="C", overall_fit=0.7)
        c.cost_assessment = CostAssessment(1500, "hybrid", "over_budget", -500)

        with (
            patch(
                "crane.tools.evaluation_v2.PaperProfileService.extract_profile",
                return_value=fake_profile,
            ),
            patch(
                "crane.tools.evaluation_v2.JournalMatchingService.match",
                return_value=[a, b, c],
            ),
            patch(
                "crane.tools.evaluation_v2.APCAnalysisService.generate_apc_report",
                return_value="# APC Analysis Report\n",
            ),
        ):
            result = collector.tools["analyze_apc"]("paper.tex", budget_usd=1000)

        assert result["affordability_summary"]["affordable_journals"] == 2
